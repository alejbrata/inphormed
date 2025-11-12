# app/agents/sources/base.py
from __future__ import annotations
import abc
from typing import List
# --- ¡CAMBIO REALIZADO AQUÍ! ---
from app.domain.core_models import Claim, CandidateDoc, SlideContext

class BaseSourceAgent(abc.ABC):
    name: str = "base"
    timeout_default: float = 6.0

    @abc.abstractmethod
    # --- ¡CAMBIO REALIZADO AQUÍ! ---
    async def fetch_candidates(
        self, 
        claim: Claim, 
        slide_ctx: SlideContext, 
        limit: int = 5
    ) -> List[CandidateDoc]:
        """Devuelve candidatos (sin puntuar) para que el LLM los juzgue."""
        raise NotImplementedError