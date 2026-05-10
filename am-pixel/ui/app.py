"""
AM Pixel Web UI — FastAPI entrypoint.
Serves both the inference API and the local web interface.
See SPEC.md §13 for full requirements. Localhost only (127.0.0.1).

Phase 0: Working skeleton — chat panel, 1x/4x sprite preview, approve/reject/adjust controls,
         project tabs, freeform tab. Functional before Practice Gauntlet (Phase 5).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AM Pixel",
    description="AI Sprite Generator — Absentmind Studio",
    version="0.1.0",
)

_BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")


def _read_template(name: str) -> str:
    """Read an HTML template file and return its contents."""
    return (_BASE / "templates" / name).read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    message: str
    mode: Optional[str] = "auto"       # auto, character, tileset, ui, freeform, …
    session_id: Optional[str] = None


class ApprovalAction(BaseModel):
    action: str                         # "approve" | "reject" | "adjust"
    candidate_id: str
    adjustment_note: Optional[str] = None


class FreeformRequest(BaseModel):
    description: str
    width: int = 64
    height: int = 64


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Main application shell."""
    return HTMLResponse(_read_template("index.html"))


@app.get("/freeform", response_class=HTMLResponse)
async def freeform_page():
    """Dedicated freeform (Mode 7) tab."""
    return HTMLResponse(_read_template("freeform.html"))


# ---------------------------------------------------------------------------
# Chat / generation API
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat(msg: ChatMessage):
    """
    Receive a natural language generation request.
    Phase 0 skeleton: echoes back a stub response.
    Full implementation: routes to pipeline/modes/* based on detected mode.
    """
    # TODO: wire to pipeline/approval/conversation.py in Phase 7
    return JSONResponse({
        "status": "ok",
        "mode": msg.mode,
        "reply": (
            f"[Stub] Received: '{msg.message}'. "
            "Generation engine not yet connected — Phase 0 skeleton."
        ),
        "candidate_id": None,
        "preview_1x": None,
        "preview_4x": None,
    })


@app.post("/api/freeform")
async def freeform_generate(req: FreeformRequest):
    """
    Mode 7 freeform generation endpoint.
    Phase 0 skeleton: returns stub.
    Full implementation: routes to pipeline/modes/mode7_freeform.py.
    """
    # TODO: wire to pipeline/modes/mode7_freeform.py in Phase 7
    return JSONResponse({
        "status": "ok",
        "description": req.description,
        "dimensions": f"{req.width}x{req.height}",
        "reply": "[Stub] Freeform generation not yet connected — Phase 0 skeleton.",
        "candidate_id": None,
        "preview_url": None,
    })


# ---------------------------------------------------------------------------
# Approval API
# ---------------------------------------------------------------------------

@app.post("/api/approve")
async def approve(action: ApprovalAction):
    """
    Handle approve / reject / adjust actions from the UI.
    Phase 0 skeleton: acknowledges the action.
    Full implementation: routes to pipeline/approval/* in Phase 7.
    """
    if action.action not in ("approve", "reject", "adjust"):
        raise HTTPException(status_code=400, detail="action must be approve, reject, or adjust")

    # TODO: wire to pipeline/approval/conversation.py in Phase 7
    return JSONResponse({
        "status": "ok",
        "action": action.action,
        "candidate_id": action.candidate_id,
        "note": action.adjustment_note,
        "reply": f"[Stub] Action '{action.action}' received for candidate {action.candidate_id}.",
    })


# ---------------------------------------------------------------------------
# Project / manifest API
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def status():
    """Hardware and pipeline status for the status bar."""
    try:
        from model.hardware.detector import get_device_info
        hw = get_device_info()
    except Exception:
        hw = {"backend": "unknown", "gpu_model": "unknown", "vram_gb": "unknown"}

    return JSONResponse({
        "hardware": hw,
        "phase": "Phase 0 — System Initialization",
        "training_status": "Not started",
    })


@app.get("/api/manifest")
async def continuity_manifest():
    """Return the continuity manifest as JSON for the viewer tab."""
    manifest_path = _BASE.parent / "dna" / "CONTINUITY_MANIFEST.md"
    if not manifest_path.exists():
        return JSONResponse({"content": "", "characters": []})
    content = manifest_path.read_text(encoding="utf-8")
    return JSONResponse({"content": content, "characters": []})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import uvicorn
    uvicorn.run(
        "ui.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
