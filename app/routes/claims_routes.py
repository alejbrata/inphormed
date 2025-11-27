from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
import os
import uuid

from app.services.claim_extractor import extract_claims_from_pptx
from app.vector.qdrant_store import QdrantStore
from app.vector.embedder import EmbedderMiniLM
from app.repository.evidence_repo import EvidenceRepository
from app.services.claim_validator import ClaimValidatorService
# --- NUEVO: validar un claim de texto libre ---
from hashlib import sha256 as _sha

# Compliance (Re-integrated)
from app.compliance.engine import ComplianceEngine
from app.schemas import Citation

# Importamos la caché compartida para el Viewer
from app.api.validation_routes import SNIPPET_CACHE

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
    # Compliance fields
    compliance_status: Optional[str] = None
    compliance_reason: Optional[str] = None

class ValidatePptResponse(BaseModel):
    file_name: str
    doc_id: str
    total_claims: int
    results: List[ClaimResult]

# --------- Dependencias para inyectar servicios ----------
def get_validator() -> ClaimValidatorService:
    if not _QDRANT_URL:
        # Fallback si no hay Qdrant, aunque ClaimValidatorService actual es web-first
        pass 
    # store = QdrantStore(url=_QDRANT_URL, api_key=_QDRANT_KEY, collection=_EVID_COLL, dim=_EMBED_DIM)
    # repo  = EvidenceRepository(store=store, embedder=EmbedderMiniLM())
    # repo.ensure_ready()
    # return ClaimValidatorService(evidence=repo, topk=_RAG_TOPK, thr_green=_THR_GREEN, thr_yellow=_THR_YELLOW)
    
    # Usamos la versión web-first directa
    return ClaimValidatorService(topk=_RAG_TOPK, thr_green=_THR_GREEN, thr_yellow=_THR_YELLOW)

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

    # Instanciamos Compliance Engine
    comp_engine = ComplianceEngine()

    for c in claims:
        # AWAIT HERE
        res = await validator.validate(c["text"])
        
        # --- CACHE LOGIC FOR VIEWER ---
        # Si hay hits, tomamos el mejor (el primero) y lo guardamos en caché para el viewer
        if res["hits"]:
            best_hit = res["hits"][0]
            # Generamos un ID único para este snippet
            snippet_id = f"claim_{c.get('claim_id', uuid.uuid4().hex)}"
            
            SNIPPET_CACHE[snippet_id] = {
                "claim": c["text"],
                "snippet": (best_hit.get("text") or "")[:500] + "...", # Snippet corto para display
                "full_text": best_hit.get("text") or "Texto no disponible",
                "paper_title": best_hit.get("title", ""),
                "pubmed_url": best_hit.get("url", "") # URL original
            }
            
            # Sobreescribimos la URL del hit para que apunte al viewer
            best_hit["url"] = f"/api/viewer?id={snippet_id}"

        # Compliance Check
        citations = [
            Citation(
                source=h.get("source"),
                url=h.get("url"),
                title=h.get("title"),
                score=h.get("score")
            ) for h in res["hits"]
        ]
        
        comp_report = comp_engine.run_checks(claim=c["text"], citations=citations)
        compliance_status = "pass" if comp_report.passed else "fail"
        compliance_reason = None
        if not comp_report.passed and comp_report.issues:
            # Tomamos el primer fallo o concatenamos
            failures = [i.reason for i in comp_report.issues if not i.passed]
            compliance_reason = "; ".join(failures) if failures else "Compliance check failed"

        results.append({
            "where": c["where"],
            "text": c["text"],
            "claim_id": c["claim_id"],
            "status": res["status"],
            "best_score": res["best_score"],
            "hits": res["hits"],
            "compliance_status": compliance_status,
            "compliance_reason": compliance_reason,
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
    compliance_status: Optional[str] = None
    compliance_reason: Optional[str] = None

def _sha16(s: str) -> str:
    return _sha(s.encode("utf-8")).hexdigest()[:16]

@router.post("/validate-text", response_model=ValidateTextResponse, tags=["claims"])
async def validate_text(req: ValidateTextRequest, validator: ClaimValidatorService = Depends(get_validator)):
    validator.topk = req.topk
    validator.thr_green = req.thr_green
    validator.thr_yellow = req.thr_yellow

    # AWAIT HERE
    res = await validator.validate(req.text)
    
    # --- CACHE LOGIC FOR VIEWER (TEXT) ---
    if res["hits"]:
        best_hit = res["hits"][0]
        snippet_id = f"text_{_sha16(req.text)}"
        
        SNIPPET_CACHE[snippet_id] = {
            "claim": req.text,
            "snippet": (best_hit.get("text") or "")[:500] + "...",
            "full_text": best_hit.get("text") or "Texto no disponible",
            "paper_title": best_hit.get("title", ""),
            "pubmed_url": best_hit.get("url", "")
        }
        best_hit["url"] = f"/api/viewer?id={snippet_id}"

    # Compliance Check (también para texto libre)
    comp_engine = ComplianceEngine()
    citations = [
        Citation(
            source=h.get("source"),
            url=h.get("url"),
            title=h.get("title"),
            score=h.get("score")
        ) for h in res["hits"]
    ]
    comp_report = comp_engine.run_checks(claim=req.text, citations=citations)
    compliance_status = "pass" if comp_report.passed else "fail"
    compliance_reason = None
    if not comp_report.passed and comp_report.issues:
        failures = [i.reason for i in comp_report.issues if not i.passed]
        compliance_reason = "; ".join(failures) if failures else "Compliance check failed"

    return ValidateTextResponse(
        where="text",
        text=req.text,
        claim_id=_sha16(req.text),
        status=res["status"],
        best_score=res["best_score"],
        hits=[ClaimHit(**h) for h in res["hits"]],
        compliance_status=compliance_status,
        compliance_reason=compliance_reason,
    )
