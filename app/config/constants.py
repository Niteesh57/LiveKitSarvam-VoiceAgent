"""
Application constants — broker configuration and language settings.
"""

# ─── Broker Configuration ──────────────────────────────────────────────────
BROKER_NAME = "Ajit Jawale"
AGENCY_NAME = "Sunrise Properties"
OFFICE_ADDRESS = "A-203 Pearl Plaza, Andheri West, Mumbai 400053"
BROKER_PHONE = "+91 98765 43210"

# ─── Basic Domain Facts (high-level answers the agent CAN give on call) ─────
# These are safe, general facts. Specifics (exact price, unit, floor plan)
# are still reserved for the office visit.
BROKER_FACTS = {
    "rera": "हाँ जी, हमारे सभी projects RERA registered हैं।",
    "areas": "हमारे पास Andheri, Goregaon, Malad और Borivali side में options हैं।",
    "possession": "कुछ projects ready-to-move हैं और कुछ under-construction — दोनों options हैं।",
    "loan": "हाँ जी, home loan में हम पूरी help करते हैं — सभी major banks के साथ tie-up है।",
    "property_types": "1BHK, 2BHK, 3BHK — सभी configurations available हैं।",
    "site_visit": "Office में मिलने के बाद site visit भी arrange कर सकते हैं।",
}

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
    "wrong_number",
    "existing_customer",
]

# ─── Agent Timing Configuration ───────────────────────────────────────────
MAX_CALL_DURATION_SECONDS = 300  # 5 minutes max
SILENCE_TIMEOUT_SECONDS = 30
BATCH_STAGGER_MIN_SECONDS = 5
BATCH_STAGGER_MAX_SECONDS = 300
BATCH_STAGGER_DEFAULT_SECONDS = 30

# How often the server checks for appointment reminders that are due to send
REMINDER_CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# ─── Inactive-room reaper ──────────────────────────────────────────────────
# A LiveKit room is force-deleted once it has been continuously "inactive"
# (no participants, or no one publishing audio) for at least this long.
# A healthy voice call always has >=1 publisher, so live calls are never hit.
ROOM_INACTIVITY_TIMEOUT_SECONDS = 300   # 5 minutes
ROOM_REAPER_INTERVAL_SECONDS = 60       # how often to sweep
# Only rooms whose names start with these prefixes are eligible for reaping,
# so unrelated rooms in a shared LiveKit project are never touched.
MANAGED_ROOM_PREFIXES = ("call-", "web-")
