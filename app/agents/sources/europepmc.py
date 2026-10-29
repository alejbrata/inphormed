# app/agents/sources/europepmc.py
from __future__ import annotations
from typing import List
# --- ¡CAMBIO REALIZADO AQUÍ! ---
from app.domain.core_models import Claim, CandidateDoc, SlideContext
from .base import BaseSourceAgent

class AgenteEuropePMC(BaseSourceAgent):
    name = "epmc"
    timeout_default = 6.0

    # --- ¡CAMBIO REALIZADO AQUÍ! ---
    async def fetch_candidates(
        self, 
        claim: Claim, 
        slide_ctx: SlideContext, 
        limit: int = 3
    ) -> List[CandidateDoc]:
        return []