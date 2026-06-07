# 🏠 Sunrise Properties — AI Voice Agent

An AI-powered voice assistant for real estate brokers, built with **LiveKit Agents**, **Sarvam AI**, **Deepgram**, and **OpenAI GPT-4o-mini**. It handles warm follow-up calls, appointment booking, and lead management with natural Hindi / Hinglish / Marathi / English conversations.

The system ships as two processes:
- **FastAPI server** — operator dashboard, REST API, and WebRTC token service
- **LiveKit agent worker** — the real-time voice pipeline (VAD → STT → LLM → TTS)

---

## 🌟 Features

### 🎙️ Voice Conversation Engine
- **Two ways to talk to the agent**
  - Browser-based WebRTC voice calls (no phone number needed)
  - Outbound phone calls via LiveKit SIP + Plivo trunk
- **Streaming STT** — Deepgram Nova-3 (low-latency, streaming) or Sarvam Saaras (native Indian-language transcription), selectable via `STT_PROVIDER`
- **High-quality TTS** — Sarvam Bulbul v3 at 24 kHz with a persistent HTTP connection pool and prewarm to eliminate first-word jitter. Streams raw `linear16` PCM with automatic fallback to the non-streaming REST endpoint
- **Silero VAD** for voice activity detection
- **Low-latency tuning** — ~250 ms min endpointing delay, preemptive LLM generation, fast barge-in
- **Natural interruptions (barge-in)** — 400 ms / 2-word threshold to interrupt the agent
- **Multi-language** — Hindi, English, Marathi, Hinglish, and Marathi-English mix, with mid-call language switching

### 🧠 Conversation Intelligence
- **Customer memory** — past call summaries, outcomes, and preferences (budget, location, property type, timeline) are injected into the system prompt for returning customers
- **Dynamic prompt hydration** — the system prompt is filled at call time with customer name/phone, broker details, today's date, and the next two weekend appointment slots (IST)
- **Devanagari greeting** — the agent opens with a short, warm greeting using the broker's name
- **Domain facts** — safe high-level answers (RERA, areas, possession, home loan, property types, site visits) while reserving specifics for the office visit

### 📞 Call Lifecycle & Safety
- **Local call recording** — single-timeline mono WAV at 24 kHz. Agent TTS is captured natively (no resampling); customer audio is resampled by LiveKit's high-quality resampler. Both voices interleave chronologically like a real phone call, then normalized to −3 dB
- **HD customer audio upload** — the browser can upload pre-Opus customer audio for higher-fidelity archival
- **Max call duration enforcement** — automatic wrap-up after 300 seconds
- **Silence / user-away handling** — prompts an unresponsive customer up to 2 times, then ends the call
- **Deterministic termination** — wrong-number, DNC, and dispute scenarios force-disconnect the call and delete the LiveKit room
- **Recording metadata** — saved to `data/recordings_meta.json` with duration, sample rate, and timestamps

### 🎯 Lead & CRM Features
- **Lead management** — add single, bulk (JSON), or CSV upload; delete single, batch, or all
- **Lead status tracking** — `pending`, `called`, `booked`, `completed`, `wrong_number`, `existing_customer`
- **Lead scoring** — `hot`, `warm`, `cold`, `dead`, derived from call outcomes
- **Appointment booking** — validates the chosen slot (rejects clearly-past times) and persists the booking
- **Callback scheduling** — captures customer-preferred callback times
- **Call scheduler** — DND enforcement (9 AM – 9 PM IST), optimal calling windows (10–11 AM, 4–6 PM), and retry logic (max 3 attempts with 4-hour gaps)

### 📊 Analytics & Reporting
- Total calls, total bookings, conversion rate
- Outcome breakdown and lead-score breakdown
- Average call duration and average calls per lead
- Per-lead analytics and call history
- Daily / weekly report generation
- Scheduler status (callable now, optimal window, attempt history)

### ⏰ Reminders & WhatsApp (stub)
- **Appointment reminders** — detects appointments within 24 hours, tracks sent/pending status, generates reminder messages
- **WhatsApp queue** — post-call thank-you, appointment confirmation (with office address + Maps link), and reminders are queued to `data/whatsapp_queue.json`
- WhatsApp sending is a **stub** — it logs messages unless `WHATSAPP_API_KEY` is configured. Wire up Twilio/Plivo in `app/core/whatsapp.py` to actually send

