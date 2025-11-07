from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.claims import router as claims_router
from app.api.chat import router as chat_router  # ← añade el router del chat
from app.api.pptx_claims import router as pptx_claims_router

app = FastAPI(title="Inphormed API", version="0.1.0")

# CORS (ajústalo a tu frontend si lo sirves desde otro host/puerto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(chat_router)    # ← expone /api/chat
app.include_router(claims_router)  # ← expone /api/claims/*
app.include_router(pptx_claims_router)
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
