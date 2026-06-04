"""
Appointment Reminder Flow.

Checks upcoming appointments and generates reminder messages for WhatsApp.
Tracks reminder status (sent/pending).
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config.settings import settings
from app.core.data_store import data_store

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# Reminder window: appointments within the next 24 hours
REMINDER_WINDOW_HOURS = 24


class ReminderManager:
    """
    Manages appointment reminders — checks upcoming bookings and
    generates WhatsApp reminder messages.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data_dir = settings.data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def reminders_file(self) -> Path:
        return self._data_dir / "reminders.json"

    def _read_reminders(self) -> list[dict]:
        """Read reminder status from JSON file."""
        with self._lock:
            if self.reminders_file.exists():
                try:
                    return json.loads(self.reminders_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    return []
            return []

    def _write_reminders(self, data: list[dict]) -> None:
        """Atomic write reminders to JSON file."""
        with self._lock:
            tmp = self.reminders_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.reminders_file)

    def get_upcoming_appointments(self) -> list[dict]:
        """
        Get all appointments booked within the next 24 hours.
        Parses the slot_chosen field from bookings.
        """
        bookings = data_store.get_bookings()
        now = datetime.now(IST)
        window_end = now + timedelta(hours=REMINDER_WINDOW_HOURS)

        upcoming = []
        for booking in bookings:
            if booking.get("type") != "appointment_booked":
                continue

            slot = booking.get("slot_chosen", "")
            customer_name = booking.get("customer_name", "Customer")
            customer_phone = booking.get("customer_phone", "")
            booked_at = booking.get("booked_at", "")

            upcoming.append({
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "slot_chosen": slot,
                "booked_at": booked_at,
            })

        return upcoming

    def get_pending_reminders(self) -> list[dict]:
        """
        Get appointments needing reminders (not yet sent).
        Returns list of appointments with reminder status.
        """
        upcoming = self.get_upcoming_appointments()
        sent_reminders = self._read_reminders()
        sent_keys = {
            f"{r['customer_phone']}_{r['slot_chosen']}" for r in sent_reminders
        }

        pending = []
        for appt in upcoming:
            key = f"{appt['customer_phone']}_{appt['slot_chosen']}"
            if key not in sent_keys:
                appt["reminder_status"] = "pending"
                pending.append(appt)

        return pending

    def generate_reminder_message(self, customer_name: str, slot: str) -> str:
        """Generate a WhatsApp reminder message for an appointment."""
        from app.config.constants import BROKER_NAME, AGENCY_NAME, OFFICE_ADDRESS

        message = (
            f"🏠 Appointment Reminder\n\n"
            f"Namaste {customer_name} ji!\n\n"
            f"This is a reminder for your appointment:\n"
            f"📅 {slot}\n"
            f"📍 {OFFICE_ADDRESS}\n\n"
            f"Looking forward to meeting you!\n"
            f"— {BROKER_NAME}, {AGENCY_NAME}\n\n"
            f"If you need to reschedule, please call us back."
        )
        return message

    def mark_reminder_sent(self, customer_phone: str, slot: str) -> None:
        """Mark a reminder as sent."""
        reminders = self._read_reminders()
        reminders.append({
            "customer_phone": customer_phone,
            "slot_chosen": slot,
            "sent_at": datetime.now(IST).isoformat(),
            "status": "sent",
        })
        self._write_reminders(reminders)

    def get_all_reminders(self) -> list[dict]:
        """Get all reminder records (sent and pending)."""
        sent = self._read_reminders()
        pending = self.get_pending_reminders()
        return {
            "sent": sent,
            "pending": pending,
        }


# Module-level singleton
reminder_manager = ReminderManager()
