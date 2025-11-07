# app/agents/sources/ema.py
from __future__ import annotations
from typing import List
from app.schemas import ResultadoFuente

class AgenteEMA:
    """
    Stub inicial para EMA. Devuelve vacío por ahora.
    Más adelante podremos integrar scraping / endpoints oficiales.
    """
    def __init__(self, indexer=None, auditor=None) -> None:
        self.indexer = indexer
        self.auditor = auditor

    def buscar(self, *, claim: str, query: str, top_k: int = 8) -> List[ResultadoFuente]:
        return []
