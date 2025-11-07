# app/agents/sources/crossref.py
from __future__ import annotations
import requests
from typing import List, Optional

from app.agents.claims.base import AgenteFuente
from app.schemas import ResultadoFuente
from app.audit.auditor import Auditor
from app.ingest.chunker import create_chunks

CROSSREF_URL = "https://api.crossref.org/works"

class AgenteCrossref(AgenteFuente):
    """
    Crossref: buena puerta para DOIs + metadatos (título, revista, fecha). A menudo sin abstract.
    """
    def __init__(self, indexer=None, auditor: Optional[Auditor]=None, rows:int=20):
        self.indexer = indexer
        self.auditor = auditor or Auditor()
        self.rows = rows

    def fuente(self) -> str:
        return "crossref"

    def buscar(self, claim: str, top_k:int=10, idioma: Optional[str]="en") -> List[ResultadoFuente]:
        params = {
            "query": claim,
            "rows": min(top_k, self.rows),
            "select": "DOI,title,author,container-title,issued,page,volume,issue,URL,language"
        }
        self.auditor.log("Crossref.query", {"params": params})
        r = requests.get(CROSSREF_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("message", {}).get("items", []) or []
        out: List[ResultadoFuente] = []
        for it in items[:top_k]:
            doi = it.get("DOI")
            title = (it.get("title") or [""])[0]
            url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")
            year = None
            issued = it.get("issued", {}).get("date-parts", [])
            if issued and issued[0]:
                year = str(issued[0][0])
            # Crossref suele no traer abstract → text vacío (servirá como señal para que otro agente lo complete)
            meta = {
                "doi": doi,
                "journal": (it.get("container-title") or [""])[0],
                "volume": it.get("volume"),
                "issue": it.get("issue"),
                "pages": it.get("page"),
                "language": it.get("language"),
                "authors": it.get("author"),
            }
            out.append(ResultadoFuente(
                source=self.fuente(),
                id_externo=doi or url or title,
                title=title,
                url=url,
                published_at=year,
                license=None,
                text="",
                metadata=meta
            ))
        self.auditor.log("Crossref.results", {"count": len(out)})
        return out

    def ingerir_y_indexar(self, res: List[ResultadoFuente]) -> int:
        if not res or not self.indexer:
            return 0
        total = 0
        for r in res:
            chunks = create_chunks(r)
            total += self.indexer.index(chunks)
        self.auditor.log("Crossref.indexed", {"chunks": total})
        return total
