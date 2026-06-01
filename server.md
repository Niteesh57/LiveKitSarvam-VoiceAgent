"""
Sunrise  Agent DEMO — Standalone Vapi Warm-Caller
=====================================================

3-file demo: server.py + ui.html + prompt.md
Standalone — writes to local JSON files, zero external DB.

SETUP:
  pip install fastapi uvicorn requests python-dotenv pyngrok python-multipart

  Create .env (see .env.example below)

RUN:
  python server.py
  → browser opens to http://localhost:8000
  → ngrok tunnel printed in console
"""

import os, sys, json, csv, io, asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
import requests, uvicorn, webbrowser, threading

load_dotenv()

# ─── ENV ───────────────────────────────────────────────────────────────────
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")
PORT = int(os.getenv("PORT", "8000"))

# ─── HARDCODED BROKER CONFIG ───────────────────────────────────────────────
BROKER_NAME = "Ajit Jawale"
AGENCY_NAME = "Sunrise Properties"
OFFICE_ADDRESS = "A-203 Pearl Plaza, Andheri West, Mumbai 400053"
BROKER_PHONE = "+91 98765 43210"

# ─── FILES ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
LEADS_FILE = ROOT / "leads.json"
BOOKINGS_FILE = ROOT / "bookings.json"
PROMPT_FILE = ROOT / "prompt.md"
UI_FILE = ROOT / "ui.html"

def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

# ─── DYNAMIC IST DATE + WEEKEND SLOTS ──────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

def get_runtime_context():
    """Computed fresh on every call. Always returns next 2 upcoming weekend slots at 11 AM IST."""
    now = datetime.now(IST)
    today = now.date()
    wd = today.weekday()  # Mon=0..Sun=6
    days_to_sat = (5 - wd) % 7
    if days_to_sat == 0 and now.hour >= 11:
        days_to_sat = 7
    days_to_sun = (6 - wd) % 7
    if days_to_sun == 0 and now.hour >= 11:
        days_to_sun = 7
    slots = sorted([today + timedelta(days=days_to_sat), today + timedelta(days=days_to_sun)])
    return {
        "today_human": now.strftime("%A, %B %d, %Y at %I:%M %p IST"),
        "slot_1": f"{slots[0].strftime('%A %B %d')} at 11 AM",
        "slot_2": f"{slots[1].strftime('%A %B %d')} at 11 AM",
        "broker_name": BROKER_NAME,
        "agency_name": AGENCY_NAME,
        "office_address": OFFICE_ADDRESS,
        "broker_phone": BROKER_PHONE,
    }

# ─── PROMPT LOADING + VARIABLE INJECTION ───────────────────────────────────
def get_prompt(customer_name, customer_phone):
    if not PROMPT_FILE.exists():
        raise FileNotFoundError("prompt.md not found — create it from artifact")
    p = PROMPT_FILE.read_text()
    ctx = get_runtime_context()
    return (p
        .replace("{{customer_name}}", customer_name)
        .replace("{{customer_phone}}", customer_phone)
        .replace("{{broker_name}}", ctx["broker_name"])
        .replace("{{agency_name}}", ctx["agency_name"])
        .replace("{{office_address}}", ctx["office_address"])
        .replace("{{broker_phone}}", ctx["broker_phone"])
        .replace("{{slot_1}}", ctx["slot_1"])
        .replace("{{slot_2}}", ctx["slot_2"])
        .replace("{{today_human}}", ctx["today_human"])
    )