### 🔧 Corner-Case Handling (via agent tools)
- Wrong number / person not found → `mark_wrong_number` (logs, marks dead, ends call)
- Privacy complaint / legal threat → `handle_dispute` (one apology, marks DNC, ends call)
- Already booked / already visited → `acknowledge_existing_customer` (skips re-pitch)
- Customer busy / driving → `request_callback`
- Language mismatch → `switch_language`
- Graceful goodbye → `end_call`

---

## 🏗️ Architecture

### Voice Pipeline
```
User Voice → LiveKit Room
           ↓
   Silero VAD (Voice Activity Detection)
           ↓
   STT (Deepgram Nova-3  OR  Sarvam Saaras)
           ↓
   LLM (OpenAI GPT-4o-mini  OR  Sarvam sarvam-30b)
           ↓
   TTS (Sarvam Bulbul v3 @ 24kHz)
           ↓
   LiveKit Room → User Audio
```

### System Components
```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Server                       │
│   (Dashboard UI + REST API + WebRTC Token Service)    │
└───────────────────┬───────────────────────────────────┘
                    │  /api/webrtc/token  (browser calls)
                    │  /api/call          (phone calls via SIP)
                    │  /api/leads         (CRUD + CSV/bulk)
                    │  /api/bookings      (appointments + outcomes)
                    │  /api/recordings    (list/download/upload)
                    │  /api/analytics     (stats + reports + scheduler)
                    │  /api/reminders     (appointment reminders)
                    ↓
┌─────────────────────────────────────────────────────┐
│              LiveKit Cloud / Server                   │
│           (WebRTC rooms + SIP trunking)               │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│             LiveKit Agent Worker                      │
│   BrokerAssistant: VAD → STT → LLM → TTS + tools      │
└───────────────────────────────────────────────────────┘
```

