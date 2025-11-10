# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
import os, requests, urllib.parse, xml.etree.ElementTree as ET

from .base import AgenteFuente

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

def _params(extra: Dict[str,str]) -> Dict[str,str]:
    p = {"tool": "inphormed"}
    if NCBI_EMAIL: p["email"] = NCBI_EMAIL
    if NCBI_API_KEY: p["api_key"] = NCBI_API_KEY
    p.update(extra)
    return p

def _mk_url_from_pmid(pmid: str | None) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

def search(query: str, page_size: int = 8, timeout: float = 15.0) -> List[Dict[str, Any]]:
    q = urllib.parse.quote_plus(query)
    # 1) ESearch
    r = requests.get(f"{EUTILS}/esearch.fcgi",
                     params=_params({"db":"pubmed","retmode":"json","retmax":str(page_size),"term":q}),
                     timeout=timeout)
    r.raise_for_status()
    ids = (r.json().get("esearchresult", {}).get("idlist", []) or [])[:page_size]
    if not ids:
        return []

    # 2) EFetch
    r2 = requests.get(f"{EUTILS}/efetch.fcgi",
                      params=_params({"db":"pubmed","retmode":"xml","id":",".join(ids)}),
                      timeout=timeout)
    r2.raise_for_status()

    out: List[Dict[str, Any]] = []
    root = ET.fromstring(r2.text)
    for art in root.findall(".//PubmedArticle"):
        pmid = (art.findtext(".//PMID") or "").strip() or None
        title = (art.findtext(".//ArticleTitle") or "").strip()
        abs_nodes = art.findall(".//Abstract/AbstractText")
        abstract = " ".join([(t.text or "").strip() for t in abs_nodes if (t.text or "").strip()])
        doi = None
        for idnode in art.findall(".//ArticleIdList/ArticleId"):
            if (idnode.get("IdType") or "").lower() == "doi":
                doi = (idnode.text or "").strip()
                break
        out.append({
            "source": "pubmed",
            "pmid": pmid,
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else _mk_url_from_pmid(pmid)),
            "title": title,
            "abstract": abstract,
            "year": art.findtext(".//Journal/JournalIssue/PubDate/Year"),
            "journal": art.findtext(".//Journal/Title"),
        })
    return out

class AgentePubMed(AgenteFuente):
    name = "pubmed"
    timeout_default = 15.0
    def buscar(self, claim: str, deadline: datetime):
        return None
