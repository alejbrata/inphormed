import os
from app.config.settings import settings

try:
    import openai
except Exception:
    openai = None

class LLMService:
    def __init__(self):
        self.key = settings.OPENAI_API_KEY
        if self.key and openai:
            openai.api_key = self.key

    def ask(self, prompt: str):
        # Stub anterior (lo puedes mantener o eliminar)
        return {"prompt": prompt, "response": "Respuesta simulada."}

    def chat(self, topic: str, messages: list[dict]) -> str:
        system = (
            f"Eres un asistente experto, prudente y claro en {topic}. "
            "Responde en español, con tono profesional, y sugiere fuentes clínicas de alto nivel "
            "(p.ej., PubMed, guías ESMO/NCCN) cuando corresponda. "
            "Si no estás seguro, dilo y explica cómo verificar."
        )
        # Si hay API y clave, intenta llamada real (MVP robusto)
        if self.key and openai:
            try:
                resp = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": system}] + messages,
                    temperature=0.2,
                )
                return resp.choices[0].message.content
            except Exception:
                pass
        # Fallback (sin API key o error)
        last = messages[-1]["content"] if messages else ""
        return (
            f"[MVP sin modelo] (Tema: {topic}) He recibido: «{last}». "
            "Cuando configures OPENAI_API_KEY, responderé con una salida clínica real con referencias."
        )