# ─── VAPI ASSISTANT BUILDER ────────────────────────────────────────────────
def build_assistant(customer_name, customer_phone, webhook_url):
    return {
        "name": "Sunrise  Agent Demo",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.6,
            "maxTokens": 150,
            "messages": [{"role": "system", "content": get_prompt(customer_name, customer_phone)}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "book_appointment",
                        "description": "Book office meeting with broker. Call AFTER customer agrees to a specific slot.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_name": {"type": "string"},
                                "customer_phone": {"type": "string"},
                                "slot_chosen": {"type": "string", "description": "exact {{slot_1}} or {{slot_2}} text"},
                                "notes": {"type": "string"},
                            },
                            "required": ["customer_name", "customer_phone", "slot_chosen"],
                        },
                    },
                    "server": {"url": f"{webhook_url}/tool/book_appointment"},
                },
                {
                    "type": "function",
                    "function": {
                        "name": "log_call_outcome",
                        "description": "Log final outcome. MUST invoke before goodbye.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_phone": {"type": "string"},
                                "outcome": {
                                    "type": "string",
                                    "enum": ["appointment_booked", "callback_requested",
                                             "not_interested_now", "dnc_requested",
                                             "customer_busy_reschedule"],
                                },
                                "notes": {"type": "string"},
                            },
                            "required": ["customer_phone", "outcome"],
                        },
                    },
                    "server": {"url": f"{webhook_url}/tool/log_call_outcome"},
                },
            ],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "sarah",
            "model": "eleven_turbo_v2_5",
            "stability": 0.5,
            "optimizeStreamingLatency": 3,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "hi",
            "confidenceThreshold": 0.6,
        },
        "firstMessage": "",
        "firstMessageMode": "assistant-speaks-first-with-model-generated-message",
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 240,
        "endCallFunctionEnabled": True,
        "backgroundDenoisingEnabled": True,
        "startSpeakingPlan": {
            "smartEndpointingPlan": {
                "provider": "livekit",
                "waitFunction": "(100 + 100 * x + 50) / 1",
            }
        },
        "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.3, "backoffSeconds": 0.5},
    }

# ─── FASTAPI ───────────────────────────────────────────────────────────────
app = FastAPI()
WEBHOOK_URL = None

@app.get("/", response_class=HTMLResponse)
async def home():
    return UI_FILE.read_text()

@app.get("/api/context")
async def api_context():
    return get_runtime_context()

@app.get("/api/leads")
async def get_leads():
    return load_json(LEADS_FILE, [])

@app.post("/api/leads/add")
async def lead_add(payload: dict):
    name = payload.get("name", "").strip()
    phone = payload.get("phone", "").strip()
    if not name or not phone.startswith("+"):
        return JSONResponse({"error": "name + phone (with +country code) required"}, status_code=400)
    leads = load_json(LEADS_FILE, [])
    if any(l["phone"] == phone for l in leads):
        return JSONResponse({"error": f"Phone {phone} already loaded"}, status_code=400)
    leads.append({"name": name, "phone": phone, "status": "pending"})
    save_json(LEADS_FILE, leads)
    return {"ok": True, "total": len(leads)}

@app.delete("/api/leads")
async def leads_clear():
    save_json(LEADS_FILE, [])
    return {"ok": True}

