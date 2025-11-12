from __future__ import annotations
from typing import List, Any
from .pubmed import AgentePubMed
from .base import BaseSourceAgent

def get_default_sources(**kwargs: Any) -> List[BaseSourceAgent]:
    return [AgentePubMed()]

get_default_fuentes = get_default_sources
