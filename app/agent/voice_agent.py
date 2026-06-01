"""
BrokerAssistant — The LiveKit Agent class for warm follow-up calls.

This agent handles the full conversation lifecycle:
- Warm greeting in Hindi/Hinglish/Marathi/English
- Natural conversation flow
- Appointment booking via function tools
- Call outcome logging
- Multi-language support with dynamic switching
"""

import logging
from datetime import datetime

from livekit.agents import Agent, RunContext, function_tool

from app.core.data_store import data_store
from app.config.constants import VALID_OUTCOMES

logger = logging.getLogger(__name__)


class BrokerAssistant(Agent):
    """
    LiveKit Agent for Sunrise Properties warm follow-up calls.

    Handles multi-language conversations (Hindi, English, Marathi, Hinglish)
    with function tools for booking appointments and logging outcomes.
    """

    def __init__(
        self,
        customer_name: str,
        customer_phone: str,
        system_prompt: str,
    ):
        super().__init__(instructions=system_prompt)
        self.customer_name = customer_name
        self.customer_phone = customer_phone

    @function_tool
    async def book_appointment(
        self,
        context: RunContext,
        customer_name: str,
        customer_phone: str,
        slot_chosen: str,
        notes: str = "",
    ) -> dict:
        """
        Book an office meeting with the broker.
        Call this ONLY AFTER the customer explicitly agrees to a specific day and time.

        Args:
            customer_name: Full name of the customer
            customer_phone: Phone number with country code (e.g., +919876543210)
            slot_chosen: The exact day and time the customer confirmed (e.g., "Saturday June 7 at 11 AM")
            notes: Additional context about the booking
        """
        booking = {
            "booked_at": datetime.now().isoformat(),
            "type": "appointment_booked",
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "slot_chosen": slot_chosen,
            "notes": notes,
        }

        data_store.add_booking(booking)
        data_store.update_lead_status(customer_phone, "booked")

        logger.info(
            "Appointment booked: %s -> %s", customer_name, slot_chosen
        )

        return {
            "status": "confirmed",
            "message": (
                f"Booked {customer_name} for {slot_chosen}. "
                "Office address will be sent via WhatsApp."
            ),
        }

    @function_tool
    async def log_call_outcome(
        self,
        context: RunContext,
        customer_phone: str,
        outcome: str,
        notes: str = "",
    ) -> dict:
        """
        Log the final call outcome. You MUST invoke this before saying goodbye.
        This must be the last tool call in every conversation.

        Args:
            customer_phone: Phone number with country code
            outcome: One of: appointment_booked, callback_requested,
                     not_interested_now, dnc_requested, customer_busy_reschedule
            notes: Brief summary of the conversation
        """
        if outcome not in VALID_OUTCOMES:
            return {
                "status": "error",
                "message": f"Invalid outcome. Must be one of: {VALID_OUTCOMES}",
            }

        entry = {
            "booked_at": datetime.now().isoformat(),
            "customer_phone": customer_phone,
            "outcome": outcome,
            "notes": notes,
        }

        data_store.add_booking(entry)
        data_store.update_lead_status(customer_phone, "completed", outcome=outcome)

        logger.info("Call outcome logged: %s -> %s", customer_phone, outcome)

        return {"status": "logged", "outcome": outcome}

    @function_tool
    async def switch_language(
        self,
        context: RunContext,
        language: str,
    ) -> dict:
        """
        Switch the conversation language when the customer requests it or
        seems more comfortable in a different language.

        Args:
            language: Target language - one of: hindi, english, marathi, hinglish, marathienglish
        """
        language_map = {
            "hindi": "Hindi",
            "english": "English",
            "marathi": "Marathi",
            "hinglish": "Hindi-English mix (Hinglish)",
            "marathienglish": "Marathi-English mix",
        }

        display_name = language_map.get(language.lower(), language)

        logger.info(
            "Language switch requested: %s for %s",
            display_name,
            self.customer_phone,
        )

        return {
            "status": "switched",
            "language": display_name,
            "instruction": (
                f"Now continue the conversation entirely in {display_name}. "
                "Maintain the same warm, friendly tone. Do not announce the switch explicitly "
                "unless the customer asked for it — just naturally continue in the new language."
            ),
        }

    @function_tool
    async def end_call(
        self,
        context: RunContext,
        reason: str,
    ) -> dict:
        """
        Gracefully end the call. Call this AFTER log_call_outcome and your final goodbye.
        Use this when:
        - Customer said goodbye
        - Appointment is booked and confirmed
        - Customer clearly wants to end the conversation
        - Customer said "don't call again"
        - Conversation has naturally concluded
        - You've said your final goodbye

        Args:
            reason: Brief reason for ending (e.g., "appointment booked", "customer said bye", "not interested")
        """
        logger.info(
            "Call ending for %s: %s", self.customer_phone, reason
        )

        # Schedule session close after a brief delay to let final audio play
        import asyncio

        async def _close_session():
            await asyncio.sleep(3)  # Let final goodbye audio finish playing
            session = self.session
            if session:
                await session.aclose()

        asyncio.create_task(_close_session())

        return {
            "status": "ending",
            "message": f"Call ending: {reason}. Goodbye audio will play then disconnect.",
        }
