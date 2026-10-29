# app/routes/chat_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any
import traceback

# --- ¡CAMBIO! Importamos nuestro servicio ---
from app.services.llm_service import LLMService, LLMServiceError

router = APIRouter(prefix="/api", tags=["chat"])

class Message(BaseModel):
    role: str # Changed from Literal to str to be more permissive
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    topic: Optional[str] = "hidradenitis supurativa"

@router.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    # Usamos model_dump() para compatibilidad con Pydantic v2
    print(f"📥 [CHAT] Recibido request: {req.model_dump()}")
    
    try:
        # Validar que haya mensajes
        if not req.messages:
            return {"reply": "Error: No se recibieron mensajes."}

        print("🤖 [CHAT] Inicializando LLMService...")
        try:
            llm = LLMService(temperature=0.3)
        except Exception as e:
            print(f"❌ [CHAT] Error init LLMService: {e}")
            return {"reply": f"Error de configuración del servidor (LLM): {str(e)}"}

        print(f"💬 [CHAT] Enviando a LLM (Topic: {req.topic})...")
        try:
            # Convert Pydantic models to dicts using model_dump()
            msgs = [m.model_dump() for m in req.messages]
            
            reply = llm.chat(
                topic=req.topic, 
                messages=msgs
            )
            print("✅ [CHAT] Respuesta recibida.")
            return {"reply": reply}
            
        except Exception as e:
            print(f"❌ [CHAT] Error en llm.chat: {e}")
            traceback.print_exc()
            return {"reply": f"Error generando respuesta: {str(e)}"}

    except Exception as e:
        print(f"🔥 [CHAT] CRITICAL ERROR: {e}")
        traceback.print_exc()
        return {"reply": f"Error interno del servidor: {str(e)}"}