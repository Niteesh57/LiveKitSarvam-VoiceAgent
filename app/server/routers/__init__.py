"""API routers — modular endpoint definitions."""

from .leads import router as leads_router
from .calls import router as calls_router
from .bookings import router as bookings_router
from .context import router as context_router
from .dashboard import router as dashboard_router
from .webrtc import router as webrtc_router

__all__ = [
    "leads_router",
    "calls_router",
    "bookings_router",
    "context_router",
    "dashboard_router",
    "webrtc_router",
]
