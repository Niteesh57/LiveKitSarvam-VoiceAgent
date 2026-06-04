# 🏠 Sunrise Properties - AI Voice Agent

An enterprise-grade AI-powered voice assistant for real estate brokers, built with LiveKit, Sarvam AI, and OpenAI GPT-4o-mini. Handles warm follow-up calls, appointment booking, and lead management with natural Hindi/Hinglish conversations.

## 🌟 Features

### 🎙️ Voice Conversation Engine
- **Multi-modal Input**: Browser-based WebRTC voice calls + phone calling via SIP
- **Natural Speech**: Devanagari Hindi script for accurate pronunciation
- **Low-latency Pipeline**: Optimized STT → LLM → TTS flow (< 2s response time)
- **Streaming STT**: Real-time speech recognition with Deepgram Nova-3 or Sarvam Saaras v3
- **High-quality TTS**: Sarvam Bulbul v3 at 48kHz with persistent connection pooling
- **Interruption Handling**: Natural barge-in support for human-like conversations
- **Multi-language**: Hindi, English, Marathi, Hinglish, and Marathi-English mix

### 🧠 Intelligent Conversation Management
- **Emotional Tone Adaptation**: Detects and mirrors customer emotions (angry, excited, sad, rushed)
- **Trust Verification**: Handles "who is this?" / suspicion gracefully
- **Competitor Handling**: Professional responses when customers mention other brokers
- **Context Memory**: Remembers previous conversations, preferences, budget, timeline
- **Natural Fillers**: Uses "अच्छा", "हाँ जी", "बिल्कुल" for human-like responses
- **Ultra-short Responses**: Max 1-2 sentences per turn for natural flow
- **Smart Call Closing**: Mandatory "और कुछ पूछना था जी?" confirmation sequence

### 📞 Advanced Call Features
- **Call Recording**: Built-in LiveKit recording with automatic archival
- **Auto-disconnect**: Intelligent call termination after natural closure
- **Max Duration Enforcement**: Automatic call wrap-up after 300 seconds
- **Silence Detection**: Prompts unresponsive customers, ends after 2 attempts
- **Wrong Number Detection**: Automatically handles wrong number scenarios
- **Dispute Management**: Deterministic termination for privacy/legal threats

### 🎯 Enterprise Features

#### Lead Management
- **Lead Status Tracking**: pending, called, booked, completed, wrong_number, existing_customer
- **Lead Scoring**: Hot, warm, cool, cold, dead (based on interaction outcomes)
- **Bulk Operations**: Add multiple leads via CSV/JSON, delete all, batch delete
- **Lead Selector**: Quick customer selection from dashboard

#### Analytics & Reporting
- **Call Duration Tracking**: Monitors time spent per customer
- **Lead Scoring**: Automatic scoring based on conversation outcomes
- **Call Outcome Logging**: Tracks appointment_booked, callback_requested, not_interested_now, dnc_requested
- **Conversation History**: Stores summaries, preferences, budget, property type

#### Appointment Management
- **Smart Booking**: Validates appointment times (rejects past times)
- **Reminder System**: Automatic 1-day-before appointment reminders
- **Callback Scheduling**: Captures customer-preferred callback times

#### WhatsApp Integration (Stub)
- **Post-call Thank You**: Queued WhatsApp messages after calls
- **Appointment Confirmation**: Office address and details via WhatsApp
- **Appointment Reminders**: Day-before reminder messages
- **Property Details**: Follow-up with brochures and listings

#### Safety & Compliance
- **DND Compliance**: 9 AM - 9 PM calling window (configurable)
- **Privacy Handling**: Graceful handling of consent/privacy complaints
- **Legal Threat Protection**: Auto-ends calls with one apology, logs dispute
- **Content Moderation**: Refuses abusive, sexual, or inappropriate content
- **Wrong Number Tracking**: Automatically removes invalid numbers

### 🔧 Corner Case Handling

