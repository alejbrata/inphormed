import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.agents.ingestion_agent import IngestionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.generation_agent import GenerationAgent
from app.routes.upload_routes import router as upload_router


app = FastAPI(title="Inphormed API", version="0.1")
for folder in ["uploads", "outputs"]:
    os.makedirs(folder, exist_ok=True)

app.include_router(upload_router)
# --- Static & Templates ---
app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

templates = Jinja2Templates(directory="templates")


# --- Páginas (UI) ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- API mínima ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/validate")
async def api_validate(payload: dict):
    claim = (payload or {}).get("claim", "").strip()
    result = ValidationAgent().validate_claim(claim)
    return result

@app.post("/api/ingest")
async def api_ingest(payload: dict):
    path = (payload or {}).get("path", "").strip()
    result = IngestionAgent().ingest_document(path)
    return result
