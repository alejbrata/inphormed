# app/services/claim_validator.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.repository.evidence_repo import EvidenceRepository


def _status_from_score(score: float, thr_green: float, thr_yellow: float) -> str:
    if score >= thr_green:
        return "green"
    if score >= thr_yellow:
        return "yellow"
    return "red"


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Lee atributo o clave dict de forma tolerante."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class ClaimValidatorService:
    evidence: EvidenceRepository
    topk: int = 5
    thr_green: float = 0.82
    thr_yellow: float = 0.70

    def validate(self, claim_text: str) -> Dict[str, Any]:
        """
        Busca evidencia para `claim_text` en la base vectorial y calcula el semáforo.
        Retorna:
        {
          "status": "green|yellow|red",
          "best_score": float,
          "hits": [
            {"score": float, "text": str, "title": str|None, "pmid": str|None,
             "doi": str|None, "url": str|None, "year": int|None, "section": str|None},
            ...
          ]
        }
        """
        # Consulta vectorial
        results = self.evidence.search_text(claim_text, k=self.topk)

        # Normaliza a lista (algunas versiones devuelven objeto con .points)
        if hasattr(results, "points"):
            points = results.points  # type: ignore[attr-defined]
        else:
            points = results or []

        hits: List[Dict[str, Any]] = []
        best = 0.0

        for h in points:
            score = float(_get_attr(h, "score", 0.0))
            if score > best:
                best = score

            payload = _get_attr(h, "payload", {}) or {}

            # Campos esperados por tu respuesta/Streamlit
            hit = {
                "score": score,
                "text": payload.get("text"),
                "title": payload.get("title"),
                "pmid": payload.get("pmid"),
                "doi": payload.get("doi"),
                # acepta 'landing_url' o 'url'
                "url": payload.get("landing_url") or payload.get("url"),
                "year": payload.get("year"),
                "section": payload.get("section"),
            }
            hits.append(hit)

        status = _status_from_score(best, self.thr_green, self.thr_yellow)

        return {
            "status": status,
            "best_score": best,
            "hits": hits,
        }