#### Customer Scenarios
- ✅ Wrong person / number changed
- ✅ Customer driving / can't talk now
- ✅ Customer already booked / already visited
- ✅ Legal threats / privacy complaints
- ✅ Elderly / slow speakers (adaptive pacing)
- ✅ Rushed / impatient customers (quick pitch)
- ✅ Skeptical / guarded customers (trust building)
- ✅ Competitor comparisons (confident positioning)
- ✅ "Who is this?" / suspicion (transparent introduction)
- ✅ Budget concerns (options at all price points)
- ✅ Wants WhatsApp details (offer both, nudge office)

#### Technical Edge Cases
- ✅ STT confusion / repetition requests (rephrases in simpler words)
- ✅ Unsupported languages (offers Hindi/English/Marathi)
- ✅ Past appointment times (politely corrects)
- ✅ No remote participants (auto-ends call after 5s)
- ✅ Connection drops (auto-reconnect + fallback disconnect)

## 🏗️ Architecture

### Voice Pipeline
```
User Voice → LiveKit Room
           ↓
   Silero VAD (Voice Activity Detection)
           ↓
   STT (Deepgram Nova-3 / Sarvam Saaras v3)
           ↓
   LLM (GPT-4o-mini / Sarvam sarvam-30b)
           ↓
   TTS (Sarvam Bulbul v3)
           ↓
   LiveKit Room → User Audio
```

### System Components

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Server                      │
│  (Dashboard UI + REST API + WebRTC Token Service)   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ├── /api/webrtc/token (browser calls)
                    ├── /api/call (phone calls via SIP)
                    ├── /api/leads (CRUD operations)
                    ├── /api/bookings (view appointments)
                    ├── /api/recordings (call playback)
                    └── /api/analytics (dashboard stats)
                    │
                    ↓
┌─────────────────────────────────────────────────────┐
│              LiveKit Cloud / Server                  │
│         (WebRTC rooms + SIP trunking)                │
└───────────────────┬─────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────┐
│            LiveKit Agent Worker                      │
│  (Voice pipeline: VAD → STT → LLM → TTS)            │
└───────────────────┬─────────────────────────────────┘
                    │
                    ├── BrokerAssistant (Agent logic)
                    ├── PromptEngine (Dynamic prompts)
                    ├── DataStore (JSON persistence)
                    ├── Analytics (Lead scoring)
                    ├── Memory (Conversation history)
                    ├── WhatsApp (Message queuing)
                    ├── Scheduler (DND compliance)
                    └── Reminders (Appointment alerts)
