# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.claim_validator import validate_claim_text

router = APIRouter(prefix="/api/claims", tags=["claims"])

class ValidateTextInput(BaseModel):
    text: str = Field(..., description="Claim a validar")
    topk: int = 8
    thr_green: float = 0.80
    thr_yellow: float = 0.65
    require_llm: bool = True  # reservado

@router.post("/validate-text")
async def validate_text(inp: ValidateTextInput) -> Dict[str, Any]:
    return validate_claim_text(
        text=inp.text,
        topk=int(inp.topk),
        thr_green=float(inp.thr_green),
        thr_yellow=float(inp.thr_yellow),
    )
