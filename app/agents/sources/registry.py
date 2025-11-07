from __future__ import annotations
from typing import List, Any

# Si tu interfaz vive aquí:
from .base import AgenteFuente
from .europepmc import AgenteEuropePMC
# from .ctgov import AgenteCTGov  # déjalo comentado hasta que tenga implementación real


def get_default_sources(*, indexer: Any = None, auditor: Any = None, **kwargs) -> List[AgenteFuente]:
    """
    Devuelve la lista de agentes de fuente habilitados por defecto.

    Parámetros (compat):
      - indexer, auditor: aceptados para compatibilidad con call-sites que los pasan,
        pero los agentes de 'fuente' NO deben usarlos (solo buscan y devuelven).
      - **kwargs: se aceptan silenciosamente para no romper en el futuro.

    Nota: si algún agente llegara a necesitar deps, se le inyectarán aquí.
    """
    agentes: List[AgenteFuente] = [
        AgenteEuropePMC(),
        # AgenteCTGov(),
    ]
    return agentes


# Alias en español usado por el API
def get_default_fuentes(*, indexer: Any = None, auditor: Any = None, **kwargs) -> List[AgenteFuente]:
    return get_default_sources(indexer=indexer, auditor=auditor, **kwargs)
