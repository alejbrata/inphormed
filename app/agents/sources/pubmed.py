# app/agents/sources/pubmed.py
from __future__ import annotations
from typing import List, Optional
import os
import re
import httpx
import asyncio

from app.domain.core_models import Claim, CandidateDoc, SlideContext
from app.utils.ref_extractor import extract_references
from .base import BaseSourceAgent

# Importamos los crawlers y helpers
from .pmc_crawler import PMCCrawler, _q_title_exact, _q_title_keywords
from .browser_crawler import BrowserCrawler

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

NCBI_API_KEY = os.getenv("NCBI_API_KEY")

class AgentePubMed(BaseSourceAgent):
    name = "pubmed"
    timeout_default = 120.0 # Damos margen global amplio

    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self._session = session
        self.pmc_crawler = PMCCrawler(session=session)
        self.browser_crawler = BrowserCrawler()

    async def fetch_candidates(
        self, 
        claim: Claim, 
        slide_ctx: SlideContext, 
        limit: int = 5
    ) -> List[CandidateDoc]:
        
        found_pmids: List[str] = []
        citation_query = getattr(slide_ctx, "citation_string", None)
        extra_context = "hidradenitis suppurativa[Title/Abstract] OR hidradenitis supurativa[Title/Abstract]"

        async with (self._session or httpx.AsyncClient(timeout=30.0)) as client:
            if citation_query:
                refs = extract_references(citation_query)
                pmids = refs.get("pmid", [])
                dois = refs.get("doi", [])
                if pmids: found_pmids = pmids
                elif dois: found_pmids = await self._esearch(client, dois[0], retmax=limit)

            if not found_pmids and citation_query:
                queries = [_q_title_keywords(citation_query, extra=extra_context)]
                for q in queries:
                    found_pmids = await self._esearch(client, q, retmax=limit)
                    if found_pmids: break
            
            if not found_pmids:
                title_guess = (claim.text or "").split("\n")[0][:220]
                queries = [
                    _q_title_exact(title_guess),
                    _q_title_keywords(title_guess, extra=extra_context),
                    _q_title_keywords(claim.text, extra=extra_context),
                ]
                for q in queries:
                    found_pmids = await self._esearch(client, q, retmax=limit)
                    if found_pmids: break
            
            if not found_pmids: return [] 

            summaries = await self._esummary(client, found_pmids)
            abstracts = await self._efetch_abstracts(client, found_pmids)

        cands: List[CandidateDoc] = []
        for pmid in found_pmids[:limit]:
            meta = summaries.get(pmid, {})
            title = meta.get("Title") or meta.get("title") or ""
            if not title: continue

            authors = [a.get("Name") or a.get("name") for a in meta.get("Authors", []) if a]
            journal = meta.get("FullJournalName") or meta.get("Source")
            year = None
            try: year = int((meta.get("PubDate") or "").split()[0])
            except: pass
            
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            abstract_text = abstracts.get(pmid, "")
            
            full_text = None
            pmcid = None
            doi = None
            for article_id in meta.get("ArticleIds", []):
                id_type = article_id.get("IdType")
                if id_type == "pmc":
                    pmcid = article_id.get("Value")
                elif id_type == "doi":
                    doi = article_id.get("Value")

            try:
                # 1. Intentar PMC (Rápido)
                if pmcid:
                    full_text = await self.pmc_crawler.fetch_full_text(pmcid)
                
                # 2. Si falla, Crawler Browser (Lento)
                if not full_text and doi:
                    target_url = f"https://doi.org/{doi}"
                    
                    print(f"[DEBUG] Lanzando Crawler para {target_url} (Timeout: 90s)...")
                    
                    # --- ¡CAMBIO CRÍTICO! Subimos a 90 segundos ---
                    full_text = await asyncio.wait_for(
                        self.browser_crawler.fetch_full_text(target_url),
                        timeout=90.0 
                    )
                    # ----------------------------------------------

            except Exception as e:
                print(f"AgentePubMed: Error/Timeout recuperando full-text para {pmid}: {e}")

            cands.append(CandidateDoc(
                source="pubmed",
                id=pmid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                url=url,
                abstract=abstract_text,
                full_text_content=full_text, 
            ))
            
        return cands

    async def _esearch(self, client, query, retmax=10):
        params = {"db": "pubmed", "retmode": "json", "sort": "bestmatch", "retmax": retmax, "term": query}
        if NCBI_API_KEY: params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(ESEARCH_URL, params=params)
            r.raise_for_status()
            js = r.json()
            return js.get("esearchresult", {}).get("idlist", []) or []
        except Exception: return []

    async def _esummary(self, client, pmids):
        if not pmids: return {}
        params = {"db": "pubmed", "retmode": "json", "id": ",".join(pmids)}
        if NCBI_API_KEY: params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(ESUMMARY_URL, params=params)
            r.raise_for_status()
            js = r.json()
            res = js.get("result", {})
            res.pop("uids", None)
            return res
        except Exception: return {}

    async def _efetch_abstracts(self, client, pmids):
        if not pmids: return {}
        params = {"db": "pubmed", "retmode": "xml", "id": ",".join(pmids)}
        if NCBI_API_KEY: params["api_key"] = NCBI_API_KEY
        try:
            r = await client.get(EFETCH_URL, params=params)
            r.raise_for_status()
            xml = r.text
            abstracts: dict = {}
            articles = re.findall(r"<PubmedArticle>(.*?)</PubmedArticle>", xml, flags=re.S)
            for art in articles:
                pmid_match = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
                pmid = pmid_match.group(1) if pmid_match else None
                if not pmid: continue
                parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, flags=re.S)
                text = " ".join(re.sub(r"<[^>]+>", "", p).strip() for p in parts if p).strip()
                abstracts[pmid] = text
            return abstracts
        except Exception: return {}