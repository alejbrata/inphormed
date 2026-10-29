# app/routes/ui_routes.py
from __future__ import annotations
import os, json
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.ui_agent import UIAgent

router = APIRouter(prefix="/api", tags=["ui"])
LAYOUT_PATH = "outputs/ui_layout.json"

DEFAULT_LAYOUT = {
    "version": 1,
    "widgets": [
        {"id": "chat",     "order": 0, "span": 2, "visible": True},
        {"id": "validate", "order": 1, "span": 2, "visible": True},
        {"id": "create",   "order": 2, "span": 2, "visible": True},
    ]
}

def _read_layout() -> Dict[str, Any]:
    if os.path.exists(LAYOUT_PATH):
        try:
            with open(LAYOUT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_LAYOUT

def _write_layout(layout: Dict[str, Any]) -> None:
    os.makedirs("outputs", exist_ok=True)
    with open(LAYOUT_PATH, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)

@router.get("/ui-layout")
def get_layout():
    return _read_layout()

class SaveReq(BaseModel):
    layout: Dict[str, Any]

@router.post("/ui-layout")
def save_layout(req: SaveReq):
    _write_layout(req.layout)
    return {"ok": True}

class AgentReq(BaseModel):
    command: str
    layout: Dict[str, Any] | None = None

@router.post("/ui-agent/command")
def ui_command(req: AgentReq):
    layout = req.layout or _read_layout()
    agent = UIAgent()
    new_layout, notes = agent.apply_command(layout, req.command)
    _write_layout(new_layout)
    # El front actual no muestra 'notes', pero lo devolvemos por si quieres loguearlo
    return {"layout": new_layout, "notes": notes}
