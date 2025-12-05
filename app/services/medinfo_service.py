from app.services.llm_service import LLMService
from app.schemas import MedInfoResponse
import json

class MedInfoService:
    def __init__(self):
        # Usamos gpt-4o para asegurar tono científico y precisión
        self.llm = LLMService(model="gpt-4o", temperature=0.0)

    def generate_response_letter(self, paper_text: str) -> MedInfoResponse:
        system_prompt = """Eres un Técnico de Información Médica (MedInfo) en una farmacéutica.
Tu tarea es redactar una Carta de Respuesta Estándar (Standard Response Document) para contestar a una consulta médica no solicitada.

Basándote EXCLUSIVAMENTE en el paper proporcionado:
1. Resumen objetivo del estudio.
2. Datos de eficacia y seguridad relevantes.
3. Limitaciones del estudio.

TONO: Estrictamente científico, neutro, sin adjetivos promocionales. Cumple con la regulación de Farmaindustria.
NO inventes datos. Si no está en el texto, no lo incluyas.

Debes responder EXCLUSIVAMENTE con un objeto JSON válido que cumpla con este esquema:
{
  "subject": "Asunto formal de la carta (ej: Respuesta a consulta sobre...)",
  "summary": "Resumen ejecutivo neutro del estudio (max 300 palabras)",
  "efficacy_data": ["punto clave 1", "punto clave 2", ...],
  "safety_data": ["punto clave 1", "punto clave 2", ...],
  "limitations": ["limitación 1", "limitación 2", ...],
  "references": ["Cita bibliográfica completa en formato Vancouver"]
}
"""

        # Truncar texto si es excesivo
        max_chars = 100000
        truncated_text = paper_text[:max_chars] + "..." if len(paper_text) > max_chars else paper_text

        user_prompt = f"Genera la carta de respuesta basada en este paper:\n\n{truncated_text}"

        data = self.llm.chat_with_json(system_prompt, user_prompt)
        
        if not data:
            raise ValueError("El LLM no generó una respuesta válida.")

        return MedInfoResponse(**data)
