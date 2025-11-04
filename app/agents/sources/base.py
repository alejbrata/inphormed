# app/services/agents/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TYPE_CHECKING

# Evita dependencia dura mientras aún no creamos schemas.py:
if TYPE_CHECKING:
    from app.schemas import ResultadoFuente


class AgenteFuente(ABC):
    """
    Contrato para agentes que buscan evidencia en una fuente concreta (PubMed, CT.gov, EMA, ...).

    Reglas del contrato (muy importantes):
    - Entrada:     claim (str) + deadline (datetime UTC).
    - Salida:      ResultadoFuente (mínimo: id_externo, source, url, texto) o None si no hay hallazgo útil.
    - Rendimiento: debe respetar el deadline (timeouts cortos; nada de operaciones largas).
    - Idempotente: NO debe indexar, embedir ni mutar el sistema. Solo "buscar y devolver".
    - Minimalismo: NO hace normalización compleja; eso lo hace el NormalizadorDocumento.
    - Robustez:    captura errores de red/parse y devuelve None en vez de romper el orquestador.

    El orquestador lanzará varios AgenteFuente en *modo carrera*; el primero que devuelva
    un ResultadoFuente válido "gana" y dispara la ingesta + indexado.
    """

    # Nombre único del agente (p. ej., "pubmed", "ctgov", "ema")
    name: str = "base"

    # Timeout por defecto si el orquestador no especifica uno (segundos)
    timeout_default: int = 8

    @abstractmethod
    def buscar(self, claim: str, deadline: datetime) -> Optional["ResultadoFuente"]:
        """
        Busca evidencia sobre `claim` en la fuente de este agente.

        Debe:
          - Respetar el `deadline` (usar timeouts en HTTP, cortar bucles largos, etc.)
          - Devolver un ResultadoFuente si encuentra evidencia razonable; si no, None.
          - NO lanzar excepciones hacia arriba por fallos recuperables (red, 5xx); devolver None.

        No debe:
          - Hacer embeddings, chunking ni indexar (eso es responsabilidad de la ingesta).
          - Normalizar a nuestro esquema final más allá de lo básico (lo hace el NormalizadorDocumento).
        """
        ...
