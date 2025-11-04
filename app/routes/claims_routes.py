from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
import os

from app.services.claim_extractor import extract_claims_from_pptx
from app.vector.qdrant_store import QdrantStore
from app.vector.embedder import EmbedderMiniLM
from app.repository.evidence_repo import EvidenceRepository
from app.services.claim_validator import ClaimValidatorService
# --- NUEVO: validar un claim de texto libre ---
from hashlib import sha256 as _sha

router = APIRouter()

# --------- Config vía ENV (fallbacks sensatos) ----------
_QDRANT_URL  = os.getenv("QDRANT_URL", "")
_QDRANT_KEY  = os.getenv("QDRANT_API_KEY", None)
_EVID_COLL   = os.getenv("QDRANT_EVIDENCE_COLLECTION", "biomed_evidence_v1")
_EMBED_DIM   = int(os.getenv("EMBED_DIM", "384"))
_RAG_TOPK    = int(os.getenv("RAG_TOPK", "5"))
_THR_GREEN   = float(os.getenv("RAG_THR_GREEN", "0.82"))
_THR_YELLOW  = float(os.getenv("RAG_THR_YELLOW", "0.70"))

# --------- Modelos de request/response ----------
class ValidateParams(BaseModel):
    topk: int = Field(default=_RAG_TOPK, ge=1, le=20)
    thr_green: float = Field(default=_THR_GREEN, ge=0, le=1)
    thr_yellow: float = Field(default=_THR_YELLOW, ge=0, le=1)

class ClaimHit(BaseModel):
    score: float
    text: Optional[str] = None
    title: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    year: Optional[int] = None
    section: Optional[str] = None

class ClaimResult(BaseModel):
    where: str
    text: str
    claim_id: str
    status: str
    best_score: float
    hits: List[ClaimHit]

class ValidatePptResponse(BaseModel):
    file_name: str
    doc_id: str
    total_claims: int
    results: List[ClaimResult]

# --------- Dependencias para inyectar servicios ----------
def get_validator() -> ClaimValidatorService:
    if not _QDRANT_URL:
        raise RuntimeError("QDRANT_URL no configurado")
    store = QdrantStore(url=_QDRANT_URL, api_key=_QDRANT_KEY, collection=_EVID_COLL, dim=_EMBED_DIM)
    repo  = EvidenceRepository(store=store, embedder=EmbedderMiniLM())
    repo.ensure_ready()
    return ClaimValidatorService(evidence=repo, topk=_RAG_TOPK, thr_green=_THR_GREEN, thr_yellow=_THR_YELLOW)

# --------- Endpoint: subir PPT y validar claims ----------
@router.post("/validate-ppt", response_model=ValidatePptResponse, tags=["claims"])
async def validate_ppt(
    file: UploadFile = File(..., description="PPTX con claims a validar"),
    params: ValidateParams = Depends(),
    validator: ClaimValidatorService = Depends(get_validator),
):
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .pptx")

    data = await file.read()
    try:
        parsed = extract_claims_from_pptx(data, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extrayendo claims del PPTX: {e}")

    claims = parsed["claims"]
    results: List[Dict[str, Any]] = []

    # Ajustamos los umbrales/TopK a demanda de la petición
    validator.topk = params.topk
    validator.thr_green = params.thr_green
    validator.thr_yellow = params.thr_yellow

    for c in claims:
        res = validator.validate(c["text"])
        results.append({
            "where": c["where"],
            "text": c["text"],
            "claim_id": c["claim_id"],
            "status": res["status"],
            "best_score": res["best_score"],
            "hits": res["hits"],
        })

    return {
        "file_name": parsed["file_name"],
        "doc_id": parsed["doc_id"],
        "total_claims": len(claims),
        "results": results,
    }



class ValidateTextRequest(BaseModel):
    text: str = Field(..., min_length=5)
    topk: int = Field(default=_RAG_TOPK, ge=1, le=20)
    thr_green: float = Field(default=_THR_GREEN, ge=0, le=1)
    thr_yellow: float = Field(default=_THR_YELLOW, ge=0, le=1)

class ValidateTextResponse(BaseModel):
    where: str
    text: str
    claim_id: str
    status: str
    best_score: float
    hits: list[ClaimHit]

def _sha16(s: str) -> str:
    return _sha(s.encode("utf-8")).hexdigest()[:16]

@router.post("/validate-text", response_model=ValidateTextResponse, tags=["claims"])
def validate_text(req: ValidateTextRequest, validator: ClaimValidatorService = Depends(get_validator)):
    validator.topk = req.topk
    validator.thr_green = req.thr_green
    validator.thr_yellow = req.thr_yellow

    res = validator.validate(req.text)
    return ValidateTextResponse(
        where="text",
        text=req.text,
        claim_id=_sha16(req.text),
        status=res["status"],
        best_score=res["best_score"],
        hits=[ClaimHit(**h) for h in res["hits"]],
    )
