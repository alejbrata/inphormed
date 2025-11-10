# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
import os, re, requests

from .base import AgenteFuente

CROSSREF = "https://api.crossref.org/works"
MAILTO = os.getenv("CROSSREF_MAILTO", "")

JATS_TAGS = re.compile(r"</?[^>]+>")

def _clean_abstract(s: str) -> str:
    s = (s or "").strip()
    return JATS_TAGS.sub("", s)

def search(query: str, page_size: int = 8, timeout: float = 15.0) -> List[Dict[str, Any]]:
    params = {"query": query, "rows": int(page_size)}
    if MAILTO:
        params["mailto"] = MAILTO
    r = requests.get(CROSSREF, params=params, timeout=timeout)
    r.raise_for_status()
    data = (r.json() or {}).get("message", {})
    out: List[Dict[str, Any]] = []
    for it in data.get("items", []) or []:
        doi = (it.get("DOI") or "").strip() or None
        title_list = it.get("title") or []
        title = (title_list[0] if title_list else "").strip()
        abstract = _clean_abstract(it.get("abstract") or "")
        out.append({
            "source": "crossref",
            "pmid": None,
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else ""),
            "title": title,
            "abstract": abstract,
            "year": (it.get("issued", {}).get("date-parts", [[None]])[0][0]),
            "journal": (it.get("container-title", [None])[0]),
        })
    return out

class AgenteCrossref(AgenteFuente):
    name = "crossref"
    timeout_default = 15.0
    def buscar(self, claim: str, deadline: datetime):
        return None
