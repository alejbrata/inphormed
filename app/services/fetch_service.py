import requests
from typing import Optional, Dict

PUBMED_SUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CROSSREF_WORKS = "https://api.crossref.org/works/"

def fetch_pubmed_text(pmid: str) -> Optional[str]:
    # efetch: abstract
    params = {"db":"pubmed","id":pmid,"retmode":"text","rettype":"abstract"}
    r = requests.get(PUBMED_FETCH, params=params, timeout=15)
    if r.ok and r.text.strip():
        return r.text
    return None

def fetch_crossref_by_doi(doi: str) -> Optional[Dict]:
    r = requests.get(CROSSREF_WORKS + doi, timeout=15)
    if not r.ok: return None
    data = r.json().get("message", {})
    # concatenamos título + abstract si hubiese
    title = " ".join(data.get("title") or [])
    abstr = data.get("abstract") or ""
    return {"title": title, "abstract": abstr}

def fetch_text_for_ref(ref: Dict) -> Optional[str]:
    t = ref["type"]; idv = ref["id"]
    if t == "pmid":
        return fetch_pubmed_text(idv)
    if t == "doi":
        cr = fetch_crossref_by_doi(idv)
        if not cr: return None
        return (cr.get("title","") + "\n" + (cr.get("abstract") or "")).strip()
    # autor-año → intentamos Crossref search (simple)
    if t == "author-year":
        # Muy simple: intentar resolver si contiene año
        r = requests.get("https://api.crossref.org/works",
                         params={"query": idv, "rows": 1}, timeout=15)
        if r.ok:
            items = r.json().get("message", {}).get("items", [])
            if items:
                it = items[0]
                title = it.get("title",[ ""])[0]
                abstr = it.get("abstract") or ""
                return (title + "\n" + abstr).strip()
    return None
