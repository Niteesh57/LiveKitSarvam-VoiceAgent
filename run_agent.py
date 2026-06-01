"""
LiveKit Agent Worker — Entry Point
====================================
Starts the LiveKit agent worker that handles voice conversations.

Usage:
    python run_agent.py dev        # Development mode (auto-reload)
    python run_agent.py start      # Production mode

The agent automatically joins LiveKit rooms created by the server
and handles the full STT → LLM → TTS voice pipeline.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import AgentServer, JobContext, cli

from app.agent.entrypoint import entrypoint

server = AgentServer()


@server.rtc_session
async def session_entrypoint(ctx: JobContext):
    await entrypoint(ctx)


if __name__ == "__main__":
    cli.run_app(server)
