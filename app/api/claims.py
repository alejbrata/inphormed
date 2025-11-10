# app/api/claims.py — endpoint estable para validar claims por texto (web-first + LLM)
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.claim_validator import ClaimValidatorService

router = APIRouter(prefix="/api/claims", tags=["claims"])


# ─────────────────────────────────────────────────────────────
# Esquemas de E/S (Pydantic)
# ─────────────────────────────────────────────────────────────
class ClaimHit(BaseModel):
    source: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    year: Optional[str] = None
    score: float = 0.0


class ValidateTextRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Claim a validar")
    topk: int = Field(default=int(os.getenv("RAG_TOPK", "8")), ge=1, le=20)
    thr_green: float = Field(default=float(os.getenv("RAG_THR_GREEN", "0.82")))
    thr_yellow: float = Field(default=float(os.getenv("RAG_THR_YELLOW", "0.70")))


class ValidateTextResponse(BaseModel):
    where: str = "text"
    text: str
    claim_id: str
    status: str
    best_score: float
    hits: List[ClaimHit]


# ─────────────────────────────────────────────────────────────
# DI simple para el servicio
# ─────────────────────────────────────────────────────────────
def get_validator() -> ClaimValidatorService:
    return ClaimValidatorService(
        evidence=None,  # web-first (PubMed, EuropePMC, Crossref)
        topk=int(os.getenv("RAG_TOPK", "8")),
        thr_green=float(os.getenv("RAG_THR_GREEN", "0.82")),
        thr_yellow=float(os.getenv("RAG_THR_YELLOW", "0.70")),
    )


# ─────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────
@router.post("/validate-text", response_model=ValidateTextResponse)
def validate_text(req: ValidateTextRequest, validator: ClaimValidatorService = Depends(get_validator)):
    # Permite ajustar por-request
    validator.topk = req.topk
    validator.thr_green = req.thr_green
    validator.thr_yellow = req.thr_yellow

    res: Dict[str, Any] = validator.validate(req.text)

    claim_id = hashlib.sha256(req.text.encode("utf-8")).hexdigest()[:16]
    hits_models = [ClaimHit(**h) for h in (res.get("hits") or [])]

    return ValidateTextResponse(
        where="text",
        text=req.text,
        claim_id=claim_id,
        status=res.get("status", "red"),
        best_score=float(res.get("best_score", 0.0)),
        hits=hits_models,
    )
