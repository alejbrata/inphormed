# -*- coding: utf-8 -*-
"""
Puerta única para extraer claims desde PPTX con IA generativa.
(No toca utils/ref_extractor.py, que es para referencias.)
"""

from typing import List, Dict, Any
from app.agents.claims.llm_claim_extractor import extract_claims_from_pptx_llm

def extract_claims_from_pptx(path_pptx: str, max_claims_per_slide: int = 1) -> List[str]:
    items = extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
    return [it["text"] for it in items]

def extract_claims_with_debug(path_pptx: str, max_claims_per_slide: int = 1) -> List[Dict[str, Any]]:
    return extract_claims_from_pptx_llm(path_pptx, max_claims_per_slide=max_claims_per_slide)
