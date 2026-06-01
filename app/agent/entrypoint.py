"""
LiveKit Agent entrypoint — configures the voice pipeline and starts the session.

Pipeline: Silero VAD → Sarvam STT (Saaras v3) → GPT-4o-mini → Sarvam TTS (Bulbul v3)
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

    # Build the hydrated system prompt
    system_prompt = PromptEngine.get_prompt(customer_name, customer_phone)

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

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=SarvamSTT(
            language_code=stt_language,
            model="saaras:v3",
        ),
        llm=llm_instance,
        tts=SarvamTTS(
            speaker=settings.sarvam_tts_speaker,
            target_language_code=preferred_language,
            model="bulbul:v3",
            pace=1.1,  # Slightly faster speech for natural conversational feel
        ),
        # ─── Low-latency + natural conversation tuning ─────────────────
        min_endpointing_delay=0.4,    # React quickly after user stops (400ms)
        max_endpointing_delay=2.5,    # Don't wait too long
        preemptive_generation=True,   # Start generating before user fully finishes
        allow_interruptions=True,     # Let user interrupt agent naturally
    )

    # Create the agent
    agent = BrokerAssistant(
        customer_name=customer_name,
        customer_phone=customer_phone,
        system_prompt=system_prompt,
    )

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Agent speaks first — short warm greeting with broker name
    from app.config.constants import BROKER_NAME
    await session.generate_reply(
        instructions=f"Say exactly this greeting in Devanagari Hindi: 'हैलो {customer_name} जी! मैं {BROKER_NAME} बोल रहा हूँ, Sunrise Properties से। कैसे हैं आप?' — say only this one sentence, nothing more."
    )

    logger.info("Agent session started for room: %s", ctx.room.name)


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