### File Structure
```
LiveKitSarvam-VoiceAgent/
├── app/
│   ├── agent/
│   │   ├── entrypoint.py            # Session setup, pipeline config, lifecycle
│   │   ├── voice_agent.py           # BrokerAssistant + function tools
│   │   └── sarvam_plugins/
│   │       ├── stt.py               # Sarvam Saaras STT plugin
│   │       └── tts.py               # Sarvam Bulbul v3 TTS plugin (streaming)
│   │
│   ├── config/
│   │   ├── settings.py              # Env-based config (pydantic-settings)
│   │   └── constants.py             # Broker info, languages, outcomes, timing
│   │
│   ├── core/
│   │   ├── data_store.py            # Thread-safe JSON storage (atomic writes)
│   │   ├── prompt_engine.py         # System-prompt hydration
│   │   ├── context.py               # Runtime context (IST dates, slots, broker)
│   │   ├── memory.py                # Per-customer conversation memory
│   │   ├── analytics.py             # Lead scoring + analytics + reports
│   │   ├── scheduler.py             # DND windows + retry logic
│   │   ├── reminders.py             # Appointment reminder flow
│   │   ├── whatsapp.py              # WhatsApp queue + send (stub)
│   │   └── call_recorder.py         # Single-timeline mono WAV recorder
│   │
│   └── server/
│       ├── app.py                   # FastAPI app factory + /api/status
│       └── routers/
│           ├── dashboard.py         # Serves static/index.html
│           ├── context.py           # GET /api/context
│           ├── webrtc.py            # POST /api/webrtc/token
│           ├── calls.py             # POST /api/call, /api/call/batch
│           ├── leads.py             # Lead CRUD + CSV + bulk
│           ├── bookings.py          # GET /api/bookings
│           ├── recordings.py        # List/download/upload recordings
│           ├── analytics.py         # Analytics, reports, scheduler
│           └── reminders.py         # Reminder endpoints
│
├── data/                            # JSON storage (auto-created)
│   ├── leads.json
│   ├── bookings.json
│   ├── conversations.json
│   ├── lead_scores.json
│   ├── call_durations.json
│   ├── call_attempts.json
│   ├── reminders.json
│   ├── whatsapp_queue.json
│   ├── recordings_meta.json
│   └── recordings/                  # WAV files
│
├── prompts/system_prompt.md         # Agent system prompt template
├── static/index.html               # Operator dashboard UI
├── run_server.py                    # Start FastAPI server
├── run_agent.py                     # Start LiveKit agent worker
├── setup_plivo_trunk.py             # Helper to create a LiveKit SIP trunk
├── start.sh                         # Run both processes (Docker entrypoint)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🤖 Agent Function Tools

The `BrokerAssistant` (in `app/agent/voice_agent.py`) exposes these tools to the LLM:

| Tool | Purpose |
|------|---------|
| `book_appointment` | Books an office meeting after the customer confirms a slot; rejects past times, updates status to `booked`, scores `hot`, queues WhatsApp confirmation + reminder |
| `log_call_outcome` | Logs the final outcome (must be the last tool call); updates score; saves summary; queues post-call thank-you; force-ends call on DNC |
| `save_conversation_summary` | Captures budget, location, property type, timeline, and notes for future calls |
| `request_callback` | Records a callback time; scores `warm` |
| `switch_language` | Switches conversation language mid-call |
| `mark_wrong_number` | Flags wrong number, scores `dead`, ends call |
| `handle_dispute` | Handles privacy/legal threats — one apology, marks DNC, ends call |
| `acknowledge_existing_customer` | Skips the office re-pitch for existing customers |
| `end_call` | Gracefully disconnects after goodbye |

**Valid call outcomes:** `appointment_booked`, `callback_requested`, `not_interested_now`, `dnc_requested`, `customer_busy_reschedule`, `wrong_number`, `existing_customer`.

---

## 🚀 Setup

### Prerequisites
- Python 3.11 (the Dockerfile uses `python:3.11-slim`)
- LiveKit Cloud account (or self-hosted LiveKit server)
- Sarvam AI API key (used for TTS, and STT if `STT_PROVIDER=sarvam`)
- OpenAI API key (required when `USE_SARVAM_LLM=false`)
- Deepgram API key (required when `STT_PROVIDER=deepgram`)
- Plivo SIP trunk (optional — only for outbound phone calls)

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the project root (see `.envSample copy` for a template):

```env
# ─── LiveKit (required) ───────────────────────────────
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# ─── Sarvam AI (required — TTS, and STT if selected) ──
SARVAM_API_KEY=your_sarvam_api_key
SARVAM_TTS_SPEAKER=shubh

# ─── STT provider: deepgram or sarvam ─────────────────
STT_PROVIDER=deepgram
DEEPGRAM_API_KEY=your_deepgram_api_key

# ─── LLM ───────────────────────────────────────────────
OPENAI_API_KEY=your_openai_api_key      # required if USE_SARVAM_LLM=false
USE_SARVAM_LLM=false

# ─── Telephony (optional — browser calls work without it) ──
SIP_OUTBOUND_TRUNK_ID=ST_xxxxxxxxxxxx

# ─── Voice / language ──────────────────────────────────
DEFAULT_LANGUAGE=hi-IN

# ─── Server ────────────────────────────────────────────
PORT=8000
HOST=0.0.0.0
DEBUG=false

# ─── WhatsApp (optional — stub mode if unset) ──────────
WHATSAPP_API_KEY=
WHATSAPP_PHONE_NUMBER=
```

### Optional: Set Up a Plivo SIP Trunk (phone calls only)
1. Add `PLIVO_AUTH_ID`, `PLIVO_AUTH_TOKEN`, `PLIVO_PHONE_NUMBER` to `.env`
2. Install the LiveKit CLI: `winget install LiveKit.LiveKitCLI`
3. Run `python setup_plivo_trunk.py` — it generates `sip-trunk.json`, registers the trunk, and prints a `SIP_OUTBOUND_TRUNK_ID`
4. Add that ID to `.env` and restart the server

---

## ▶️ Running the Application

You need **two processes** running at the same time.

**Terminal 1 — FastAPI server**
```bash
python run_server.py
```
- Serves the dashboard at `http://localhost:8000` (auto-opens the browser)
- Provides the REST API and WebRTC token service

