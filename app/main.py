# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat_routes import router as chat_router
# importa upload_routes solo si lo usas
try:
    from app.routes.upload_routes import router as upload_router
except Exception:
    upload_router = None
from app.routes.claims_routes import router as claims_router



app = FastAPI(title="Inphormed API")
app.include_router(claims_router, prefix="/api/claims", tags=["claims"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ciérralo en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="")
if upload_router:
    app.include_router(upload_router, prefix="")

@app.get("/health")
def health():
    return {"status": "ok"}
@app.get("/")
def root():
    return {"message": "Inphormed API está en marcha."}