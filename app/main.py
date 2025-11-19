# app/main.py
from __future__ import annotations # <--- Esta línea SIEMPRE debe ir la primera
import sys
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI

# --- ¡PARCHE CRÍTICO PARA WINDOWS! ---
# Forzar Proactor para que Playwright funcione con uvicorn reload
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -------------------------------------

# 1. Importamos el NUEVO router unificado
from app.api.validation_routes import router as validation_router

# 2. (Mantenemos los otros routers)
from app.routes.chat_routes import router as chat_router
from app.routes.ui_routes import router as ui_router

load_dotenv()

def create_app() -> FastAPI:
    app = FastAPI(title="Inphormed — LLM-first Claims Validator")
    
    # Endpoints
    app.include_router(validation_router)
    app.include_router(chat_router)
    app.include_router(ui_router)
    
    return app

app = create_app()