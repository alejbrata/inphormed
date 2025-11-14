# app/services/llm_service.py
from __future__ import annotations
import os
import json
from typing import List, Dict, Optional, Any, Literal

from app.config.settings import settings

# --- SDKs de proveedores (importaciones opcionales) ---
try:
    from openai import OpenAI, AzureOpenAI
except ImportError:
    OpenAI = None
    AzureOpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Tipo para roles de mensajes
MessageRole = Literal["system", "user", "assistant"]

class LLMServiceError(Exception):
    """Excepción personalizada para errores del servicio LLM."""
    pass

class LLMService:
    """
    Servicio de abstracción de LLM (El "Puerto USB").
    Unifica las llamadas a OpenAI, Azure y Gemini.
    
    Configuración (variables de entorno):
    - LLM_PROVIDER: "openai" (default), "azure", "gemini"
    - OPENAI_API_KEY / AZURE_... / GOOGLE_API_KEY
    - OPENAI_MODEL / AZURE_OPENAI_DEPLOYMENT / GEMINI_MODEL
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.2) -> None:
        # 1. LEER EL PROVEEDOR (del settings)
        self.provider = settings.LLM_PROVIDER
        self.temperature = temperature
        self.client = None
        self.model_name = model # El modelo se puede forzar o se coge del .env

        # --- 2. Inicializar el cliente según el proveedor ---
        try:
            if self.provider == "azure":
                if AzureOpenAI is None:
                    raise ImportError("SDK de Azure no instalado. Ejecuta: pip install openai")
                self.client = AzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                )
                self.model_name = model or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

            elif self.provider == "gemini":
                if genai is None:
                    raise ImportError("SDK de Gemini no instalado. Ejecuta: pip install google-generativeai")
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise LLMServiceError("GOOGLE_API_KEY no configurada.")
                genai.configure(api_key=api_key)
                self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
                self.client = genai.GenerativeModel(self.model_name)

            else: # Default a "openai"
                self.provider = "openai"
                if OpenAI is None:
                    raise ImportError("SDK de OpenAI no instalado. Ejecuta: pip install openai")
                api_key = settings.OPENAI_API_KEY
                if not api_key:
                    raise LLMServiceError("OPENAI_API_KEY no configurada.")
                self.client = OpenAI(api_key=api_key)
                self.model_name = model or settings.OPENAI_MODEL

        except ImportError as e:
            raise LLMServiceError(f"Error de importación para {self.provider}: {e}") from e
        except Exception as e:
            raise LLMServiceError(f"Error configurando cliente {self.provider}: {e}") from e

    # --- 3. MÉTODOS PÚBLICOS (El "API" de nuestro USB) ---

    def chat(self, messages: List[Dict[str, str]], topic: Optional[str] = None) -> str:
        """
        Devuelve una respuesta de texto simple (para el chatbot).
        'topic' se usa para inyectar un system prompt si no existe.
        """
        if not self.client:
            raise LLMServiceError("Cliente no inicializado.")

        final_messages = self._prepare_chat_messages(messages, topic)

        try:
            if self.provider in ("openai", "azure"):
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=final_messages,
                    temperature=self.temperature,
                )
                return resp.choices[0].message.content or ""

            elif self.provider == "gemini":
                gemini_messages = self._convert_messages_to_gemini(final_messages)
                response = self.client.generate_content(gemini_messages)
                return response.text

        except Exception as e:
            raise LLMServiceError(f"Error en API ({self.provider}) chat: {e}") from e
        
        return f"Error: Proveedor {self.provider} no implementado en chat()"

    def chat_with_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve un objeto JSON (parseado) o None si falla.
        Usado por el Juez y el Extractor.
        """
        if not self.client:
            raise LLMServiceError("Cliente no inicializado.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            if self.provider in ("openai", "azure"):
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.0, # Crítico para JSON
                    response_format={"type": "json_object"},
                )
                txt = resp.choices[0].message.content or ""
            
            elif self.provider == "gemini":
                # Gemini no tiene 'response_format', lo pedimos en el prompt
                messages[1]["content"] = f"{user_prompt}\n\nResponde SÓLO con un objeto JSON válido."
                gemini_messages = self._convert_messages_to_gemini(messages)

                response = self.client.generate_content(gemini_messages)
                # Limpiar markdown
                txt = response.text.strip().lstrip("```json").rstrip("```") 

            # Parseo
            return json.loads(txt)

        except json.JSONDecodeError as e:
            raise LLMServiceError(f"Error parseando JSON de {self.provider}: {e}\nTexto recibido: {txt[:200]}...") from e
        except Exception as e:
            raise LLMServiceError(f"Error en API JSON ({self.provider}): {e}") from e

    # --- 4. Métodos privados de adaptación ---

    def _prepare_chat_messages(self, messages: List[Dict[str, str]], topic: Optional[str] = None) -> List[Dict[str, str]]:
        """Asegura que hay un system prompt si se provee un 'topic'."""
        has_system = any(m.get("role") == "system" for m in messages)
        if topic and not has_system:
            system_prompt = (
                f"Eres un asistente experto, prudente y claro en {topic}. "
                "Responde en español con tono profesional."
            )
            return [{"role": "system", "content": system_prompt}] + messages
        return messages

    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Adapta el historial de OpenAI al de Gemini."""
        gemini_messages = []
        system_prompt = ""
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_prompt = content
                continue
            
            if system_prompt and role == "user":
                content = f"{system_prompt}\n\n---\n\n{content}"
                system_prompt = "" 
            
            gemini_messages.append({
                "role": "model" if role == "assistant" else "user",
                "parts": [content]
            })
        return gemini_messages