```

### File Structure

```
LiveKitSarvam/
├── app/
│   ├── agent/
│   │   ├── entrypoint.py           # Agent session setup
│   │   ├── voice_agent.py          # BrokerAssistant class + tools
│   │   └── sarvam_plugins/
│   │       ├── stt.py              # Sarvam STT plugin
│   │       └── tts.py              # Sarvam TTS plugin (Bulbul v3)
│   │
│   ├── config/
│   │   ├── settings.py             # Environment config
│   │   └── constants.py            # Business constants
│   │
│   ├── core/
│   │   ├── data_store.py           # JSON file storage
│   │   ├── prompt_engine.py        # Prompt hydration
│   │   ├── memory.py               # Conversation history
│   │   ├── analytics.py            # Lead scoring
│   │   ├── whatsapp.py             # WhatsApp queue
│   │   ├── scheduler.py            # Call scheduling + DND
│   │   ├── reminders.py            # Appointment reminders
│   │   └── context.py              # Runtime context
│   │
│   └── server/
│       ├── app.py                  # FastAPI app factory
│       └── routers/
│           ├── webrtc.py           # Browser WebRTC tokens
│           ├── calls.py            # Phone calling (SIP)
│           ├── leads.py            # Lead CRUD
│           ├── bookings.py         # Appointments
│           ├── recordings.py       # Call recordings
│           ├── analytics.py        # Dashboard stats
│           ├── context.py          # Context API
│           └── dashboard.py        # Static file serving
│
├── data/                            # JSON data storage
│   ├── leads.json
│   ├── bookings.json
│   ├── conversations.json
│   ├── lead_scores.json
│   ├── call_durations.json
│   ├── reminders.json
│   ├── whatsapp_queue.json
│   └── recordings/                  # Call audio files
│
├── prompts/
│   └── system_prompt.md            # Agent system prompt
│
├── static/
│   └── index.html                  # Dashboard UI
│
├── run_server.py                   # Start FastAPI server
├── run_agent.py                    # Start LiveKit agent
├── requirements.txt
├── .env                            # Configuration (secrets)
└── README.md                       # This file
```

## 🚀 Setup

### Prerequisites
- Python 3.10+
- LiveKit Cloud account (or self-hosted LiveKit server)
- Sarvam AI API key
- OpenAI API key (for GPT-4o-mini)
- Deepgram API key (optional, for streaming STT)
- SIP trunk ID (optional, for phone calling)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd LiveKitSarvam
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file with your credentials:
   ```env
   # LiveKit Configuration
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=APIxxxxxxxxxxxxx
   LIVEKIT_API_SECRET=your-secret-key

   # Sarvam AI
   SARVAM_API_KEY=your-sarvam-api-key
   SARVAM_TTS_SPEAKER=ritu
   
   # STT Provider (deepgram or sarvam)
   STT_PROVIDER=deepgram
   DEEPGRAM_API_KEY=your-deepgram-api-key

   # OpenAI (for GPT-4o-mini LLM)
   OPENAI_API_KEY=your-openai-api-key
   USE_SARVAM_LLM=false

   # Optional: Phone Calling via SIP
   SIP_OUTBOUND_TRUNK_ID=your-sip-trunk-id

   # Server Configuration
   PORT=8000
   HOST=0.0.0.0
   DEBUG=false
   ```

4. **Get LiveKit Credentials**
   - Sign up at [LiveKit Cloud](https://cloud.livekit.io/)
   - Create a project
   - Copy `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` from dashboard

5. **Get Sarvam AI API Key**
   - Sign up at [Sarvam AI](https://www.sarvam.ai/)
   - Generate API key from dashboard
   - Add to `.env` as `SARVAM_API_KEY`

6. **Get Deepgram API Key** (optional, for streaming STT)
   - Sign up at [Deepgram](https://deepgram.com/)
   - Generate API key
   - Add to `.env` as `DEEPGRAM_API_KEY`
   - Set `STT_PROVIDER=deepgram`

7. **Get OpenAI API Key** (for GPT-4o-mini)
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Add credits to account
   - Generate API key
   - Add to `.env` as `OPENAI_API_KEY`

8. **Optional: Setup SIP Trunk** (for phone calling)
   - In LiveKit dashboard, create a SIP trunk
   - Configure trunk with phone provider (Twilio, Plivo, etc.)
   - Copy trunk ID to `.env` as `SIP_OUTBOUND_TRUNK_ID`

### Running the Application

You need to run **two processes** simultaneously:

#### Terminal 1: Start FastAPI Server
```bash
python run_server.py
```
- Opens dashboard at `http://localhost:8000`
- Provides REST API and WebRTC token service
- Auto-opens browser

#### Terminal 2: Start LiveKit Agent Worker
```bash
python run_agent.py dev
```
- Connects to LiveKit and waits for room assignments
- Handles voice pipeline (STT → LLM → TTS)
- Use `dev` mode for auto-reload during development

### Verify Setup
1. Dashboard should open at `http://localhost:8000`
2. Agent worker should show: `Connected to LiveKit`
3. Test browser call:
   - Enter name and phone (e.g., "+919876543210")
   - Click "Start Voice Call"
   - Grant microphone permission
   - Agent should greet you in Hinglish

## 📋 Usage

