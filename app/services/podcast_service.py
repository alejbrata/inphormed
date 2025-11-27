from __future__ import annotations
import io
import json
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from app.services.llm_service import LLMService

class PodcastService:
    def __init__(self):
        self.llm = LLMService(temperature=0.7) # Un poco más creativo para el podcast

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extrae texto de un PDF en memoria."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error leyendo PDF: {e}")

    def generate_script(self, text: str) -> List[Dict[str, str]]:
        """
        Genera un guion de podcast (Host vs Experto) basado en el texto.
        Devuelve una lista de mensajes: [{"speaker": "Host", "text": "..."}, ...]
        """
        system_prompt = """
        Eres un productor de podcasts científicos de clase mundial.
        Tu tarea es convertir un texto técnico (paper/documento) en un guion de podcast atractivo y educativo.
        
        Formato:
        - Dos oradores: "Host" (Curioso, entusiasta, hace las preguntas correctas) y "Experto" (Científico, claro, didáctico).
        - Tono: "Inphormed" (Profesional pero accesible, estilo NPR o TED Radio Hour).
        - Duración: Breve y conciso (aprox 3-5 minutos de lectura).
        - Idioma: Español neutro.

        Output:
        Devuelve SÓLO un objeto JSON con la clave "script", que es una lista de objetos:
        {
          "script": [
            {"speaker": "Host", "text": "Hola a todos, bienvenidos a un nuevo episodio de Inphormed..."},
            {"speaker": "Experto", "text": "Gracias por invitarme. Hoy vamos a hablar de..."},
            ...
          ]
        }
        """

        # Truncamos el texto si es muy largo para no exceder tokens (simple approach)
        max_chars = 15000 
        truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text

        user_prompt = f"Aquí tienes el texto fuente:\n\n---\n{truncated_text}\n---\n\nGenera el guion del podcast."

        data = self.llm.chat_with_json(system_prompt, user_prompt)
        if not data or "script" not in data:
            raise ValueError("El LLM no generó un guion válido.")
        
        return data["script"]

    def generate_summary(self, text: str) -> str:
        """
        Genera un resumen ejecutivo estructurado del texto.
        """
        system_prompt = """
        Eres un analista científico experto.
        Tu tarea es crear un Resumen Ejecutivo estructurado de un paper o documento técnico.
        
        Formato de Salida (Markdown):
        # Título del Documento (detectado o generado)
        
        ## 🎯 Objetivo Principal
        Breve descripción del propósito del estudio.
        
        ## 🔑 Hallazgos Clave
        - Hallazgo 1
        - Hallazgo 2
        - Hallazgo 3
        
        ## 📉 Conclusión
        Resumen final de las implicaciones.
        
        Mantén un tono profesional, objetivo y conciso.
        """
        
        # Truncamos para no exceder contexto
        max_chars = 20000
        truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text
        
        user_prompt = f"Analiza el siguiente texto y genera el resumen:\n\n---\n{truncated_text}\n---"
        
        return self.llm.chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])

    async def generate_audio(self, script: List[Dict[str, str]]) -> bytes:
        """
        Convierte el guion a audio usando OpenAI TTS.
        Concatena los audios de cada intervención.
        """
        if not self.llm.client or self.llm.provider != "openai":
             # Fallback o error si no es OpenAI (Azure/Gemini TTS requieren otra implementación)
             # Por ahora asumimos OpenAI como dice el requerimiento.
             if self.llm.provider != "openai":
                 raise ValueError("La generación de audio requiere OpenAI por ahora.")

        # Voces
        voice_host = "nova"  # Voz femenina enérgica (mejor para Host)
        voice_expert = "echo" # Voz masculina equilibrada (mejor para Experto)

        combined_audio = io.BytesIO()

        for turn in script:
            speaker = turn.get("speaker", "Host")
            text = turn.get("text", "")
            voice = voice_expert if speaker == "Experto" else voice_host

            try:
                response = self.llm.client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                # Escribir los bytes en el buffer
                for chunk in response.iter_bytes():
                    combined_audio.write(chunk)
            except Exception as e:
                print(f"Error generando audio para {speaker}: {e}")
                continue
        
        combined_audio.seek(0)
        return combined_audio.read()