**Terminal 2 — LiveKit agent worker**
```bash
python run_agent.py dev      # development (auto-reload)
python run_agent.py start    # production
```
- Registers with LiveKit and auto-joins rooms created by the server
- Runs the full STT → LLM → TTS voice pipeline

### Docker
The `Dockerfile` installs dependencies and runs `start.sh`, which launches the agent worker (background) and the server (foreground):
```bash
docker build -t sunrise-voice-agent .
docker run -p 8000:8000 --env-file .env sunrise-voice-agent
```

---

## 📋 Usage

### Browser Voice Call (WebRTC)
1. Open `http://localhost:8000`
2. Enter customer name, phone, and language
3. Click **🎤 Browser Call** and grant microphone permission
4. Speak naturally; the agent responds in real time
5. Click **End Call** when done (the browser also uploads HD customer audio)

### Phone Call (SIP)
1. Configure `SIP_OUTBOUND_TRUNK_ID` in `.env`
2. Add a lead, then click **📞 Call Phone**
3. The agent dials the number and handles the conversation
4. Batch-dial all pending leads via `POST /api/call/batch`

### Lead Management (dashboard)
- **Add** a single lead (name + phone with `+country` code)
- **Add Multiple** via JSON, or upload a CSV (`name,phone` per row)
- **Delete** single, **Delete Selected** (checkboxes), or **Delete All**

---

## 🔌 API Reference

### Status & Context
- `GET /api/status` — SIP config flag, LiveKit URL, TTS voice, LLM mode
- `GET /api/context` — broker info, today's date (IST), next two weekend slots

### WebRTC
- `POST /api/webrtc/token` — create a room + browser join token
  ```json
  { "name": "Customer Name", "phone": "+919876543210", "language": "hi-IN" }
  ```

### Phone Calls
- `POST /api/call` — dial one customer via SIP `{ "name": "...", "phone": "+91..." }`
- `POST /api/call/batch` — dial all pending leads `{ "stagger_sec": 30 }`

### Leads
- `GET /api/leads` — list all leads
- `POST /api/leads/add` — add one `{ "name": "...", "phone": "+91..." }`
- `POST /api/leads/bulk` — add many `{ "leads": [{ "name": "...", "phone": "+91..." }] }`
- `POST /api/leads/csv` — upload a CSV file (`name,phone` rows)
- `POST /api/leads/delete` — delete one `{ "phone": "+91..." }`
- `POST /api/leads/delete-batch` — delete many `{ "phones": ["+91...", ...] }`
- `DELETE /api/leads` — delete all leads

### Bookings
- `GET /api/bookings` — all bookings and call-outcome records

### Recordings
- `GET /api/recordings` — list recordings with metadata
- `GET /api/recordings/{filename}` — download a `.wav` / `.webm`
- `POST /api/recordings/upload-customer` — upload browser HD customer audio

### Analytics
- `GET /api/analytics/` — overall stats (calls, bookings, conversion, breakdowns)
- `GET /api/analytics/leads` — all leads with scores
- `GET /api/analytics/report/{period}` — `daily` or `weekly` summary
- `GET /api/analytics/lead/{phone}` — per-lead analytics
- `GET /api/analytics/scheduler` — callable-now / optimal-window / attempts

### Reminders
- `GET /api/reminders/` — sent + pending reminders
- `GET /api/reminders/pending` — appointments needing reminders
- `GET /api/reminders/upcoming` — appointments within 24 hours
- `POST /api/reminders/send/{phone}?slot=...` — send a specific reminder

---

