"""Dashboard route — serves the operator UI."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

UI_FILE = Path(__file__).parent.parent.parent.parent / "static" / "index.html"


@router.get("/", response_class=HTMLResponse)
async def home():
    """Serve the operator dashboard."""
    if not UI_FILE.exists():
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
    return HTMLResponse(UI_FILE.read_text(encoding="utf-8"))
