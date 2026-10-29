# app/config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

class Settings:
    def __init__(self) -> None:
        # LLM
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Embeddings
        self.EMBEDDING_MODEL = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )

        # Qdrant
        self.QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "inphormed_chunks")
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

        # Auditoría / logs
        self.AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "logs/audit.log")

        # Reglas orquestador
        self.CITATIONS_LIMIT = int(os.getenv("CITATIONS_LIMIT", "3"))
        self.MIN_HITS = int(os.getenv("MIN_HITS", "1"))

settings = Settings()
