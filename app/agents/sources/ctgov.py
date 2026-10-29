# app/agents/sources/ctgov.py
from __future__ import annotations
import requests
from typing import List, Optional

from app.agents.claims.base import AgenteFuente
from app.schemas import ResultadoFuente
from app.audit.auditor import Auditor
from app.ingest.chunker import create_chunks

# Usamos la API "study_fields" v1 por simplicidad
CTG_FIELDS = "NCTId,BriefTitle,Condition,BriefSummary,StudyType,Phase,StartDate,CompletionDate"
CTG_URL = "https://clinicaltrials.gov/api/query/study_fields"

class AgenteCTGov(AgenteFuente):
    """
    ClinicalTrials.gov: útil para claims que mencionan ensayos, fases, eficacia/seguridad.
    """
    def __init__(self, indexer=None, auditor: Optional[Auditor]=None):
        self.indexer = indexer
        self.auditor = auditor or Auditor()

    def fuente(self) -> str:
        return "ctgov"

    def _build_expr(self, claim: str) -> str:
        # expr básico: Claim en texto libre (se puede mejorar con Condition= hidradenitis suppurativa)
        # Por defecto, ClinicalTrials hace AND entre términos; podemos dejarlo simple.
        return claim

    def buscar(self, claim: str, top_k:int=10, idioma: Optional[str]=None) -> List[ResultadoFuente]:
        expr = self._build_expr(claim)
        params = {
            "expr": expr,
            "fields": CTG_FIELDS,
            "min_rnk": 1,
            "max_rnk": top_k,
            "fmt": "json"
        }
        self.auditor.log("CTGov.query", {"params": params})
        r = requests.get(CTG_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        studies = data.get("StudyFieldsResponse", {}).get("StudyFields", []) or []
        out: List[ResultadoFuente] = []
        for s in studies[:top_k]:
            nct = (s.get("NCTId") or [""])[0]
            title = (s.get("BriefTitle") or [""])[0]
            summary = (s.get("BriefSummary") or [""])[0]
            url = f"https://clinicaltrials.gov/study/{nct}" if nct else ""
            meta = {
                "condition": (s.get("Condition") or []),
                "study_type": (s.get("StudyType") or [""])[0],
                "phase": (s.get("Phase") or [""])[0],
                "start": (s.get("StartDate") or [""])[0],
                "completion": (s.get("CompletionDate") or [""])[0],
            }
            out.append(ResultadoFuente(
                source=self.fuente(),
                id_externo=nct or url or title,
                title=title,
                url=url,
                published_at=None,
                license=None,
                text=summary,
                metadata=meta
            ))
        self.auditor.log("CTGov.results", {"count": len(out)})
        return out

    def ingerir_y_indexar(self, res: List[ResultadoFuente]) -> int:
        if not res or not self.indexer:
            return 0
        total = 0
        for r in res:
            chunks = create_chunks(r)
            total += self.indexer.index(chunks)
        self.auditor.log("CTGov.indexed", {"chunks": total})
        return total
