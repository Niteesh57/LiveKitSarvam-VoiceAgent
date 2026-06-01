"""
Calls API — triggers outbound calls via LiveKit SIP.

Creates a LiveKit room with customer metadata, then dispatches
a SIP participant to dial the customer through Plivo SIP trunk.
The agent worker automatically joins the room and handles the conversation.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse

from livekit import api

from app.config.settings import settings
from app.config.constants import (
    BATCH_STAGGER_MIN_SECONDS,
    BATCH_STAGGER_MAX_SECONDS,
    BATCH_STAGGER_DEFAULT_SECONDS,
)
from app.core.context import get_runtime_context
from app.core.data_store import data_store

logger = logging.getLogger(__name__)

router = APIRouter()


async def _create_livekit_call(name: str, phone: str) -> str:
    """
    Create a LiveKit room and dispatch a SIP call to the customer.

    Flow:
    1. Create a room with customer metadata
    2. Agent worker auto-joins (via LiveKit's agent dispatch)
    3. SIP participant dials the customer's phone via Plivo trunk

    Returns:
        Room name for tracking
    """
    lk_api = api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    # Unique room name per call
    room_name = f"call-{phone.replace('+', '')}-{int(time.time())}"

    # Room metadata carries customer context for the agent
    room_metadata = json.dumps({
        "customer_name": name,
        "customer_phone": phone,
        "language": settings.default_language,
        **get_runtime_context(),
    })

    try:
        # Step 1: Create the room
        await lk_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=room_metadata,
                empty_timeout=60,  # Close room 60s after last participant leaves
                max_participants=3,  # Agent + Customer + optional monitor
            )
        )
        logger.info("Created room: %s", room_name)

        # Step 2: Dispatch SIP call to customer's phone
        sip_request = api.CreateSIPParticipantRequest(
            sip_trunk_id=settings.sip_outbound_trunk_id,
            sip_call_to=phone,
            room_name=room_name,
            participant_identity=f"customer-{phone}",
            participant_name=name,
        )
        await lk_api.sip.create_sip_participant(sip_request)
        logger.info("SIP call dispatched to %s in room %s", phone, room_name)

    finally:
        await lk_api.aclose()

    return room_name


@router.post("")
async def trigger_call(payload: dict):
    """Trigger a single outbound call to a customer."""
    name = payload.get("name")
    phone = payload.get("phone")

    if not name or not phone:
        return JSONResponse({"error": "name + phone required"}, status_code=400)

    if not settings.sip_outbound_trunk_id:
        return JSONResponse(
            {"error": "SIP trunk not configured. Use browser WebRTC calls instead (POST /api/webrtc/token)."},
            status_code=400,
        )

    try:
        room_name = await _create_livekit_call(name, phone)

        # Update lead status
        data_store.update_lead_status(
            phone, "called", called_at=time.strftime("%Y-%m-%dT%H:%M:%S")
        )

        return {"ok": True, "room_name": room_name, "phone": phone}

    except Exception as e:
        logger.error("Failed to create call for %s: %s", phone, e)
        return JSONResponse({"error": str(e)}, status_code=500)


async def _batch_dial(leads_to_call: list[dict], stagger_sec: int):
    """Background task: dial multiple leads with stagger delay."""
    for i, lead in enumerate(leads_to_call):
        if i > 0:
            await asyncio.sleep(stagger_sec)

        try:
            room_name = await _create_livekit_call(lead["name"], lead["phone"])
            data_store.update_lead_status(
                lead["phone"], "called", called_at=time.strftime("%Y-%m-%dT%H:%M:%S")
            )
            logger.info("Batch: dialed %s (%s) -> room %s", lead["name"], lead["phone"], room_name)

        except Exception as e:
            logger.error("Batch call failed for %s: %s", lead["phone"], e)


@router.post("/batch")
async def call_batch(payload: dict, bg: BackgroundTasks):
    """Batch-dial all pending leads with configurable stagger between calls."""
    stagger = max(
        BATCH_STAGGER_MIN_SECONDS,
        min(BATCH_STAGGER_MAX_SECONDS, int(payload.get("stagger_sec", BATCH_STAGGER_DEFAULT_SECONDS))),
    )

    leads = data_store.get_leads()
    pending = [lead for lead in leads if lead["status"] == "pending"]

    if not pending:
        return {"queued": 0, "msg": "No pending leads"}

    bg.add_task(_batch_dial, pending, stagger)
    return {"queued": len(pending), "stagger_sec": stagger}
