# app/agents/sources/pubmed.py  (versión completa smart)
from __future__ import annotations
from typing import List, Optional, Dict, Any
import os
import re
import requests
import xml.etree.ElementTree as ET

from app.schemas import ResultadoFuente

_PERC = re.compile(r"\b\d{1,3}(\.\d+)?\s?%")

def _build_term(claim: str, rewritten: str) -> str:
    """
    Construye una query PubMed acotada:
    - Usa Title/Abstract
    - Si ve % o palabras de epidemiología → enfoca a prevalence/incidence
    - Si ve comparativas → Clinical Trial/RCT
    - Idiomas: inglés/español
    - Rango temporal: ~10 años (reldate=3650 días)
    """
    base = (rewritten or claim or "").strip()
    if not base:
        return ""

    tiab = f"({base})[Title/Abstract]"

    epi = any(k in base.lower() for k in ["prevalence","incidence","epidemiolog", "porcentaje","prevalencia","incidencia"]) or bool(_PERC.search(base))
    comp = any(k in base.lower() for k in ["vs", "versus", "noninferior", "superior", "superiority", "reduce", "reducción", "mejor", "improves","inferior"])

    filters = []
    if epi:
        filters.append("(prevalence[Title/Abstract] OR incidence[Title/Abstract] OR epidemiology[Subheading])")
    if comp:
        filters.append("(randomized controlled trial[Publication Type] OR clinical trial[Publication Type] OR comparative study[Publication Type])")

    filters.append("(english[lang] OR spanish[lang])")
    # Nota: el reldate se aplica en esearch (no en el término), lo pasaremos como parámetro

    if filters:
        return f"{tiab} AND {' AND '.join(filters)}"
    return tiab

