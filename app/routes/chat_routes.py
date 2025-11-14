# app/routes/chat_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any

# --- ¡CAMBIO! Importamos nuestro servicio ---
from app.services.llm_service import LLMService, LLMServiceError

router = APIRouter(prefix="/api", tags=["chat"])

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    topic: Optional[str] = "hidradenitis supurativa"

@router.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    
    # --- ¡CAMBIO! ---
    # Toda la lógica de 'openai' desaparece
    try:
        llm = LLMService(temperature=0.3) # Temperatura específica para chat
        
        reply = llm.chat(
            topic=req.topic, 
            messages=[m.model_dump() for m in req.messages]
        )
        
        return {"reply": reply}

    except (LLMServiceError, Exception) as e:
        # Devolvemos el error al frontend para que el usuario sepa qué pasa
        return {"reply": f"Error en el servicio LLM: {e}"}
    # --- FIN DEL CAMBIO ---