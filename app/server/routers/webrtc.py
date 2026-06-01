"""
WebRTC API — enables in-browser voice conversations with the agent.

Instead of dialing a phone number via SIP, this creates a LiveKit room
and returns a token so the browser can join directly via WebRTC.
The agent worker auto-joins the room and handles the conversation.
"""

import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from livekit import api

from app.config.settings import settings
from app.core.context import get_runtime_context
from app.core.data_store import data_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/token")
async def create_browser_call(payload: dict):
    """
    Create a LiveKit room and return a join token for the browser.

    The agent worker will auto-join the room when it detects a new room.
    The browser user joins as the "customer" participant.

    Request body:
        name: Customer display name
        phone: Customer phone (for context, not dialed)
        language: Preferred language code (optional)
    """
    name = payload.get("name", "Browser User")
    phone = payload.get("phone", "+910000000000")
    language = payload.get("language", settings.default_language)

    # Unique room name
    room_name = f"web-{phone.replace('+', '')}-{int(time.time())}"

    # Room metadata carries customer context for the agent
    room_metadata = json.dumps({
        "customer_name": name,
        "customer_phone": phone,
        "language": language,
        **get_runtime_context(),
    })

    lk_api = api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    try:
        # Create the room — agent worker will auto-join
        await lk_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=room_metadata,
                empty_timeout=120,
                max_participants=3,
            )
        )
        logger.info("Created WebRTC room: %s for %s", room_name, name)

    finally:
        await lk_api.aclose()

    # Generate a join token for the browser participant
    token = api.AccessToken(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    token.with_identity(f"customer-{phone}")
    token.with_name(name)
    token.with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )

    jwt_token = token.to_jwt()

    # Update lead status if this phone exists in leads
    data_store.update_lead_status(
        phone, "called", called_at=time.strftime("%Y-%m-%dT%H:%M:%S")
    )

    return {
        "ok": True,
        "token": jwt_token,
        "room_name": room_name,
        "livekit_url": settings.livekit_url,
    }