@app.post("/api/leads/csv")
async def leads_csv(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    existing = load_json(LEADS_FILE, [])
    existing_phones = {l["phone"] for l in existing}
    added = 0
    for row in reader:
        if len(row) >= 2 and row[1].strip().startswith("+"):
            phone = row[1].strip()
            if phone not in existing_phones:
                existing.append({"name": row[0].strip(), "phone": phone, "status": "pending"})
                existing_phones.add(phone)
                added += 1
    save_json(LEADS_FILE, existing)
    return {"loaded": added, "total": len(existing)}

@app.post("/api/call")
async def trigger_call(payload: dict):
    name = payload.get("name")
    phone = payload.get("phone")
    if not name or not phone:
        return JSONResponse({"error": "name + phone required"}, status_code=400)
    if not WEBHOOK_URL:
        return JSONResponse({"error": "Webhook URL not initialized"}, status_code=500)
    assistant = build_assistant(name, phone, WEBHOOK_URL)
    resp = requests.post(
        "https://api.vapi.ai/call",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"},
        json={
            "phoneNumberId": VAPI_PHONE_NUMBER_ID,
            "customer": {"number": phone, "name": name},
            "assistant": assistant,
        },
    )
    if resp.status_code in (200, 201):
        leads = load_json(LEADS_FILE, [])
        for l in leads:
            if l["phone"] == phone:
                l["status"] = "called"
                l["called_at"] = datetime.now().isoformat()
        save_json(LEADS_FILE, leads)
        return resp.json()
    return JSONResponse({"error": resp.text}, status_code=resp.status_code)

async def batch_dial(leads_to_call, stagger_sec):
    for i, l in enumerate(leads_to_call):
        if i > 0:
            await asyncio.sleep(stagger_sec)
        try:
            assistant = build_assistant(l["name"], l["phone"], WEBHOOK_URL)
            resp = requests.post(
                "https://api.vapi.ai/call",
                headers={"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "phoneNumberId": VAPI_PHONE_NUMBER_ID,
                    "customer": {"number": l["phone"], "name": l["name"]},
                    "assistant": assistant,
                },
            )
            if resp.status_code in (200, 201):
                all_leads = load_json(LEADS_FILE, [])
                for x in all_leads:
                    if x["phone"] == l["phone"]:
                        x["status"] = "called"
                        x["called_at"] = datetime.now().isoformat()
                save_json(LEADS_FILE, all_leads)
                print(f"📞 Batch: dialed {l['name']} ({l['phone']})")
            else:
                print(f"❌ Batch failed for {l['phone']}: {resp.text}")
        except Exception as e:
            print(f"❌ Batch error for {l['phone']}: {e}")

@app.post("/api/call/batch")
async def call_batch(payload: dict, bg: BackgroundTasks):
    stagger = max(5, min(300, int(payload.get("stagger_sec", 30))))
    leads = load_json(LEADS_FILE, [])
    pending = [l for l in leads if l["status"] == "pending"]
    if not pending:
        return {"queued": 0, "msg": "No pending leads"}
    bg.add_task(batch_dial, pending, stagger)
    return {"queued": len(pending), "stagger_sec": stagger}

@app.get("/api/bookings")
async def get_bookings():
    return load_json(BOOKINGS_FILE, [])

# ─── VAPI TOOL WEBHOOKS ────────────────────────────────────────────────────
def extract_tool_args(body):
    tc = body.get("message", {}).get("toolCalls", [{}])[0]
    args = tc.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        args = json.loads(args)
    return tc.get("id"), args

@app.post("/tool/book_appointment")
async def book_appointment(request: Request):
    body = await request.json()
    tc_id, args = extract_tool_args(body)
    booking = {"booked_at": datetime.now().isoformat(), "type": "appointment_booked", **args}
    b = load_json(BOOKINGS_FILE, [])
    b.append(booking)
    save_json(BOOKINGS_FILE, b)
    print(f"\n🎉 BOOKED: {args.get('customer_name')} → {args.get('slot_chosen')}\n")
    return {"results": [{"toolCallId": tc_id,
        "result": f"Booked {args.get('customer_name')} for {args.get('slot_chosen')}. Office address will be sent via WhatsApp."}]}

@app.post("/tool/log_call_outcome")
async def log_outcome(request: Request):
    body = await request.json()
    tc_id, args = extract_tool_args(body)
    entry = {"booked_at": datetime.now().isoformat(), **args}
    b = load_json(BOOKINGS_FILE, [])
    b.append(entry)
    save_json(BOOKINGS_FILE, b)
    print(f"\n📝 OUTCOME: {args.get('outcome')} for {args.get('customer_phone')}\n")
    return {"results": [{"toolCallId": tc_id, "result": f"Logged: {args.get('outcome')}"}]}

@app.post("/")
async def vapi_catchall(request: Request):
    body = await request.json()
    print(f"[webhook] {body.get('message', {}).get('type', '?')}")
    return {"ok": True}

# ─── MAIN ──────────────────────────────────────────────────────────────────
def serve():
    global WEBHOOK_URL
    try:
        from pyngrok import ngrok
        token = os.getenv("NGROK_AUTHTOKEN")
        if token:
            ngrok.set_auth_token(token)
        tunnel = ngrok.connect(PORT)
        WEBHOOK_URL = tunnel.public_url
        print(f"\n🌐 Public webhook URL: {WEBHOOK_URL}")
    except Exception as e:
        print(f"⚠️  ngrok unavailable ({e}); calls won't reach webhooks!")
        WEBHOOK_URL = f"http://localhost:{PORT}"
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    print(f"\n🚀 UI → http://localhost:{PORT}\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")

if __name__ == "__main__":
    serve()
