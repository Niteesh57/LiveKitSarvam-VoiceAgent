"""
WhatsApp Follow-up Integration (stub with Twilio/Plivo).

Provides functions for sending WhatsApp messages — currently logs messages
as stubs. Actual integration with Twilio or Plivo can be added later
by implementing the HTTP calls in send_whatsapp_message().

Also provides message queuing (stored in data/whatsapp_queue.json)
for async/batch processing.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config.settings import settings
from app.config.constants import BROKER_NAME, AGENCY_NAME, OFFICE_ADDRESS

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def send_whatsapp_message(phone: str, message: str) -> dict:
    """
    Send a WhatsApp message to a phone number.

    Currently a stub that logs the message. Replace with actual
    Twilio/Plivo API call when ready.

    Args:
        phone: Phone number with country code (e.g., +919876543210)
        message: Message text to send

    Returns:
        dict with status and details
    """
    api_key = settings.whatsapp_api_key
    from_number = settings.whatsapp_phone_number

    if not api_key:
        logger.warning(
            "[WhatsApp STUB] No API key configured. Message NOT sent to %s: %s",
            phone,
            message[:100],
        )
        return {
            "status": "stub",
            "message": "WhatsApp API key not configured. Message logged only.",
            "phone": phone,
            "content": message,
            "timestamp": datetime.now(IST).isoformat(),
        }

    # TODO: Replace with actual Twilio/Plivo API call
    # Example Twilio implementation:
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # message = client.messages.create(
    #     body=message,
    #     from_=f"whatsapp:{from_number}",
    #     to=f"whatsapp:{phone}"
    # )

    logger.info(
        "[WhatsApp] Sending message to %s from %s: %s",
        phone,
        from_number,
        message[:100],
    )

    return {
        "status": "sent",
        "phone": phone,
        "from": from_number,
        "content": message,
        "timestamp": datetime.now(IST).isoformat(),
    }


def queue_whatsapp_message(phone: str, message: str, message_type: str = "general") -> dict:
    """
    Queue a WhatsApp message for later sending. Stored in data/whatsapp_queue.json.

    This enables batch processing and retry logic without blocking the call flow.

    Args:
        phone: Customer phone number with country code
        message: Message text content
        message_type: Type of message (post_call_thanks, appointment_confirmation,
                      appointment_reminder, follow_up)

    Returns:
        dict with queue status
    """
    from app.core.data_store import data_store

    entry = {
        "phone": phone,
        "message": message,
        "message_type": message_type,
        "queued_at": datetime.now(IST).isoformat(),
        "status": "pending",
    }

    data_store.queue_whatsapp_message(entry)

    logger.info(
        "[WhatsApp Queue] Queued %s message for %s",
        message_type,
        phone,
    )

    return {
        "status": "queued",
        "phone": phone,
        "message_type": message_type,
        "queued_at": entry["queued_at"],
    }


def queue_post_call_thankyou(phone: str, customer_name: str) -> dict:
    """
    Queue a post-call thank you message after a conversation.

    Args:
        phone: Customer phone number
        customer_name: Customer's name
    """
    message = (
        f"Namaste {customer_name} ji! 🙏\n\n"
        f"Thank you for your time on the call today.\n\n"
        f"If you have any questions about properties, feel free to reach out anytime.\n\n"
        f"— {BROKER_NAME}, {AGENCY_NAME}\n"
        f"📞 {BROKER_NAME}"
    )
    return queue_whatsapp_message(phone, message, "post_call_thanks")


def queue_appointment_confirmation(phone: str, customer_name: str, slot: str) -> dict:
    """
    Queue appointment confirmation with office address after booking.

    Args:
        phone: Customer phone number
        customer_name: Customer's name
        slot: Confirmed appointment slot
    """
    message = (
        f"🏠 Appointment Confirmed!\n\n"
        f"Namaste {customer_name} ji!\n\n"
        f"Your appointment has been booked:\n"
        f"📅 {slot}\n\n"
        f"📍 Office Address:\n{OFFICE_ADDRESS}\n\n"
        f"🗺️ Google Maps: https://maps.google.com/?q=Pearl+Plaza+Andheri+West+Mumbai\n\n"
        f"Please carry a valid ID proof.\n"
        f"Looking forward to meeting you!\n\n"
        f"— {BROKER_NAME}, {AGENCY_NAME}"
    )
    return queue_whatsapp_message(phone, message, "appointment_confirmation")


def queue_appointment_reminder(phone: str, customer_name: str, slot: str) -> dict:
    """
    Queue an appointment reminder message.

    Args:
        phone: Customer phone number
        customer_name: Customer's name
        slot: Appointment slot
    """
    message = (
        f"⏰ Appointment Reminder\n\n"
        f"Namaste {customer_name} ji!\n\n"
        f"Just a friendly reminder about your appointment tomorrow:\n\n"
        f"📅 {slot}\n"
        f"📍 {OFFICE_ADDRESS}\n\n"
        f"We're looking forward to meeting you!\n\n"
        f"If you need to reschedule, just reply to this message or call us.\n\n"
        f"— {BROKER_NAME}, {AGENCY_NAME}"
    )
    return queue_whatsapp_message(phone, message, "appointment_reminder")


def get_pending_queue() -> list[dict]:
    """Get all pending (unsent) messages from the queue."""
    from app.core.data_store import data_store
    queue = data_store.get_whatsapp_queue()
    return [msg for msg in queue if msg.get("status") == "pending"]


def send_office_address(phone: str, customer_name: str) -> dict:
    """
    Send office address via WhatsApp after booking confirmation.

    Args:
        phone: Customer phone number
        customer_name: Customer's name for personalization
    """
    message = (
        f"🏠 Sunrise Properties - Office Visit Confirmed!\n\n"
        f"Namaste {customer_name} ji!\n\n"
        f"Your appointment has been confirmed. Here are the details:\n\n"
        f"📍 Office Address:\n{OFFICE_ADDRESS}\n\n"
        f"🗺️ Google Maps: https://maps.google.com/?q=Pearl+Plaza+Andheri+West+Mumbai\n\n"
        f"Please carry a valid ID proof.\n"
        f"For any queries, contact: {BROKER_NAME}\n\n"
        f"See you soon!\n"
        f"— {AGENCY_NAME}"
    )

    return send_whatsapp_message(phone, message)


def send_appointment_reminder(phone: str, customer_name: str, slot: str) -> dict:
    """
    Send appointment reminder via WhatsApp.

    Args:
        phone: Customer phone number
        customer_name: Customer's name
        slot: Appointment slot (e.g., "Saturday June 7 at 11 AM")
    """
    message = (
        f"⏰ Appointment Reminder\n\n"
        f"Namaste {customer_name} ji!\n\n"
        f"Just a friendly reminder about your upcoming appointment:\n\n"
        f"📅 {slot}\n"
        f"📍 {OFFICE_ADDRESS}\n\n"
        f"We're looking forward to meeting you!\n\n"
        f"If you need to reschedule, just reply to this message or call us.\n\n"
        f"— {BROKER_NAME}, {AGENCY_NAME}"
    )

    return send_whatsapp_message(phone, message)


def send_follow_up_message(phone: str, customer_name: str, context: str = "") -> dict:
    """
    Send a follow-up WhatsApp message after a call.

    Args:
        phone: Customer phone number
        customer_name: Customer's name
        context: Brief context about the call outcome
    """
    message = (
        f"Namaste {customer_name} ji! 🙏\n\n"
        f"Thank you for your time on the call today.\n\n"
        f"{context}\n\n"
        f"Feel free to reach out whenever you're ready to discuss further.\n\n"
        f"— {BROKER_NAME}, {AGENCY_NAME}\n"
        f"📞 Contact: {BROKER_NAME}"
    )

    return send_whatsapp_message(phone, message)
