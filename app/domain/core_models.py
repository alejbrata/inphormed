# app/domain/core_models.py
from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# ============
# Esquemas del juez LLM
# ============

class EvidenceQuote(BaseModel):
    source: Literal["pubmed", "epmc", "crossref", "other"]
    section: Optional[Literal["title", "abstract", "methods", "results", "conclusions", "fulltext", "table"]] = None
    quote: str

class MetaAlignment(BaseModel):
    title_match: float = Field(ge=0, le=1)
    author_overlap: float = Field(ge=0, le=1)
    year_match: Literal["exact", "near", "far", "unknown"]
    population_match: float = Field(ge=0, le=1)
    outcome_match: float = Field(ge=0, le=1)

class JudgeResult(BaseModel):
    verdict: Literal["supports", "refutes", "insufficient"]
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    why_short: str
    evidence_quotes: List[EvidenceQuote] = []
    meta_alignment: MetaAlignment
    best_snippet: Optional[str] = None 

# ============
# Dominio
# ============

class Claim(BaseModel):
    text: str
    id: Optional[str] = None

class SlideContext(BaseModel):
    title: str = ""
    excerpt: str = ""
    citation_string: Optional[str] = None 

class CandidateDoc(BaseModel):
    source: str
    id: str
    title: str
    authors: List[str] = []
    journal: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    
    abstract: Optional[str] = None
    full_text_content: Optional[str] = None 

    latency_ms: Optional[int] = None

    score: Optional[float] = None
    verdict: Optional[Literal["supports", "refutes", "insufficient"]] = None
    llm_judgement: Optional[JudgeResult] = None

# ============
# Salida orquestador
# ============

class RankedItem(BaseModel):
    rank: int
    source: str
    id: str
    title: str
    score: float
    verdict: Literal["supports", "refutes", "insufficient"]
    why_short: str
    url: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    best_snippet: Optional[str] = None
    
    # --- ¡ESTE ES EL CAMPO QUE FALTABA! ---
    full_text: Optional[str] = None 

class OrchestratorResult(BaseModel):
    claim_id: Optional[str] = None
    claim_text: str
    best: Optional[RankedItem] = None
    topk: List[RankedItem] = []
    canceled_early: bool = False
    thresholds: Dict[str, Any] = {}
    timings_ms: Dict[str, float] = {}