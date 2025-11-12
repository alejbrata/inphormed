from __future__ import annotations
import abc
from typing import List
from app.domain.core_models import Claim, CandidateDoc

class BaseSourceAgent(abc.ABC):
    name: str = "base"
    timeout_default: float = 6.0  # segundos

    @abc.abstractmethod
    async def fetch_candidates(self, claim: Claim, limit: int = 5) -> List[CandidateDoc]:
        """Devuelve candidatos (sin puntuar) para que el LLM los juzgue."""
        raise NotImplementedError
