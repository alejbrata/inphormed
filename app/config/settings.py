# app/config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

# Base dir del repo: .../inphormed
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

class Settings:
    def __init__(self) -> None:
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
