# app/main.py
from __future__ import annotations 
import sys
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Parche Windows (Lo mantenemos por seguridad)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.api.validation_routes import router as validation_router
from app.api.generation_routes import router as generation_router
from app.routes.chat_routes import router as chat_router
from app.routes.ui_routes import router as ui_router

load_dotenv()

def create_app() -> FastAPI:
    app = FastAPI(title="Inphormed — LLM-first Claims Validator")
    
    # --- ¡HABILITAR CORS! (La puerta abierta para tu nuevo Front) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción se pone el dominio real, para dev "*" es perfecto
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # --------------------------------------------------------------
    
    app.include_router(validation_router)
    app.include_router(generation_router)
    app.include_router(chat_router)
    app.include_router(ui_router)
    
    return app

app = create_app()