# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
import os

from app.agents.sources import europepmc, pubmed, crossref

ENABLED = [s.strip() for s in os.getenv("EVIDENCE_SOURCES", "epmc,pubmed,crossref").split(",") if s.strip()]

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _dedupe(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_doi, seen_pmid, seen_title = set(), set(), set()
    out: List[Dict[str, Any]] = []
    for r in records:
        doi = _norm(r.get("doi"))
        pmid = _norm(r.get("pmid"))
        title = _norm(r.get("title"))
        if doi:
            if doi in seen_doi: continue
            seen_doi.add(doi)
        elif pmid:
            if pmid in seen_pmid: continue
            seen_pmid.add(pmid)
        else:
            if title in seen_title: continue
            seen_title.add(title)
        out.append(r)
    return out

def _rank(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(r: Dict[str, Any]) -> float:
        has_abs = 1.0 if (r.get("abstract") or "").strip() else 0.0
        has_id  = (0.6 if r.get("doi") else 0.0) + (0.4 if r.get("pmid") else 0.0)
        year    = 0
        try: year = int(r.get("year") or 0)
        except Exception: pass
        return 1.5*has_abs + has_id + 0.0001*year
    return sorted(records, key=score, reverse=True)

def search_evidence(query: str, page_size: int = 8, timeout: float = 15.0) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []
    try:
        if "epmc" in ENABLED:   all_results.extend(europepmc.search(query, page_size, timeout))
    except Exception: pass
    try:
        if "pubmed" in ENABLED: all_results.extend(pubmed.search(query, page_size, timeout))
    except Exception: pass
    try:
        if "crossref" in ENABLED: all_results.extend(crossref.search(query, page_size, timeout))
    except Exception: pass

    return _rank(_dedupe(all_results))[:page_size]
