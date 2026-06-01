"""
FastAPI application factory.
Creates the app with all routers mounted.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .routers import leads_router, calls_router, bookings_router, context_router, dashboard_router, webrtc_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sunrise Properties Voice Agent",
        description="LiveKit + Sarvam AI powered warm follow-up voice agent",
        version="1.0.0",
    )

    # CORS middleware for dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(dashboard_router, tags=["Dashboard"])
    app.include_router(context_router, prefix="/api", tags=["Context"])
    app.include_router(leads_router, prefix="/api/leads", tags=["Leads"])
    app.include_router(calls_router, prefix="/api/call", tags=["Calls"])
    app.include_router(bookings_router, prefix="/api/bookings", tags=["Bookings"])
    app.include_router(webrtc_router, prefix="/api/webrtc", tags=["WebRTC"])

    return app
