"""
BrokerAssistant — The LiveKit Agent class for warm follow-up calls.

This agent handles the full conversation lifecycle:
- Warm greeting in Hindi/Hinglish/Marathi/English
- Natural conversation flow
- Appointment booking via function tools
- Call outcome logging
- Multi-language support with dynamic switching
- Conversation memory for customer context
- WhatsApp follow-up queuing
- Lead scoring updates
- Appointment reminders
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from livekit.agents import Agent, RunContext, function_tool

from app.core.data_store import data_store
from app.core.memory import save_conversation
from app.core.analytics import compute_lead_score
from app.core.whatsapp import (
    queue_post_call_thankyou,
    queue_appointment_confirmation,
    queue_appointment_reminder,
)
from app.config.constants import VALID_OUTCOMES

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


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
        # Validate: reject past times
        now = datetime.now(IST)
        slot_lower = slot_chosen.lower()

        # Deterministic safety check for UNAMBIGUOUS past-time markers only.
        # The LLM is instructed to handle past-time validation via the system
        # prompt; this is just a backstop.
        #
        # NOTE: "kal" (कल) is intentionally EXCLUDED here — in Hindi it means
        # BOTH "yesterday" AND "tomorrow". Matching it previously rejected
        # valid next-day bookings (e.g. "kal subah" = tomorrow morning),
        # which defeated the booking flow. Disambiguating "kal" requires real
        # date parsing, which the LLM handles contextually.
        past_markers = [
            "yesterday",
            "बीता", "बीते",      # beeta / beete (passed)
            "पिछले", "पिछला",     # pichhle / pichhla (last/previous)
            "गुज़रा", "गुजरा",     # guzra (gone by)
        ]
        if any(marker in slot_lower for marker in past_markers):
            return {
                "status": "error",
                "message": "वो time तो निकल गया जी। आज के बाद का कोई time बताइए?",
            }

        booking = {
            "booked_at": datetime.now(IST).isoformat(),
            "type": "appointment_booked",
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "slot_chosen": slot_chosen,
            "notes": notes,
        }

        data_store.add_booking(booking)
        data_store.update_lead_status(customer_phone, "booked")

        # Update lead score to "hot"
        data_store.update_lead_score(customer_phone, "hot")

        # Queue WhatsApp confirmation with office address
        queue_appointment_confirmation(customer_phone, customer_name, slot_chosen)

        # Queue reminder for 1 day before
        queue_appointment_reminder(customer_phone, customer_name, slot_chosen)

        logger.info(
            "Appointment booked: %s -> %s (reminder + WhatsApp queued)", customer_name, slot_chosen
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
            "booked_at": datetime.now(IST).isoformat(),
            "customer_phone": customer_phone,
            "outcome": outcome,
            "notes": notes,
        }

        data_store.add_booking(entry)
        data_store.update_lead_status(customer_phone, "completed", outcome=outcome)

        # Update lead score based on outcome
        score = compute_lead_score(outcome)
        data_store.update_lead_score(customer_phone, score)

        # Save conversation summary to memory
        save_conversation(
            phone=customer_phone,
            summary=notes or f"Call ended with outcome: {outcome}",
            outcome=outcome,
            preferences={},
        )

        # Queue WhatsApp follow-up (post-call thank you)
        if outcome != "dnc_requested":
            queue_post_call_thankyou(customer_phone, self.customer_name)

        logger.info(
            "Call outcome logged: %s -> %s (score: %s, WhatsApp queued)",
            customer_phone,
            outcome,
            score,
        )

        # DETERMINISTIC TERMINATION: for DNC, force-end the call immediately
        # without relying on the LLM to call end_call separately.
        if outcome == "dnc_requested":
            import asyncio
            asyncio.create_task(self._force_disconnect(delay=4.0))
            logger.info("DNC detected — forcing call termination for %s", customer_phone)

        return {"status": "logged", "outcome": outcome, "lead_score": score}

    async def _force_disconnect(self, delay: float = 4.0) -> None:
        """Force-close the session and delete the room after a delay."""
        import asyncio
        from livekit import api
        from app.config.settings import settings

        await asyncio.sleep(delay)
        session = self.session
        try:
            room = session._room if session else None
            if session:
                await session.aclose()
            if room and room.name:
                lk_api = api.LiveKitAPI(
                    url=settings.livekit_url,
                    api_key=settings.livekit_api_key,
                    api_secret=settings.livekit_api_secret,
                )
                await lk_api.room.delete_room(api.DeleteRoomRequest(room=room.name))
                await lk_api.aclose()
                logger.info("Force disconnect: room deleted %s", room.name)
        except Exception as e:
            logger.debug("Force disconnect (non-critical): %s", e)

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
    async def request_callback(
        self,
        context: RunContext,
        callback_time: str,
        notes: str = "",
    ) -> dict:
        """
        Capture a callback request when the customer is busy or wants to be called later.
        Use this when customer says things like "abhi busy hoon, shaam ko call karo",
        "kal call karna", "main drive kar raha hoon", etc.

        Args:
            callback_time: When to call back, in customer's words (e.g., "shaam 6 baje", "kal subah", "agle hafte")
            notes: Why they want a callback / any context
        """
        from app.core.scheduler import call_scheduler

        entry = {
            "booked_at": datetime.now(IST).isoformat(),
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "callback_time": callback_time,
            "notes": notes,
            "type": "callback_scheduled",
        }
        data_store.add_booking(entry)
        data_store.update_lead_score(self.customer_phone, "warm")

        logger.info(
            "Callback requested by %s at: %s",
            self.customer_phone,
            callback_time,
        )

        return {
            "status": "scheduled",
            "callback_time": callback_time,
            "message": f"Callback noted for {callback_time}.",
        }

    @function_tool
    async def mark_wrong_number(
        self,
        context: RunContext,
        notes: str = "",
    ) -> dict:
        """
        Call this when the person says it's a wrong number, the number changed,
        or they are NOT the customer you're looking for (e.g., "galat number",
        "yeh Rahul ka number nahi hai", "main woh nahi hoon").

        Logs the wrong number, removes the lead from active calling, and ends the call.

        Args:
            notes: Any context (e.g., "number reassigned to different person")
        """
        entry = {
            "booked_at": datetime.now(IST).isoformat(),
            "customer_phone": self.customer_phone,
            "outcome": "wrong_number",
            "notes": notes or "Wrong number / person not found",
            "type": "wrong_number",
        }
        data_store.add_booking(entry)
        data_store.update_lead_status(self.customer_phone, "wrong_number")
        data_store.update_lead_score(self.customer_phone, "dead")

        logger.info("Wrong number flagged for %s — ending call", self.customer_phone)

        import asyncio
        asyncio.create_task(self._force_disconnect(delay=3.0))

        return {
            "status": "wrong_number_logged",
            "message": "Wrong number logged. Call ending.",
        }

    @function_tool
    async def handle_dispute(
        self,
        context: RunContext,
        dispute_type: str,
        notes: str = "",
    ) -> dict:
        """
        Call this IMMEDIATELY when the customer raises a privacy complaint, legal threat,
        or says they will file a police complaint / court case / legal notice.
        Examples: "police complaint karunga", "case lagaunga", "notice bhejunga",
        "privacy breach", "consent ke bina number liya".

        Logs the dispute as DNC, marks the number for removal, and ENDS the call
        after ONE apology. Do NOT keep arguing — call this tool right away.

        Args:
            dispute_type: Type (e.g., "privacy_complaint", "legal_threat", "police_threat")
            notes: Brief context of what the customer said
        """
        entry = {
            "booked_at": datetime.now(IST).isoformat(),
            "customer_phone": self.customer_phone,
            "outcome": "dnc_requested",
            "notes": f"DISPUTE/{dispute_type}: {notes}",
            "type": "dispute",
        }
        data_store.add_booking(entry)
        data_store.update_lead_status(self.customer_phone, "completed", outcome="dnc_requested")
        data_store.update_lead_score(self.customer_phone, "dead")

        save_conversation(
            phone=self.customer_phone,
            summary=f"Customer raised {dispute_type}. Number marked DO NOT CALL.",
            outcome="dnc_requested",
            preferences={"do_not_call": "true", "dispute": dispute_type},
        )

        logger.warning(
            "DISPUTE (%s) from %s — number marked DNC, force-ending call",
            dispute_type,
            self.customer_phone,
        )

        import asyncio
        asyncio.create_task(self._force_disconnect(delay=5.0))

        return {
            "status": "dispute_logged",
            "instruction": (
                "Say ONE short apology and goodbye ONLY, then STOP completely: "
                "'जी, माफ़ कीजिए। आपका number remove कर दिया है, दोबारा call नहीं आएगी। "
                "किसी भी formal बात के लिए हमारा office address है। धन्यवाद।' "
                "Do NOT say anything after this. Do NOT argue. The call will disconnect."
            ),
        }

    @function_tool
    async def acknowledge_existing_customer(
        self,
        context: RunContext,
        status: str,
        notes: str = "",
    ) -> dict:
        """
        Call this when the customer says they have ALREADY visited the office,
        already booked, already met you, or are already dealing with the agency.
        Examples: "main toh kal office aaya tha", "already book kar liya".

        Updates their record so you don't repeat the office invite.

        Args:
            status: What they said (e.g., "already_visited", "already_booked", "already_met")
            notes: Any context
        """
        data_store.update_lead_status(self.customer_phone, "existing_customer", visit_note=notes)
        data_store.update_lead_score(self.customer_phone, "hot")

        save_conversation(
            phone=self.customer_phone,
            summary=f"Existing customer — {status}. {notes}",
            outcome="existing_customer",
            preferences={"existing_customer": status},
        )

        logger.info("Existing customer acknowledged: %s (%s)", self.customer_phone, status)

        return {
            "status": "acknowledged",
            "instruction": (
                "This is an existing customer. Do NOT pitch the office visit again. "
                "Warmly acknowledge, ask if they need further help, and if not, "
                "thank them and end the call."
            ),
        }

    @function_tool
    async def end_call(
        self,
        context: RunContext,
        reason: str,
    ) -> dict:
        """
        Gracefully end and disconnect the call. You MUST call this after saying your final goodbye.
        
        IMPORTANT: Call this immediately when:
        - You have said "धन्यवाद" or "bye" or any goodbye phrase
        - Customer said "bye", "okay bye", "theek hai", "chalega", "thanks", "thank you"
        - You have already called log_call_outcome
        - The conversation is clearly over
        
        Do NOT wait or ask more questions after goodbye. Just call end_call.

        Args:
            reason: Brief reason for ending (e.g., "appointment booked", "customer said bye", "not interested")
        """
        logger.info(
            "Call ending for %s: %s", self.customer_phone, reason
        )

        import asyncio
        asyncio.create_task(self._force_disconnect(delay=4.0))

        return {
            "status": "ending",
            "message": f"Call disconnecting: {reason}",
        }

    @function_tool
    async def save_conversation_summary(
        self,
        context: RunContext,
        summary: str,
        outcome: str,
        budget: str = "",
        preferred_location: str = "",
        property_type: str = "",
        timeline: str = "",
        notes: str = "",
    ) -> dict:
        """
        Save a summary of this conversation for future reference.
        Call this BEFORE log_call_outcome to capture key details about the customer.

        This helps personalize future calls by remembering what was discussed.

        Args:
            summary: Brief 1-2 sentence summary of what was discussed
            outcome: Call outcome (appointment_booked, callback_requested, not_interested_now, etc.)
            budget: Customer's stated budget range (e.g., "50-70 lakhs", "1 crore")
            preferred_location: Areas/locations customer is interested in
            property_type: Type of property (e.g., "2BHK flat", "3BHK", "villa", "plot")
            timeline: When customer plans to buy (e.g., "next 3 months", "within 1 year")
            notes: Any other important details mentioned by the customer
        """
        preferences = {}
        if budget:
            preferences["budget"] = budget
        if preferred_location:
            preferences["preferred_location"] = preferred_location
        if property_type:
            preferences["property_type"] = property_type
        if timeline:
            preferences["timeline"] = timeline
        if notes:
            preferences["notes"] = notes

        save_conversation(
            phone=self.customer_phone,
            summary=summary,
            outcome=outcome,
            preferences=preferences,
        )

        logger.info(
            "Conversation summary saved for %s: %s",
            self.customer_phone,
            summary[:80],
        )

        return {
            "status": "saved",
            "message": "Conversation summary saved for future reference.",
        }
