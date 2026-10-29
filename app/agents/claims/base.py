# Compatibilidad hacia atrás:
# Antes algunos módulos importaban desde app.agents.claims.base.
# Ahora la abstracción vive en app.services.agents.base.
from app.agents.sources.base import AgenteFuente  # reexport
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Solo para type hints, evita dependencia dura en runtime
    from app.schemas import ResultadoFuente  # noqa: F401

__all__ = ["AgenteFuente", "ResultadoFuente"]
