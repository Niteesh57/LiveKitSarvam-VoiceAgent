# ════════════════════════════════════════════════════════
# Sun Rise Demo — Environment Variables
# Copy this file to `.env` and fill in your actual values.
# ════════════════════════════════════════════════════════

# ─── VAPI (required) ────────────────────────────────────
# Get from: https://dashboard.vapi.ai/account → API Keys
VAPI_API_KEY=your_vapi_private_api_key_here

# Get from: https://dashboard.vapi.ai/phone-numbers
# Click on your purchased number → copy the Phone Number ID (NOT the phone number itself)
VAPI_PHONE_NUMBER_ID=your_vapi_phone_number_id_here

# ─── NGROK (optional but strongly recommended) ──────────
# Without ngrok: Vapi can't reach your local webhook → tools won't fire
# Get a free token at: https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTHTOKEN=your_ngrok_auth_token_here

# ─── SERVER ─────────────────────────────────────────────
PORT=8000

# ════════════════════════════════════════════════════════
# NOTES ON TWILIO:
# ════════════════════════════════════════════════════════
# You do NOT need a separate Twilio account or credentials.
# Vapi uses Twilio under the hood automatically.
# When you buy a phone number inside the Vapi dashboard,
# Vapi provisions it via Twilio and handles all telephony.
# Only the VAPI_PHONE_NUMBER_ID above is needed.
#
# If you want to BYO Twilio number (advanced), in Vapi dashboard:
#   Phone Numbers → Import → enter Twilio SID + Auth Token + Phone Number
#   Vapi gives you back a VAPI_PHONE_NUMBER_ID to use here.
# ════════════════════════════════════════════════════════