### Browser Voice Call (WebRTC)
1. Open dashboard at `http://localhost:8000`
2. Enter customer name, phone, and select language
3. Click **"Start Voice Call"**
4. Grant microphone permission when prompted
5. Speak naturally — the agent will respond in real-time
6. Click **"End Call"** when done

### Phone Call (SIP)
1. Configure `SIP_OUTBOUND_TRUNK_ID` in `.env`
2. Add lead with phone number (e.g., "+919876543210")
3. Click **"Call Phone"** button
4. Agent will call the number and handle conversation
5. Monitor call status in dashboard

### Lead Management
- **Add Single Lead**: Enter name + phone, click "Add"
- **Add Multiple Leads**: Click "Add Multiple", paste CSV/JSON format:
  ```
  Rahul Sharma, +919876543210
  Priya Patel, +919123456789
  ```
- **Delete Lead**: Click ✕ next to lead
- **Delete Multiple**: Check boxes, click "Delete Selected"
- **Delete All**: Click "Delete All" (requires confirmation)

### View Call Recordings
- Recordings stored in `data/recordings/`
- Access via `/api/recordings` endpoint
- Format: `call_<phone>_<timestamp>.wav`

### Analytics & Reports
- Lead scores: `data/lead_scores.json`
- Call durations: `data/call_durations.json`
- Conversation history: `data/conversations.json`
- Appointment reminders: `data/reminders.json`

## 🎛️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIVEKIT_URL` | ✅ | - | LiveKit WebSocket URL |
| `LIVEKIT_API_KEY` | ✅ | - | LiveKit API key |
| `LIVEKIT_API_SECRET` | ✅ | - | LiveKit API secret |
| `SARVAM_API_KEY` | ✅ | - | Sarvam AI API key |
| `SARVAM_TTS_SPEAKER` | ❌ | `ritu` | TTS voice (ritu/meera/etc.) |
| `STT_PROVIDER` | ❌ | `sarvam` | STT provider (deepgram/sarvam) |
| `DEEPGRAM_API_KEY` | ❌ | - | Deepgram API key (if using Deepgram STT) |
| `OPENAI_API_KEY` | ❌ | - | OpenAI API key (for GPT-4o-mini) |
| `USE_SARVAM_LLM` | ❌ | `false` | Use Sarvam sarvam-30b LLM |
| `SIP_OUTBOUND_TRUNK_ID` | ❌ | - | SIP trunk for phone calling |
| `PORT` | ❌ | `8000` | FastAPI server port |
| `HOST` | ❌ | `0.0.0.0` | Server bind address |
| `DEBUG` | ❌ | `false` | Enable debug logging |

### Conversation Tuning (in `entrypoint.py`)

```python
session = AgentSession(
    vad=silero.VAD.load(),
    stt=stt_instance,
    llm=llm_instance,
    tts=tts_instance,
    min_endpointing_delay=0.6,       # Wait 600ms after user stops
    max_endpointing_delay=3.0,       # Max 3s wait
    preemptive_generation=True,      # Start generating early
    allow_interruptions=True,        # Enable barge-in
    min_interruption_duration=0.4,   # 400ms to trigger barge-in
    min_interruption_words=2,        # Need 2 words to interrupt
    user_away_timeout=20.0,          # Detect silence after 20s
)
```

### Business Constants (in `constants.py`)

```python
BROKER_NAME = "Rajesh Kumar"
AGENCY_NAME = "Sunrise Properties"
OFFICE_ADDRESS = "Shop 12, Andheri West, Mumbai 400053"
BROKER_PHONE = "+91-22-12345678"
MAX_CALL_DURATION_SECONDS = 300    # 5 minutes
VALID_OUTCOMES = [
    "appointment_booked",
    "callback_requested",
    "not_interested_now",
    "dnc_requested",
    "customer_busy_reschedule",
]
```

## 🔌 API Endpoints

