# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
import requests, urllib.parse

from .base import AgenteFuente  # interfaz existente en tu repo

EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

def _mk_url_from_ids(pmid: str | None, doi: str | None) -> str:
    if doi:
        return f"https://doi.org/{doi}"
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return ""

def search(query: str, page_size: int = 8, timeout: float = 15.0) -> List[Dict[str, Any]]:
    q = urllib.parse.quote_plus(query)
    url = f"{EPMC_URL}?query={q}&pageSize={int(page_size)}&format=json"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    out: List[Dict[str, Any]] = []
    for it in (data.get("resultList", {}) or {}).get("result", []) or []:
        pmid = (it.get("pmid") or "").strip() or None
        doi = (it.get("doi") or "").strip() or None
        title = (it.get("title") or "").strip()
        abstract = (it.get("abstractText") or "").strip()
        out.append({
            "source": "europepmc",
            "pmid": pmid,
            "doi": doi,
            "url": _mk_url_from_ids(pmid, doi),
            "title": title,
            "abstract": abstract,
            "year": it.get("pubYear"),
            "journal": it.get("journalTitle"),
        })
    return out

# —— Clase esperada por registry —— #
class AgenteEuropePMC(AgenteFuente):
    name = "europepmc"
    timeout_default = 15.0

    def buscar(self, claim: str, deadline: datetime):
        """Interfaz requerida por AgenteFuente. No usada en el flujo actual."""
        # Puedes implementar aquí si más adelante quieres usar el orquestador de agentes.
        return None
