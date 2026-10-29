# -*- coding: utf-8 -*-
"""
Adaptador de extracción de claims.
Mantiene la API clásica extract_claims_from_pptx(...) pero por dentro usa el LLM.
"""

from typing import List, Dict, Any
from .llm_claim_extractor import extract_claims_from_pptx_llm

def extract_claims_from_pptx(path_pptx: str, max_claims_per_slide: int = 1) -> List[str]:
    """
    API compatible: devuelve sólo el texto de los claims.
    """
    items = extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
    return [it["text"] for it in items]

def extract_claims_with_debug(path_pptx: str, max_claims_per_slide: int = 1) -> List[Dict[str, Any]]:
    """
    Variante con metadata (score, slide_index, debug) para auditoría.
    """
    return extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