class AgentePubMed:
    def __init__(self, indexer=None, auditor=None, api_key: Optional[str] = None, reldays: int = 3650) -> None:
        self.indexer = indexer
        self.auditor = auditor
        self.reldays = int(os.getenv("PUBMED_RELDAYS", reldays))
        try:
            from app.config.settings import settings
            self.api_key = api_key or os.getenv("NCBI_API_KEY") or getattr(settings, "NCBI_API_KEY", "")
        except Exception:
            self.api_key = api_key or os.getenv("NCBI_API_KEY", "")
        self.base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Inphormed/0.1 (+github.com/alejbrata/inphormed)"})

    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            if self.auditor and hasattr(self.auditor, "log_event"):
                try: self.auditor.log_event(event, payload)  # noqa: E701
                except TypeError: self.auditor.log_event(payload)  # noqa: E701
        except Exception:
            pass

    def buscar(self, *, claim: str, query: str, top_k: int = 8) -> List[ResultadoFuente]:
        term = _build_term(claim, query)
        if not term:
            return []
        ids = self._esearch_ids(term, top_k)
        if not ids:
            return []

        metas = self._esummary(ids)
        details = self._efetch_xml(ids)
        abstracts = self._efetch_abstracts(ids)

        out: List[ResultadoFuente] = []
        for pmid in ids:
            m = metas.get(pmid, {})
            d = details.get(pmid, {})
            title = m.get("title") or d.get("title") or pmid
            pubdate = m.get("pubdate") or d.get("year")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            text = abstracts.get(pmid) or title or ""

            meta = {
                "pmid": pmid,
                "journal": m.get("fulljournalname") or d.get("journal"),
                "journal_abbrev": d.get("journal_abbrev"),
                "pubdate": pubdate,
                "year": d.get("year"),
                "volume": d.get("volume"),
                "issue": d.get("issue"),
                "pages": d.get("pages"),
                "doi": d.get("doi"),
                "pmcid": d.get("pmcid"),
                "authors": m.get("authors") or d.get("authors"),
                "esummary": m,
            }
            out.append(
                ResultadoFuente(
                    source="pubmed",
                    id_externo=pmid,
                    title=title,
                    url=url,
                    published_at=pubdate,
                    license=None,
                    text=text,
                    metadata=meta,
                )
            )

        self._audit("PubMedFetched", {"count": len(out), "term": term})
        return out

    # ---------- E-utilities helpers ----------
    def _esearch_ids(self, term: str, retmax: int) -> List[str]:
        p = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": str(retmax),
            "sort": "relevance",
            "reldate": str(self.reldays),   # últimos X días (≈10 años por defecto)
            "datetype": "edat"
        }
        if self.api_key:
            p["api_key"] = self.api_key
        try:
            r = self.session.get(self.base + "esearch.fcgi", params=p, timeout=25); r.raise_for_status()
            return (r.json().get("esearchresult", {}) or {}).get("idlist", [])[:retmax]
        except Exception:
            return []

    def _esummary(self, ids: List[str]) -> Dict[str, Any]:
        if not ids: return {}
        p = {"db":"pubmed","id":",".join(ids),"retmode":"json"}
        if self.api_key: p["api_key"]=self.api_key
        try:
            r = self.session.get(self.base + "esummary.fcgi", params=p, timeout=25); r.raise_for_status()
            data = r.json().get("result", {})
            out: Dict[str, Any] = {}
            for uid in data.get("uids", []):
                rec = data.get(uid, {})
                out[uid] = {
                    "title": rec.get("title"),
                    "fulljournalname": rec.get("fulljournalname"),
                    "pubdate": rec.get("pubdate"),
                    "authors": [a.get("name") for a in rec.get("authors", []) if isinstance(a, dict)],
                }
            return out
        except Exception:
            return {}

    def _efetch_abstracts(self, ids: List[str]) -> Dict[str, str]:
        if not ids: return {}
        p = {"db":"pubmed","id":",".join(ids),"rettype":"abstract","retmode":"text"}
        if self.api_key: p["api_key"]=self.api_key
        try:
            r = self.session.get(self.base + "efetch.fcgi", params=p, timeout=35); r.raise_for_status()
            parts = [p.strip() for p in r.text.strip().split("\n\n") if p.strip()]
            out: Dict[str, str] = {}
            for i, pmid in enumerate(ids):
                out[pmid] = parts[i] if i < len(parts) else ""
            return out
        except Exception:
            return {}

    def _efetch_xml(self, ids: List[str]) -> Dict[str, Dict[str, str]]:
        if not ids: return {}
        p = {"db":"pubmed","id":",".join(ids),"retmode":"xml"}
        if self.api_key: p["api_key"]=self.api_key
        out: Dict[str, Dict[str,str]] = {}
        try:
            r = self.session.get(self.base + "efetch.fcgi", params=p, timeout=35); r.raise_for_status()
            root = ET.fromstring(r.text)
            for art in root.findall(".//PubmedArticle"):
                pmid = (art.findtext(".//PMID") or "").strip()
                if not pmid: continue
                title = (art.findtext(".//ArticleTitle") or "").strip()
                jr = art.find(".//Journal")
                j_abbr = jr.findtext("ISOAbbreviation").strip() if jr is not None and jr.findtext("ISOAbbreviation") else None
                j_full = jr.findtext("Title").strip() if jr is not None and jr.findtext("Title") else None
                year = art.findtext(".//JournalIssue/PubDate/Year") or art.findtext(".//ArticleDate/Year")
                volume = art.findtext(".//JournalIssue/Volume")
                issue = art.findtext(".//JournalIssue/Issue")
                pages = art.findtext(".//Pagination/MedlinePgn")
                doi = None
                pmcid = None
                for aid in art.findall(".//ArticleIdList/ArticleId"):
                    idtype = (aid.attrib.get("IdType") or "").lower()
                    val = (aid.text or "").strip()
                    if idtype == "doi": doi = val
                    if idtype == "pmcid": pmcid = val
                authors = []
                for au in art.findall(".//AuthorList/Author"):
                    last = (au.findtext("LastName") or "").strip()
                    init = (au.findtext("Initials") or "").strip()
                    if last:
                        authors.append(f"{last} {init}".strip())
                out[pmid] = {
                    "title": title,
                    "journal": j_full,
                    "journal_abbrev": j_abbr,
                    "year": year,
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "doi": doi,
                    "pmcid": pmcid,
                    "authors": authors or None,
                }
            return out
        except Exception:
            return {}
