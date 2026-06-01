"""
Application constants — broker configuration and language settings.
"""

# ─── Broker Configuration ──────────────────────────────────────────────────
BROKER_NAME = "Ajit Jawale"
AGENCY_NAME = "Sunrise Properties"
OFFICE_ADDRESS = "A-203 Pearl Plaza, Andheri West, Mumbai 400053"
BROKER_PHONE = "+91 98765 43210"

# ─── Language Configuration ────────────────────────────────────────────────
# Sarvam AI supports these Indian languages natively
SUPPORTED_LANGUAGES = {
    "hi-IN": "Hindi",
    "en-IN": "English (India)",
    "mr-IN": "Marathi",
    "hi-EN": "Hinglish (Hindi-English mix)",
    "unknown": "Auto-detect",
}

DEFAULT_LANGUAGE = "hi-IN"
DEFAULT_TTS_SPEAKER = "ritu"

# ─── TTS Voice Options ─────────────────────────────────────────────────────
# bulbul:v2 speakers: anushka, abhilash, manisha, vidya, arya, karun, hitesh
AVAILABLE_VOICES = {
    "female": ["anushka", "manisha", "vidya"],
    "male": ["abhilash", "arya", "karun", "hitesh"],
}

# ─── Call Outcome Enums ────────────────────────────────────────────────────
VALID_OUTCOMES = [
    "appointment_booked",
    "callback_requested",
    "not_interested_now",
    "dnc_requested",
    "customer_busy_reschedule",
]

# ─── Agent Timing Configuration ───────────────────────────────────────────
MAX_CALL_DURATION_SECONDS = 300  # 5 minutes max
SILENCE_TIMEOUT_SECONDS = 30
BATCH_STAGGER_MIN_SECONDS = 5
BATCH_STAGGER_MAX_SECONDS = 300
BATCH_STAGGER_DEFAULT_SECONDS = 30
