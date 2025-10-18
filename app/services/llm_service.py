import openai
from app.config.settings import settings

class LLMService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def ask(self, prompt: str):
        print("🧩 Enviando prompt al modelo...")
        # TODO: implementar llamada real a OpenAI o Azure OpenAI
        return {"prompt": prompt, "response": "Respuesta simulada."}
