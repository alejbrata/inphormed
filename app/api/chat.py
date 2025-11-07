from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.settings import settings

# Cliente OpenAI compatible (SDK nuevo y legacy)
_OPENAI_CLIENT = None
def _get_openai_client(api_key: str):
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT
    try:
        # SDK >= 1.x
        from openai import OpenAI  # type: ignore
        _OPENAI_CLIENT = OpenAI(api_key=api_key)
        return _OPENAI_CLIENT
    except Exception:
        pass
    try:
        # SDK legacy
        import openai  # type: ignore
        openai.api_key = api_key
        _OPENAI_CLIENT = openai
        return _OPENAI_CLIENT
    except Exception:
        return None

router = APIRouter(tags=["chat"])

class Message(BaseModel):
    role: str
    content: str

class ChatPayload(BaseModel):
    messages: List[Message]
    topic: Optional[str] = None

@router.post("/api/chat")
async def chat(payload: ChatPayload) -> Dict[str, Any]:
    """
    Chat simple:
    - Usa OPENAI_MODEL si hay OPENAI_API_KEY.
    - Si no hay API key, responde con un fallback local.
    Devuelve: {"reply": "...", "model": "..."}
    """
    msgs = [{"role": m.role, "content": m.content} for m in payload.messages if (m.content or "").strip()]
    if not msgs:
        raise HTTPException(status_code=400, detail="No hay mensajes válidos.")

    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL

    # Fallback sin LLM
    if not api_key:
        last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
        reply = f"(modo local) Me has dicho: {last_user[:300]}"
        return {"reply": reply, "model": None}

    client = _get_openai_client(api_key)
    if client is None:
        last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
        reply = f"(sin SDK) Me has dicho: {last_user[:300]}"
        return {"reply": reply, "model": None}

    try:
        # SDK nuevo
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            resp = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=0.3,
                max_tokens=600,
            )
            text = (resp.choices[0].message.content or "").strip()
            return {"reply": text or "No obtuve respuesta.", "model": model}

        # SDK legacy
        if hasattr(client, "ChatCompletion"):
            resp = client.ChatCompletion.create(
                model=model,
                messages=msgs,
                temperature=0.3,
                max_tokens=600,
            )
            text = (resp["choices"][0]["message"]["content"] or "").strip()
            return {"reply": text or "No obtuve respuesta.", "model": model}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del modelo: {e}")

    return {"reply": "No se pudo generar respuesta.", "model": None}
