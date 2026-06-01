"""Configuration module for the voice agent application."""

from .settings import settings
from .constants import (
    BROKER_NAME,
    AGENCY_NAME,
    OFFICE_ADDRESS,
    BROKER_PHONE,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    DEFAULT_TTS_SPEAKER,
)

__all__ = [
    "settings",
    "BROKER_NAME",
    "AGENCY_NAME",
    "OFFICE_ADDRESS",
    "BROKER_PHONE",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "DEFAULT_TTS_SPEAKER",
]
