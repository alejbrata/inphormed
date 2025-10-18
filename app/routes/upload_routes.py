from fastapi import APIRouter, UploadFile, File, HTTPException
from app.agents.validation_agent import ValidationAgent
import os, uuid

router = APIRouter(prefix="/api", tags=["upload"])

@router.post("/verify-ppt")
async def verify_ppt(file: UploadFile = File(...)):
    if not (file.filename.lower().endswith(".pptx") or file.filename.lower().endswith(".docx")):
        raise HTTPException(status_code=400, detail="Sube un .pptx o .docx")

    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    uid = uuid.uuid4().hex
    ppt_path = os.path.join("uploads", f"{uid}.pptx")
    out_pdf = os.path.join("outputs", f"reporte_{uid}.pdf")

    with open(ppt_path, "wb") as f:
        f.write(await file.read())

    # pipeline principal
    agent = ValidationAgent()
    summary = agent.validate_file(ppt_path, out_pdf=out_pdf)

    # devolvemos ruta (en MVP lo sirves estático si quieres)
    return {"report_path": out_pdf, "summary": summary}
