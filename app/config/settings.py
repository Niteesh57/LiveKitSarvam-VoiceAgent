"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type safety.
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration — all values sourced from .env file."""

    # ─── LiveKit ───────────────────────────────────────────────────────
    livekit_url: str = Field(..., description="LiveKit Cloud WebSocket URL")
    livekit_api_key: str = Field(..., description="LiveKit API Key")
    livekit_api_secret: str = Field(..., description="LiveKit API Secret")

    # ─── Sarvam AI ─────────────────────────────────────────────────────
    sarvam_api_key: str = Field(..., description="Sarvam AI API Key")

    # ─── OpenAI (optional if using Sarvam LLM) ────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API Key")

    # ─── SIP / Telephony (optional — not needed for browser WebRTC) ──
    sip_outbound_trunk_id: str = Field(default="", description="LiveKit SIP Trunk ID (optional for browser-only mode)")

    # ─── Voice Configuration ──────────────────────────────────────────
    sarvam_tts_speaker: str = Field(default="ritu", description="Sarvam TTS voice")
    default_language: str = Field(default="hi-IN", description="Default language code")
    use_sarvam_llm: bool = Field(default=False, description="Use Sarvam sarvam-30b LLM")

    # ─── Server ───────────────────────────────────────────────────────
    port: int = Field(default=8000, description="FastAPI server port")
    host: str = Field(default="0.0.0.0", description="Server bind host")
    debug: bool = Field(default=False, description="Enable debug mode")

    # ─── Data Storage ─────────────────────────────────────────────────
    data_dir: Path = Field(
        default=Path(__file__).parent.parent.parent / "data",
        description="Directory for JSON data files",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


# Module-level convenience
settings = get_settings()
