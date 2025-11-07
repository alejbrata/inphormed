from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from app.agents.sources.base import AgenteFuente

if TYPE_CHECKING:
    from app.schemas import ResultadoFuente


class AgenteEuropePMC(AgenteFuente):
    name: str = "europe_pmc"
    timeout_default: int = 8

    def buscar(self, claim: str, deadline: datetime) -> Optional["ResultadoFuente"]:
        # TODO: implementar búsqueda real con timeout respetando `deadline`
        # y devolver ResultadoFuente o None.
        return None
