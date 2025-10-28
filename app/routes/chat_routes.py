from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api", tags=["chat"])

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    topic: Optional[str] = "hidradenitis supurativa"

@router.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    llm = LLMService()
    # Intenta responder con LLM si hay API key. Si falla, usa fallback.
    reply = llm.chat(topic=req.topic, messages=[m.model_dump() for m in req.messages])
    return {"reply": reply}
