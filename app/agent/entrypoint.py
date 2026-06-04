"""
LiveKit Agent entrypoint — configures the voice pipeline and starts the session.

Pipeline: Silero VAD → STT (Deepgram streaming or Sarvam) → GPT-4o-mini → Sarvam TTS (Bulbul v3)
Optimized for natural, low-latency conversational flow.
"""

import json
import logging

from livekit.agents import AgentSession, JobContext
from livekit.plugins import openai, silero

from app.agent.voice_agent import BrokerAssistant
from app.agent.sarvam_plugins import SarvamSTT, SarvamTTS
from app.config.settings import settings
from app.core.prompt_engine import PromptEngine

# Import Deepgram at module level (plugin registration must happen on main thread)
try:
    from livekit.plugins import deepgram as deepgram_plugin
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    """
    LiveKit Agent entrypoint — optimized for natural, low-latency voice.
    """
    await ctx.connect()

    # Extract customer context from room metadata
    metadata = json.loads(ctx.room.metadata or "{}")
    customer_name = metadata.get("customer_name", "Customer")
    customer_phone = metadata.get("customer_phone", "")
    preferred_language = metadata.get("language", settings.default_language)

    logger.info(
        "Agent joining room %s for customer: %s (%s)",
        ctx.room.name,
        customer_name,
        customer_phone,
    )

    # Build the hydrated system prompt with customer memory
    from app.core.memory import get_customer_history
    customer_memory = get_customer_history(customer_phone) or ""

    system_prompt = PromptEngine.get_prompt(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_memory=customer_memory,
    )

    if customer_memory:
        logger.info("Loaded conversation history for %s", customer_phone)
    else:
        logger.info("No previous history for %s (first call)", customer_phone)

    # ─── Configure LLM ─────────────────────────────────────────────────
    if settings.use_sarvam_llm:
        llm_instance = openai.LLM(
            model="sarvam-30b",
            base_url="https://api.sarvam.ai/v1",
            api_key=settings.sarvam_api_key,
            temperature=0.8,
        )
        logger.info("Using Sarvam sarvam-30b LLM")
    else:
        llm_instance = openai.LLM(
            model="gpt-4o-mini",
            temperature=0.8,  # Higher temp = more natural, varied responses
        )
        logger.info("Using OpenAI GPT-4o-mini LLM")

    # ─── Configure Voice Pipeline (low-latency + natural) ──────────────
    stt_language = _resolve_stt_language(preferred_language)

    # Choose STT provider based on config
    if settings.stt_provider == "deepgram" and settings.deepgram_api_key and DEEPGRAM_AVAILABLE:
        stt_instance = deepgram_plugin.STT(
            api_key=settings.deepgram_api_key,
            language=_resolve_deepgram_language(preferred_language),
            model="nova-3",
            interim_results=True,
            no_delay=True,           # Don't wait for extra audio before finalizing
            endpointing_ms=15,       # Faster end-of-speech detection (default 25)
            punctuate=True,
            filler_words=False,      # Skip "um/uh" — faster, cleaner transcripts
        )
        logger.info("Using Deepgram Nova-3 STT (streaming, low-latency)")
    else:
        stt_instance = SarvamSTT(
            language_code=stt_language,
            model="saaras:v3",
        )
        logger.info("Using Sarvam Saaras v3 STT")

    tts_instance = SarvamTTS(
        speaker=settings.sarvam_tts_speaker,
        target_language_code=preferred_language,
        model="bulbul:v3",
        pace=1.1,  # Slightly faster speech for natural conversational feel
    )

    # Pre-warm TTS connection to eliminate first-request jitter
    await tts_instance.prewarm()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt_instance,
        llm=llm_instance,
        tts=tts_instance,
        # ─── Conversation tuning (low-latency) ────────────────────────
        min_endpointing_delay=0.25,   # Start processing ~250ms after user stops (was 600ms)
        max_endpointing_delay=2.0,    # Cap the wait before forcing processing
        preemptive_generation=True,   # Begin LLM generation before endpoint confirmed
        allow_interruptions=True,     # Let user interrupt agent naturally
        min_interruption_duration=0.4, # Responsive barge-in (400ms)
        min_interruption_words=2,      # Need ~2 words to count as real interruption
        user_away_timeout=20.0,       # Detect if user goes silent/away for 20s
    )

    # Create the agent
    agent = BrokerAssistant(
        customer_name=customer_name,
        customer_phone=customer_phone,
        system_prompt=system_prompt,
    )

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Track call start time for duration measurement
    import time
    call_start_time = time.time()
    from pathlib import Path
    RECORDINGS_DIR = Path(settings.data_dir) / "recordings"
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Start local call recording ───────────────────────────────────
    from app.core.call_recorder import LocalCallRecorder
    recorder = LocalCallRecorder(
        room_name=ctx.room.name,
        customer_phone=customer_phone,
    )
    recorder.start(ctx.room)

    # Hook TTS to capture agent audio directly at the source
    tts_instance._recorder = recorder

    logger.info("Local call recording started for room: %s", ctx.room.name)

    # Agent speaks first — short warm greeting with broker name
    from app.config.constants import BROKER_NAME
    await session.generate_reply(
        instructions=f"Say exactly this greeting in Devanagari Hindi: 'हैलो {customer_name} जी! मैं {BROKER_NAME} बोल रहा हूँ, Sunrise Properties से। कैसे हैं आप?' — say only this one sentence, nothing more."
    )

    logger.info("Agent session started for room: %s", ctx.room.name)

    # ─── Silence / user-away handling ──────────────────────────────────
    silence_prompt_count = {"count": 0}

    @session.on("user_state_changed")
    def _on_user_state(ev):
        # When user goes "away" (silent), prompt them; after 2 prompts, close
        try:
            if getattr(ev, "new_state", None) == "away":
                silence_prompt_count["count"] += 1
                if silence_prompt_count["count"] <= 2:
                    import asyncio
                    asyncio.create_task(session.generate_reply(
                        instructions="The customer has gone silent. Gently check in with ONE short Hinglish line like 'हैलो जी, सुन रहे हैं आप?'"
                    ))
                    logger.info("Silence detected — prompting (attempt %d)", silence_prompt_count["count"])
                else:
                    import asyncio
                    logger.info("Customer unresponsive after 2 prompts — ending call")
                    asyncio.create_task(agent._force_disconnect(delay=2.0))
        except Exception as e:
            logger.debug("user_state handler error: %s", e)

    # ─── Max call duration enforcement ─────────────────────────────────
    from app.config.constants import MAX_CALL_DURATION_SECONDS

    async def _enforce_max_duration():
        import asyncio
        await asyncio.sleep(MAX_CALL_DURATION_SECONDS)
        logger.info("Max call duration (%ds) reached — ending", MAX_CALL_DURATION_SECONDS)
        try:
            await session.generate_reply(
                instructions="Politely wrap up in ONE line: 'जी, main aapko WhatsApp pe details bhej deta hoon. धन्यवाद!' Then stop."
            )
        except Exception:
            pass
        await agent._force_disconnect(delay=5.0)

    import asyncio as _asyncio
    _asyncio.create_task(_enforce_max_duration())

    # Register shutdown callback to track call duration and save recording
    @ctx.add_shutdown_callback
    async def on_shutdown():
        duration_seconds = time.time() - call_start_time
        from app.core.data_store import data_store
        data_store.track_call_duration(customer_phone, duration_seconds)

        # Unhook the TTS recorder
        tts_instance._recorder = None

        # Stop the local recorder and save WAV file
        try:
            recording_path = await recorder.stop()
            if recording_path:
                logger.info("Call recording saved: %s", recording_path)
            else:
                logger.warning("No audio captured for recording (room: %s)", ctx.room.name)
        except Exception as e:
            logger.error("Failed to save recording: %s", e)

        logger.info(
            "Call ended for %s. Duration: %.1f seconds",
            customer_phone,
            duration_seconds,
        )


def _resolve_stt_language(language_code: str) -> str:
    """Map language codes to Sarvam STT language codes."""
    mapping = {
        "hi-IN": "hi-IN",
        "en-IN": "en-IN",
        "mr-IN": "mr-IN",
        "hi-EN": "hi-IN",
        "unknown": "unknown",
    }
    return mapping.get(language_code, "hi-IN")


def _resolve_deepgram_language(language_code: str) -> str:
    """Map language codes to Deepgram language codes."""
    mapping = {
        "hi-IN": "hi",
        "en-IN": "en-IN",
        "mr-IN": "mr",
        "hi-EN": "hi",
        "unknown": "hi",
    }
    return mapping.get(language_code, "hi")