### WebRTC Voice Calls
- `POST /api/webrtc/token` - Create room + token for browser call
  ```json
  {
    "name": "Customer Name",
    "phone": "+919876543210",
    "language": "hi-EN"
  }
  ```

### Phone Calling
- `POST /api/call` - Initiate phone call via SIP
  ```json
  {
    "name": "Customer Name",
    "phone": "+919876543210"
  }
  ```

### Lead Management
- `GET /api/leads` - List all leads
- `POST /api/leads/add` - Add single lead
- `POST /api/leads/bulk` - Add multiple leads
- `POST /api/leads/delete` - Delete single lead
- `POST /api/leads/delete-batch` - Delete multiple leads
- `DELETE /api/leads` - Delete all leads

### Bookings & Appointments
- `GET /api/bookings` - List all bookings
- `GET /api/bookings/<phone>` - Get bookings for specific customer

### Call Recordings
- `GET /api/recordings` - List all recordings
- `GET /api/recordings/<filename>` - Download recording

### Analytics
- `GET /api/analytics/lead-scores` - Lead scoring data
- `GET /api/analytics/call-durations` - Call duration statistics

### Status
- `GET /api/status` - System status + configuration check

## 🧪 Testing

### Test Browser Call
1. Start server + agent
2. Open dashboard
3. Enter test data:
   - Name: "Test Customer"
   - Phone: "+919876543210"
   - Language: "Hinglish"
4. Click "Start Voice Call"
5. Say: "हैलो, main property dekh raha hoon"
6. Agent should respond naturally

### Test Phone Call (requires SIP trunk)
1. Add lead with your real phone number
2. Click "Call Phone"
3. Answer the call on your phone
4. Have a natural conversation
5. Check recording in `data/recordings/`

### Test Lead Management
1. Add single lead via UI
2. Add multiple leads via "Add Multiple"
3. Test batch delete with checkboxes
4. Test "Delete All" functionality
5. Verify data in `data/leads.json`

### Test Call Recording
1. Complete a call (browser or phone)
2. Check `data/recordings/` folder
3. Verify WAV file exists with correct naming
4. Test playback via `/api/recordings/<filename>`

## 🐛 Troubleshooting

### Agent Not Greeting
- **Symptom**: Call connects but agent doesn't speak
- **Fix**: Check `run_agent.py` logs for LLM errors
- **Common Cause**: Invalid OpenAI API key or no credits

### Voice Jitter / Delay
- **Symptom**: First word takes long time to play
- **Fix**: TTS prewarm is enabled by default in `entrypoint.py`
- **Check**: Network latency to Sarvam API

### STT Not Working
- **Symptom**: Agent doesn't hear customer speech
- **Fix**: Ensure microphone permission granted in browser
- **Check**: Browser console for WebRTC errors
- **Alternative**: Switch STT provider in `.env`:
  ```env
  STT_PROVIDER=deepgram
  DEEPGRAM_API_KEY=your-key
  ```

### Call Not Ending Properly
- **Symptom**: UI shows "active" after call ends
- **Fix**: Already implemented — multiple disconnect listeners
- **Check**: Browser console for JavaScript errors

### Wrong Number / No Answer
- **Symptom**: SIP call fails to connect
- **Fix**: Verify phone number format: `+<country><number>`
- **Check**: SIP trunk configuration in LiveKit dashboard

### Recording Not Saved
- **Symptom**: No WAV file after call
- **Fix**: Ensure `data/recordings/` folder exists
- **Check**: Agent logs for shutdown callback errors

### Lead Score Not Updating
- **Symptom**: Scores remain default after calls
- **Fix**: Verify `log_call_outcome` tool is called in conversation
- **Check**: `data/lead_scores.json` for updates

### WhatsApp Not Sending
- **Symptom**: Messages queued but not sent
- **Note**: WhatsApp integration is stub-only (saves to queue)
- **Implementation**: Add Twilio/Plivo integration in `whatsapp.py`

## 📊 Performance Optimizations

