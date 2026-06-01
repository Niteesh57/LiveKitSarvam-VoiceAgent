"""
LiveKit Agent entrypoint — configures the voice pipeline and starts the session.

Pipeline: Silero VAD → Sarvam STT (Saaras v3) → LLM → Sarvam TTS (Bulbul v3)
"""

import json
import logging
import os

from livekit.agents import AgentSession, JobContext
from livekit.plugins import openai, silero

from app.agent.voice_agent import BrokerAssistant
from app.agent.sarvam_plugins import SarvamSTT, SarvamTTS
from app.config.settings import settings
from app.core.prompt_engine import PromptEngine

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    """
    LiveKit Agent entrypoint — called when a new room is created.

    Reads customer metadata from the room, builds the system prompt,
    configures the STT→LLM→TTS pipeline, and starts the conversation.
    """
    # Wait for the room to be connected
    await ctx.connect()

    # Extract customer context from room metadata (set by server.py)
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
        # Sarvam sarvam-30b — native Hindi understanding, OpenAI-compatible, supports tool calling
        llm_instance = openai.LLM(
            model="sarvam-30b",
            base_url="https://api.sarvam.ai/v1",
            api_key=settings.sarvam_api_key,
            temperature=0.6,
        )
        logger.info("Using Sarvam sarvam-30b LLM")
    else:
        # GPT-4o-mini — proven reliability for function calling
        llm_instance = openai.LLM(
            model="gpt-4o-mini",
            temperature=0.6,
        )
        logger.info("Using OpenAI GPT-4o-mini LLM")

    # ─── Configure Voice Pipeline ──────────────────────────────────────
    # Map language codes for STT
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
        ),
    )

    # Create the agent
    agent = BrokerAssistant(
        customer_name=customer_name,
        customer_phone=customer_phone,
        system_prompt=system_prompt,
    )

    # Start the session — agent joins room and begins listening
    await session.start(agent=agent, room=ctx.room)

    # Agent speaks first with a warm greeting
    await session.generate_reply(
        instructions="Greet the customer warmly using the opening script from your instructions. Use Hinglish by default."
    )

    logger.info("Agent session started for room: %s", ctx.room.name)


def _resolve_stt_language(language_code: str) -> str:
    """
    Map our internal language codes to Sarvam STT language codes.
    Sarvam Saaras supports: hi-IN, en-IN, mr-IN, and auto-detect.
    """
    mapping = {
        "hi-IN": "hi-IN",
        "en-IN": "en-IN",
        "mr-IN": "mr-IN",
        "hi-EN": "hi-IN",  # Hinglish → use Hindi model (handles code-switching)
        "unknown": "unknown",  # Auto-detect
    }
    return mapping.get(language_code, "hi-IN")
