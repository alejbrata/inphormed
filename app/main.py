# app/main.py
from __future__ import annotations
from dotenv import load_dotenv
from fastapi import FastAPI

# --- ¡CAMBIO CRÍTICO! ---
# 1. Importamos el NUEVO router unificado que creamos
from app.api.validation_routes import router as validation_router

# 2. (Mantenemos los otros routers que SÍ usas y no dan conflicto)
from app.routes.chat_routes import router as chat_router
from app.routes.ui_routes import router as ui_router

# 3. (Las importaciones antiguas que causaban el 404/ImportError se eliminan)
# from app.api.claims import router as claims_router  <-- ELIMINADO
# from app.api.pptx_claims import router as pptx_claims_router <-- ELIMINADO

load_dotenv()
def create_app() -> FastAPI:
    app = FastAPI(title="Inphormed — LLM-first Claims Validator")
    
    # Endpoints
    # --- ¡CAMBIO CRÍTICO! ---
    # 4. Registramos el router unificado
    app.include_router(validation_router)
    
    # 5. (Registramos los otros)
    app.include_router(chat_router)
    app.include_router(ui_router)
    
    return app

app = create_app()