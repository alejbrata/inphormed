# app/utils/claim_extractor.py
# -*- coding: utf-8 -*-
"""
Extractor de CLAIMS (no referencias) desde PPTX, vía LLM.
No toca ref_extractor. Este módulo es la única puerta pública para claims.
"""

from typing import List, Dict, Any
from app.agents.claims.llm_claim_extractor import extract_claims_from_pptx_llm

def extract_claims_from_pptx(path_pptx: str, max_claims_per_slide: int = 1) -> List[str]:
    """
    Devuelve SOLO los textos de claim (limpios), 1..N por deck.
    """
    items = extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
    return [it["text"] for it in items]

def extract_claims_with_debug(path_pptx: str, max_claims_per_slide: int = 1) -> List[Dict[str, Any]]:
    """
    Igual que arriba pero con metadata (slide_index, score, debug).
    Útil para logs/auditoría y troubleshooting.
    """
    return extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
