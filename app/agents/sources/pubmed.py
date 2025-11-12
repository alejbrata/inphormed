# app/agents/sources/pubmed.py
from __future__ import annotations
from typing import List, Optional
import os, re
import httpx
# --- ¡CAMBIO REALIZADO AQUÍ! ---
from app.domain.core_models import Claim, CandidateDoc, SlideContext
from .base import BaseSourceAgent

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

NCBI_API_KEY = os.getenv("NCBI_API_KEY")  # opcional

def _q_title_exact(title: str) -> str:
    t = title.replace('"', '')
    return f"\"{t}\"[Title]"

def _q_title_keywords(text: str, extra: Optional[str] = None) -> str:
    # recorta stopwords y deja tokens informativos
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-]{3,}", text)
    # --- ¡CAMBIO REALIZADO AQUÍ! ---
    # Aumentado el número de palabras para citas más largas
    core = " ".join(words[:25]) 
    q = f"({core})[Title/Abstract]"
    if extra:
        q += f" AND ({extra})"
    return q

class AgentePubMed(BaseSourceAgent):
    name = "pubmed"
    timeout_default = 8.0

    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self._session = session

    # --- ¡CAMBIO REALIZADO AQUÍ! ---
    # Firma actualizada
    async def fetch_candidates(
        self, 
        claim: Claim, 
        slide_ctx: SlideContext, 
        limit: int = 5
    ) -> List[CandidateDoc]:
        
        # --- ¡LÓGICA DE BÚSQUEDA MEJORADA! ---
        
        # 1. ¿Nos ha pasado el extractor el texto de la cita?
        # (El texto de la cita es el "slide_body_preview")
        citation_query = getattr(slide_ctx, "citation_string", None)
        extra = "hidradenitis suppurativa[Title/Abstract] OR hidradenitis supurativa[Title/Abstract]"

        if citation_query and len(citation_query) > 10:
            # ¡SÍ! Usar el texto de la cita (autores, año) como query principal.
            # Esto es mucho más preciso.
            queries = [
                _q_title_keywords(citation_query, extra=extra)
            ]
        else:
            # NO. Volver al método antiguo: usar el texto del claim
            title_guess = (claim.text or "").split("\n")[0][:220]
            queries = [
                _q_title_exact(title_guess),
                _q_title_keywords(title_guess, extra=extra),
                _q_title_keywords(claim.text, extra=extra),
            ]
        # --- FIN DE LA LÓGICA DE BÚSQUEDA ---


        pmids: List[str] = []
        async with (self._session or httpx.AsyncClient(timeout=10.0)) as client:
            for q in queries:
                ids = await self._esearch(client, q, retmax=limit)
                for pmid in ids:
                    if pmid not in pmids:
                        pmids.append(pmid)
                if len(pmids) >= limit:
                    break

            if not pmids:
                return []

            summaries = await self._esummary(client, pmids)
            abstracts = await self._efetch_abstracts(client, pmids)

        cands: List[CandidateDoc] = []
        for pmid in pmids[:limit]:
            meta = summaries.get(pmid, {})
            title = meta.get("Title") or meta.get("title") or ""
            authors = [a.get("Name") or a.get("name") for a in meta.get("Authors", []) if a]
            journal = meta.get("FullJournalName") or meta.get("Source")
            year = None
            try:
                year = int((meta.get("PubDate") or "").split()[0])
            except Exception:
                pass
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            abstract_text = abstracts.get(pmid, "")
            snippet = abstract_text[:2000]
            cands.append(CandidateDoc(
                source="pubmed",
                id=pmid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                url=url,
                abstract_snippets=snippet,
                fulltext_snippets="",
            ))
        return cands

    async def _esearch(self, client: httpx.AsyncClient, query: str, retmax: int = 10) -> List[str]:
        params = {"db": "pubmed", "retmode": "json", "sort": "bestmatch", "retmax": retmax, "term": query}
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(ESEARCH_URL, params=params)
            r.raise_for_status()
            js = r.json()
            return js.get("esearchresult", {}).get("idlist", []) or []
        except Exception:
            # No fallar ruidosamente si PubMed da error
            return []

    async def _esummary(self, client: httpx.AsyncClient, pmids: List[str]) -> dict:
        params = {"db": "pubmed", "retmode": "json", "id": ",".join(pmids)}
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(ESUMMARY_URL, params=params)
            r.raise_for_status()
            js = r.json()
            res = js.get("result", {})
            res.pop("uids", None)
            return res
        except Exception:
            return {}

    async def _efetch_abstracts(self, client: httpx.AsyncClient, pmids: List[str]) -> dict:
        params = {"db": "pubmed", "retmode": "xml", "id": ",".join(pmids)}
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(EFETCH_URL, params=params)
            r.raise_for_status()
            xml = r.text
            abstracts: dict = {}
        
            articles = re.findall(r"<PubmedArticle>(.*?)</PubmedArticle>", xml, flags=re.S)
            for art in articles:
                pmid_match = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
                pmid = pmid_match.group(1) if pmid_match else None
                if not pmid:
                    continue
                parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, flags=re.S)
                text = " ".join(re.sub(r"<[^>]+>", "", p).strip() for p in parts if p).strip()
                abstracts[pmid] = text
            return abstracts
        except Exception:
            return {}