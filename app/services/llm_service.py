# app/services/llm_service.py
from __future__ import annotations
import os
from typing import List, Dict

from app.config.settings import settings

# SDK v1
try:
    from openai import OpenAI, AzureOpenAI
except Exception as _e:
    OpenAI = None
    AzureOpenAI = None


class LLMService:
    """
    Cliente LLM con:
    - OpenAI por defecto (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE)
    - Azure OpenAI opcional si existen AZURE_* en entorno
    Maneja tanto historial con/ sin 'system' (si no hay, inyecta uno con el topic).
    """

    def __init__(self) -> None:
        self.provider = "azure" if os.getenv("AZURE_OPENAI_API_KEY") else "openai"

        if self.provider == "azure":
            if AzureOpenAI is None:
                raise RuntimeError("Falta el SDK de OpenAI. Instala: pip install openai")
            self.client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            )
            # En Azure, 'model' es el nombre del deployment
            self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        else:
            if OpenAI is None:
                raise RuntimeError("Falta el SDK de OpenAI. Instala: pip install openai")
            # settings ya cargó .env
            api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    def ask(self, prompt: str) -> Dict[str, str]:
        # método legacy, puedes borrarlo si no lo usas
        return {"prompt": prompt, "response": "Respuesta simulada."}

    def _system_for_topic(self, topic: str) -> str:
        return (
            f"Eres un asistente experto, prudente y claro en {topic}. "
            "Responde en español con tono profesional. Incluye referencias de alto nivel "
            "(p. ej., PubMed, guías ESMO/NCCN) cuando proceda. Si no estás seguro, dilo y "
            "explica cómo verificar. No sustituyes consejo médico."
        )

    def chat(self, topic: str, messages: List[Dict[str, str]]) -> str:
        """
        messages: [{'role':'user'|'assistant'|'system', 'content':'...'}, ...]
        Si el historial no trae 'system', lo inyectamos con el topic.
        """
        try:
            has_system = any(m.get("role") == "system" for m in messages)
            final_messages = (
                messages if has_system
                else [{"role": "system", "content": self._system_for_topic(topic)}] + messages
            )

            resp = self.client.chat.completions.create(
                model=self.model,
                messages=final_messages,
                temperature=self.temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            # No ocultes el problema: devuélvelo para verlo en Streamlit
            last = messages[-1]["content"] if messages else ""
            return (
                f"[error LLM] (Tema: {topic}) No se pudo obtener respuesta.\n"
                f"Detalle: {type(e).__name__}: {e}\n"
                f"Último mensaje: «{last}»"
            )
