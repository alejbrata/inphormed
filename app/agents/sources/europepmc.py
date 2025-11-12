from __future__ import annotations
from typing import List
from app.models.core import Claim, CandidateDoc
from .base import BaseSourceAgent

class AgenteEuropePMC(BaseSourceAgent):
    name = "epmc"
    timeout_default = 6.0

    async def fetch_candidates(self, claim: Claim, limit: int = 3) -> List[CandidateDoc]:
        # Stub: devuelve vacío por defecto hasta implementarlo.
        return []
