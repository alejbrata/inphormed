from __future__ import annotations
from dotenv import load_dotenv
from fastapi import FastAPI

# Routers
from app.api.claims import router as claims_router
from app.api.pptx_claims import router as pptx_claims_router
load_dotenv()
def create_app() -> FastAPI:
    app = FastAPI(title="Inphormed — LLM-first Claims Validator")
    # Endpoints
    app.include_router(claims_router)
    app.include_router(pptx_claims_router)  # /api/claims/validate-ppt
    return app

app = create_app()
