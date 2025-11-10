# app/services/claim_validator.py  — reemplazo completo (web-first + LLM scoring)
from __future__ import annotations

import os, json, re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# HTTP
import requests

# ─────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────
def _status_from_score(score: float, thr_green: float, thr_yellow: float) -> str:
    if score >= thr_green:
        return "green"
    if score >= thr_yellow:
        return "yellow"
    return "red"

def _mk_url(pmid: Optional[str], doi: Optional[str], fallback: str = "") -> str:
    if doi:
        return f"https://doi.org/{doi}"
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return fallback

def _dedupe_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[Optional[str], Optional[str], str]] = set()
    out: List[Dict[str, Any]] = []
    for h in hits:
        key = (h.get("pmid"), h.get("doi"), (h.get("url") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out

def _strip(s: Optional[str]) -> str:
    return (s or "").strip()

# ─────────────────────────────────────────────────────────────
# Búsqueda web en 3 fuentes (EuropePMC, PubMed, Crossref)
# ─────────────────────────────────────────────────────────────
def _search_europepmc(query: str, rows: int = 6, timeout: float = 12.0) -> List[Dict[str, Any]]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    r = requests.get(url, params={"query": query, "pageSize": rows, "format": "json"}, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    out: List[Dict[str, Any]] = []
    for it in (data.get("resultList", {}) or {}).get("result", []) or []:
        pmid = _strip(it.get("pmid")) or None
        doi = _strip(it.get("doi")) or None
        title = _strip(it.get("title"))
        abstract = _strip(it.get("abstractText"))
        out.append({
            "source": "europepmc",
            "pmid": pmid,
            "doi": doi,
            "url": _mk_url(pmid, doi, _strip(it.get("fullTextUrlList", [{}])[0].get("url") if it.get("fullTextUrlList") else "")),
            "title": title,
            "text": abstract,
            "year": _strip(it.get("pubYear")),
            "journal": _strip(it.get("journalTitle")),
        })
    return out

def _search_pubmed(query: str, rows: int = 6, timeout: float = 12.0) -> List[Dict[str, Any]]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {"db":"pubmed","retmode":"json","retmax":str(rows),"term":query}
    email = os.getenv("NCBI_EMAIL") or ""
    api_key = os.getenv("NCBI_API_KEY") or ""
    if email: params["email"] = email
    if api_key: params["api_key"] = api_key

    r = requests.get(f"{base}/esearch.fcgi", params=params, timeout=timeout)
    r.raise_for_status()
    ids = (r.json().get("esearchresult", {}).get("idlist", []) or [])[:rows]
    if not ids:
        return []
    efetch_params = {"db":"pubmed","retmode":"xml","id":",".join(ids)}
    if api_key: efetch_params["api_key"] = api_key
    if email: efetch_params["email"] = email
    r2 = requests.get(f"{base}/efetch.fcgi", params=efetch_params, timeout=timeout)
    r2.raise_for_status()

    import xml.etree.ElementTree as ET
    root = ET.fromstring(r2.text)
    out: List[Dict[str, Any]] = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _strip(art.findtext(".//PMID")) or None
        title = _strip(art.findtext(".//ArticleTitle"))
        abs_nodes = art.findall(".//Abstract/AbstractText")
        abstract = " ".join([_strip(n.text) for n in abs_nodes if _strip(n.text)])
        doi = None
        for idnode in art.find(".//ArticleIdList") or []:
            if (idnode.get("IdType") or "").lower() == "doi":
                doi = _strip(idnode.text) or None
                break
        out.append({
            "source": "pubmed",
            "pmid": pmid,
            "doi": doi,
            "url": _mk_url(pmid, doi),
            "title": title,
            "text": abstract,
            "year": _strip(art.findtext(".//Journal/JournalIssue/PubDate/Year")),
            "journal": _strip(art.findtext(".//Journal/Title")),
        })
    return out

def _search_crossref(query: str, rows: int = 6, timeout: float = 12.0) -> List[Dict[str, Any]]:
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": rows}
    mailto = os.getenv("CROSSREF_MAILTO") or ""
    if mailto: params["mailto"] = mailto
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = (r.json() or {}).get("message", {})
    out: List[Dict[str, Any]] = []
    for it in data.get("items", []) or []:
        doi = _strip(it.get("DOI")) or None
        title_list = it.get("title") or []
        title = _strip(title_list[0]) if title_list else ""
        abstract = _strip(re.sub(r"</?[^>]+>", "", it.get("abstract") or ""))
        year = None
        dparts = (it.get("issued", {}).get("date-parts") or [[None]])
        if dparts and dparts[0] and dparts[0][0]:
            year = str(dparts[0][0])
        out.append({
            "source": "crossref",
            "pmid": None,
            "doi": doi,
            "url": _mk_url(None, doi, _strip(it.get("URL") or "")),
            "title": title,
            "text": abstract,
            "year": year,
            "journal": (it.get("container-title") or [None])[0],
        })
    return out

def _web_search_all(query: str, topk: int) -> List[Dict[str, Any]]:
    hits = []
    try: hits += _search_pubmed(query, rows=topk)
    except Exception: pass
    try: hits += _search_europepmc(query, rows=topk)
    except Exception: pass
    try: hits += _search_crossref(query, rows=max(3, topk//2))
    except Exception: pass
    hits = _dedupe_hits(hits)
    return hits[: max(topk, 1)]

# ─────────────────────────────────────────────────────────────
# Scoring con LLM (OpenAI 1.x / Azure)
# ─────────────────────────────────────────────────────────────
def _get_openai_client():
    provider = (os.getenv("OPENAI_PROVIDER") or "openai").strip().lower()
    if provider == "azure":
        from openai import AzureOpenAI
        key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        if not key or not endpoint:
            raise RuntimeError("Faltan AZURE_OPENAI_API_KEY/AZURE_OPENAI_ENDPOINT")
        return AzureOpenAI(api_key=key, api_version=version, azure_endpoint=endpoint)
    else:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Falta OPENAI_API_KEY")
        return OpenAI(api_key=key)

_LLM_SYSTEM = (
    "Eres un verificador científico. Toma un CLAIM y un posible estudio (título + resumen) "
    "y evalúa QUÉ TAN BIEN lo respalda, devolviendo solo un número entre 0.0 y 1.0.\n"
    "0.0 = no guarda relación / lo contradice; 0.5 = relación débil/indirecta; 1.0 = lo respalda claramente.\n"
    "Si el texto del estudio es insuficiente, devuelve ≤ 0.4."
)

_LLM_USER_TMPL = (
    "CLAIM:\n{claim}\n\n"
    "ESTUDIO (título + resumen):\n{title}\n{abstract}\n\n"
    "Responde solo el número (0..1), con máximo 3 decimales."
)

def _score_llm(claim: str, title: str, abstract: str, model: str) -> float:
    client = _get_openai_client()
    try:
        user = _LLM_USER_TMPL.format(claim=claim, title=title or "(sin título)", abstract=abstract or "(sin resumen)")
        resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_tokens=8,
            messages=[{"role":"system","content":_LLM_SYSTEM},{"role":"user","content": user}],
        )
        raw = (resp.choices[0].message.content or "").strip()
        m = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", raw)
        if not m:
            return 0.0
        return float(m.group(0))
    except Exception:
        return 0.0

def _score_fallback_overlap(claim: str, title: str, abstract: str) -> float:
    text = f"{title} {abstract}".lower()
    claim_l = claim.lower()
    w_doc = set(re.findall(r"[a-záéíóúñ]{6,}", text))
    w_clm = set(re.findall(r"[a-záéíóúñ]{6,}", claim_l))
    inter = len(w_doc & w_clm)
    if inter >= 10: return 0.85
    if inter >= 7:  return 0.70
    if inter >= 5:  return 0.55
    if inter >= 3:  return 0.40
    return 0.20 if inter else 0.0

# ─────────────────────────────────────────────────────────────
# Servicio principal
# ─────────────────────────────────────────────────────────────
@dataclass
class ClaimValidatorService:
    evidence: Any | None = None
    topk: int = 8
    thr_green: float = 0.82
    thr_yellow: float = 0.70
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def validate(self, claim: str) -> Dict[str, Any]:
        claim = (claim or "").strip()
        if not claim:
            return {"status": "red", "best_score": 0.0, "hits": []}

        # 1) Web search multi-fuente (generativa primero)
        hits = _web_search_all(claim, self.topk)

        # 2) Puntuación (LLM si hay clave; si no, solapamiento)
        scored: List[Dict[str, Any]] = []
        use_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"))
        for h in hits:
            title, abstract = _strip(h.get("title")), _strip(h.get("text"))
            score = _score_llm(claim, title, abstract, self.llm_model) if use_llm else _score_fallback_overlap(claim, title, abstract)
            scored.append({
                "source": h.get("source"),
                "pmid": h.get("pmid"),
                "doi": h.get("doi"),
                "url": h.get("url"),
                "title": title,
                "text": abstract,
                "year": h.get("year"),
                "score": float(round(score, 3)),
            })

        scored = _dedupe_hits(scored)
        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]["score"] if scored else 0.0
        status = _status_from_score(best, self.thr_green, self.thr_yellow)

        return {
            "status": status,
            "best_score": best,
            "hits": scored[: self.topk],
        }
