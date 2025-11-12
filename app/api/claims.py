from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Optional

from app.domain.core_models import Claim, SlideContext
from app.llm.judge import LLMJudge
from app.agents.sources.registry import get_default_fuentes
from app.agents.orchestrator.llm_first import orchestrate_llm_first

router = APIRouter(prefix="/api/claims", tags=["claims"])

@router.get("/validate", summary="Valida un claim contra PubMed (LLM-first)")
async def validate_claim_llm_first(
    claim_text: str = Query(..., description="Texto del claim"),
    slide_title: Optional[str] = Query("", description="Título de la slide"),
    slide_excerpt: Optional[str] = Query("", description="Extracto visible"),
    topk: int = Query(5, ge=1, le=10),
    mock_llm: bool = Query(False, description="Usa juez simulado para pruebas")
):
    claim = Claim(text=claim_text)
    slide = SlideContext(title=slide_title or "", excerpt=slide_excerpt or "")

    fuentes = get_default_fuentes()
    judge = LLMJudge(mock=mock_llm)

    result = await orchestrate_llm_first(
        claim=claim,
        slide_ctx=slide,
        sources=fuentes,
        llm_judge=judge,
        topk=topk,
    )
    return result
