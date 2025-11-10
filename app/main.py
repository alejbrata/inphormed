# app/main.py
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.claims import router as claims_router              # ✅ /api/claims/validate-text (web-first + LLM)
from app.api.pptx_claims import router as pptx_claims_router   # ✅ /api/claims/validate-ppt (LLM-first extractor)
# from app.api.claims_validate_text import router as claims_text_router  # ❌ NO duplicar

app = FastAPI(title="Inphormed API", version="0.1.0")

# CORS — en dev: o bien "*" sin credenciales, o bien orígenes concretos con credenciales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:8501", "http://127.0.0.1:8501", "*"],
    allow_credentials=False,   # ← si quieres True, quita "*" y deja solo orígenes concretos
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers (orden claro, sin duplicados)
app.include_router(chat_router)          # /api/chat
app.include_router(claims_router)        # /api/claims/validate-text
app.include_router(pptx_claims_router)   # /api/claims/validate-ppt

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
