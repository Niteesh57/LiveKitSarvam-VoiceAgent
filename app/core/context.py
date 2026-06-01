"""
Runtime context computation — dynamic IST dates, broker info, available slots.
"""

from datetime import datetime, timedelta, timezone

from app.config.constants import (
    BROKER_NAME,
    AGENCY_NAME,
    OFFICE_ADDRESS,
    BROKER_PHONE,
)

IST = timezone(timedelta(hours=5, minutes=30))


def get_runtime_context() -> dict:
    """
    Compute fresh runtime context for every call.
    Returns broker info + next 2 upcoming weekend slots at 11 AM IST.
    """
    now = datetime.now(IST)
    today = now.date()
    weekday = today.weekday()  # Mon=0 .. Sun=6

    # Calculate next Saturday
    days_to_sat = (5 - weekday) % 7
    if days_to_sat == 0 and now.hour >= 11:
        days_to_sat = 7

    # Calculate next Sunday
    days_to_sun = (6 - weekday) % 7
    if days_to_sun == 0 and now.hour >= 11:
        days_to_sun = 7

    slots = sorted([
        today + timedelta(days=days_to_sat),
        today + timedelta(days=days_to_sun),
    ])

    return {
        "today_human": now.strftime("%A, %B %d, %Y at %I:%M %p IST"),
        "slot_1": f"{slots[0].strftime('%A %B %d')} at 11 AM",
        "slot_2": f"{slots[1].strftime('%A %B %d')} at 11 AM",
        "broker_name": BROKER_NAME,
        "agency_name": AGENCY_NAME,
        "office_address": OFFICE_ADDRESS,
        "broker_phone": BROKER_PHONE,
    }
