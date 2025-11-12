# app/main.py
from __future__ import annotations
from dotenv import load_dotenv
from fastapi import FastAPI

# Routers
# --- ¡CAMBIO REALIZADO AQUÍ! ---
# Importamos el NUEVO router unificado
from app.api.validation_routes import router as validation_router

# (Mantenemos los otros routers que sí usas)
from app.routes.chat_routes import router as chat_router
from app.routes.ui_routes import router as ui_router

load_dotenv()
def create_app() -> FastAPI:
    app = FastAPI(title="Inphormed — LLM-first Claims Validator")
    
    # Endpoints
    # --- ¡CAMBIO REALIZADO AQUÍ! ---
    # Registramos el router unificado
    app.include_router(validation_router)
    
    # (Registramos los otros)
    app.include_router(chat_router)
    app.include_router(ui_router)
    
    # ESTAS LÍNEAS CONFLICTIVAS SE HAN ELIMINADO
    # app.include_router(claims_router)
    # app.include_router(pptx_claims_router)
    
    return app

app = create_app()