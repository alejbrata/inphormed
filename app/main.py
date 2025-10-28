import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.agents.ingestion_agent import IngestionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.generation_agent import GenerationAgent
from app.routes.ui_routes import router as ui_router
# NUEVO: importa routers
from app.routes.upload_routes import router as upload_router
from app.routes.chat_routes import router as chat_router

app = FastAPI(title="Inphormed API", version="0.1")

# Asegura carpetas
for folder in ["uploads", "outputs"]:
    os.makedirs(folder, exist_ok=True)

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(ui_router)

# UI
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Health
@app.get("/health")
def health_check():
    return {"status": "ok"}