## 🎛️ Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIVEKIT_URL` | ✅ | – | LiveKit WebSocket URL |
| `LIVEKIT_API_KEY` | ✅ | – | LiveKit API key |
| `LIVEKIT_API_SECRET` | ✅ | – | LiveKit API secret |
| `SARVAM_API_KEY` | ✅ | – | Sarvam AI key (TTS + Sarvam STT) |
| `STT_PROVIDER` | ❌ | `sarvam` | `deepgram` or `sarvam` |
| `DEEPGRAM_API_KEY` | ❌ | – | Required if `STT_PROVIDER=deepgram` |
| `OPENAI_API_KEY` | ❌ | – | Required if `USE_SARVAM_LLM=false` |
| `USE_SARVAM_LLM` | ❌ | `false` | Use Sarvam `sarvam-30b` instead of GPT-4o-mini |
| `SARVAM_TTS_SPEAKER` | ❌ | `ritu` | Sarvam Bulbul voice |
| `DEFAULT_LANGUAGE` | ❌ | `hi-IN` | Default conversation language |
| `SIP_OUTBOUND_TRUNK_ID` | ❌ | – | LiveKit SIP trunk for phone calls |
| `PORT` | ❌ | `8000` | Server port |
| `HOST` | ❌ | `0.0.0.0` | Server bind host |
| `DEBUG` | ❌ | `false` | Verbose logging |
| `WHATSAPP_API_KEY` | ❌ | – | Enables real WhatsApp sending (else stub) |
| `WHATSAPP_PHONE_NUMBER` | ❌ | – | WhatsApp sender number |

### Business Constants (`app/config/constants.py`)
```python
BROKER_NAME    = "Ajit Jawale"
AGENCY_NAME    = "Sunrise Properties"
OFFICE_ADDRESS = "A-203 Pearl Plaza, Andheri West, Mumbai 400053"
BROKER_PHONE   = "+91 98765 43210"
MAX_CALL_DURATION_SECONDS = 300   # 5 minutes
```

### Conversation Tuning (`app/agent/entrypoint.py`)
```python
AgentSession(
    min_endpointing_delay=0.25,    # start processing ~250ms after user stops
    max_endpointing_delay=2.0,     # cap the wait before forcing processing
    preemptive_generation=True,    # begin LLM generation early
    allow_interruptions=True,      # enable barge-in
    min_interruption_duration=0.4, # 400ms to trigger interruption
    min_interruption_words=2,      # need ~2 words to interrupt
    user_away_timeout=20.0,        # detect silence/away after 20s
)
```

---

## 🔒 Security & Privacy
- **Local storage only** — all data lives in `data/` as JSON; recordings as WAV. No external DB. Use a proper database (PostgreSQL/MongoDB) and encryption for production
- **Secrets in `.env`** — never commit it; rotate keys regularly
- **CORS** is currently open (`allow_origins=["*"]`) for dashboard convenience — restrict it before deploying publicly
- **No authentication** on the dashboard or API yet — add auth before exposing the server beyond localhost
- **DNC / disputes** are tracked and force-end calls; legal/privacy threats are logged

> ⚠️ The server and API endpoints are currently unauthenticated. Do not expose them to the public internet without adding access controls.

---

## 🐛 Troubleshooting

| Symptom | Likely Cause / Fix |
|---------|--------------------|
| Agent connects but doesn't speak | Invalid/empty `OPENAI_API_KEY` (when `USE_SARVAM_LLM=false`), or no OpenAI credits. Check the agent worker logs |
| First word delayed | TTS prewarm runs automatically; check network latency to Sarvam |
| Agent doesn't hear the customer | Grant mic permission; check browser WebRTC console; try `STT_PROVIDER=deepgram` |
| Phone call fails | Verify `SIP_OUTBOUND_TRUNK_ID` and phone format `+<country><number>` |
| No recording saved | Ensure `data/recordings/` is writable; check shutdown-callback logs |
| WhatsApp not sending | Stub mode — set `WHATSAPP_API_KEY` and implement the provider call in `app/core/whatsapp.py` |

---

## 🚧 Known Limitations
- JSON file storage (not suited for large lead volumes)
- WhatsApp integration is a stub (messages are queued/logged, not sent)
- No authentication on the dashboard/API
- One agent per call; no human handoff or call transfer
- Sarvam STT is non-streaming (batch per utterance); Deepgram is the streaming option

---

## 📊 Performance Notes
- TTS connection pooling + prewarm to cut first-byte latency
- Streaming `linear16` PCM from Sarvam with REST fallback
- Preemptive LLM generation and low endpointing delays (~250 ms)
- GPT-4o-mini is faster than Sarvam `sarvam-30b` for function calling

---

Built with [LiveKit](https://livekit.io), [Sarvam AI](https://sarvam.ai), [Deepgram](https://deepgram.com), and [OpenAI](https://openai.com).