### Current Optimizations
- ✅ TTS connection pooling (persistent HTTP)
- ✅ TTS prewarm (eliminates first-word jitter)
- ✅ Streaming STT (Deepgram Nova-3)
- ✅ Preemptive LLM generation
- ✅ Low endpointing delays (600ms)
- ✅ Fast barge-in (400ms)
- ✅ GPT-4o-mini (faster than Sarvam sarvam-30b)

### Response Times
- **STT Latency**: ~200-300ms (streaming)
- **LLM Latency**: ~800-1200ms (GPT-4o-mini)
- **TTS Latency**: ~300-500ms (Bulbul v3 with prewarm)
- **Total Response**: ~1.5-2.0s (end-to-end)

### Recommended for Production
- Use Deepgram for STT (faster streaming)
- Use GPT-4o-mini for LLM (2x faster than Sarvam)
- Enable TTS prewarm (already default)
- Use CDN for static assets
- Switch from JSON to PostgreSQL for data storage

## 🔒 Security & Privacy

### Data Storage
- All data stored locally in `data/` folder
- JSON files (not encrypted) — use encrypted DB in production
- Call recordings stored as WAV files
- No data sent to third parties (except API providers)

### API Keys
- Store in `.env` file (never commit to git)
- Use `.gitignore` to exclude `.env`
- Rotate keys regularly
- Use restricted API keys where possible

### Privacy Compliance
- DNC (Do Not Call) tracking in lead status
- Auto-removal for legal complaints
- Consent handling (records customer objections)
- Recording disclosure (mention in greeting)

### Content Moderation
- Refuses abusive/sexual content
- Logs inappropriate interactions
- Auto-ends calls on harassment
- No engagement with off-topic manipulation

## 🚧 Known Limitations

### Current Scope
- JSON file storage (not scalable to 1000+ leads)
- No real-time analytics dashboard (data in JSON files)
- WhatsApp integration is stub-only (queues messages)
- No CRM integration (Salesforce, HubSpot, etc.)
- No email notifications
- No multi-agent support (one agent per call)
- No call transfer or human handoff
- No sentiment analysis beyond basic tone detection

### Browser Compatibility
- Requires WebRTC support (Chrome, Firefox, Edge, Safari)
- Microphone permission required
- HTTPS required for production (localhost OK for dev)

### Language Support
- Hindi, English, Marathi, Hinglish well-supported
- Other Indian languages need additional STT/TTS models
- No translation layer (customer must speak supported language)

### Call Quality
- Depends on network quality (both customer + server)
- 48kHz audio recommended (default)
- Echo cancellation required for speaker mode

## 🛠️ Future Enhancements

### Near-term
- [ ] PostgreSQL database (replace JSON files)
- [ ] Real-time analytics dashboard with charts
- [ ] WhatsApp API integration (Twilio/Plivo)
- [ ] Email notifications for bookings
- [ ] CRM integration (Salesforce, Zoho)
- [ ] Multi-agent load balancing
- [ ] Call transfer to human broker
- [ ] Sentiment analysis visualization

### Long-term
- [ ] Multi-tenancy (multiple brokers/agencies)
- [ ] Voice cloning (broker's actual voice)
- [ ] Video call support (property tours)
- [ ] AR/VR property visualization
- [ ] Multilingual translation layer
- [ ] Automated follow-up campaigns
- [ ] Predictive lead scoring (ML models)
- [ ] Integration with property listing APIs

## 📝 License

This project is proprietary software developed for Sunrise Properties.

## 🤝 Contributing

This is an internal project. For bug reports or feature requests, contact the development team.

## 📧 Support

For technical support, contact:
- **Development Team**: `dev@sunriseproperties.com`
- **Business Queries**: `info@sunriseproperties.com`
- **Phone**: +91-22-12345678

---

Built with ❤️ using [LiveKit](https://livekit.io), [Sarvam AI](https://sarvam.ai), and [OpenAI](https://openai.com)
