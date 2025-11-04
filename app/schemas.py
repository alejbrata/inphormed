# app/schemas.py
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ---------- Etiquetas de decisión (semáforo) ----------
Label = Literal["GREEN", "AMBER", "RED"]


# ---------- Salida cruda de un agente de fuente ----------
class ResultadoFuente(BaseModel):
    source: str                             # ej. "pubmed", "ctgov", "ema"
    id_externo: str                         # ej. PMID, NCT, DOI, URL-id
    title: Optional[str] = None
    url: Optional[str] = None               # enlace público a la fuente
    published_at: Optional[str] = None      # fecha como la ofrece la fuente
    license: Optional[str] = None           # si aplica (open, CC, etc.)
    text: str                               # abstract/pasaje/fragmento útil
    metadata: dict = Field(default_factory=dict)  # autores, journal, etc.
    confianza_fuente: float = 0.5           # heurística simple del agente


# ---------- Documento canónico (tras normalización) ----------
class UnifiedDocument(BaseModel):
    id: str
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    license: Optional[str] = None
    text: str
    metadata: dict = Field(default_factory=dict)  # contiene doc_hash, source_version, etc.


# ---------- Chunk indexable (unidad de recuperación) ----------
class Chunk(BaseModel):
    """
    Fragmento indexable con posición y trazabilidad.
    doc_hash: SHA256 del texto normalizado del documento (para chunk_hash).
    """
    id: str                 # ej. "{doc_id}::chunk::{n}"
    doc_id: str
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    span_start: int
    span_end: int
    text: str
    doc_hash: Optional[str] = None          # <- para trazabilidad


# ---------- Resultado de recuperación (RAG) ----------
class SearchHit(BaseModel):
    chunk: Chunk
    score: float


# ---------- Cita / trazabilidad de pasaje ----------
class Citation(BaseModel):
    """
    Cita estructurada para enlazar un pasaje concreto en el PPT/JSON de salida.
    Incluye hashes para auditoría en farma.
    """
    chunk_id: str
    doc_id: str
    source: str
    url: Optional[str] = None
    title: Optional[str] = None
    span_start: int
    span_end: int
    doc_hash: Optional[str] = None
    chunk_hash: Optional[str] = None


# ---------- Resultado final por claim ----------
class ResultadoClaim(BaseModel):
    claim: str
    label: Label
    top_url: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)   # p.ej. umbrales, modelo LLM, tiempos


# ---------- Compliance ----------
Severity = Literal["critical", "major", "minor", "info"]

class ComplianceIssue(BaseModel):
    """
    Incidencia de cumplimiento para un claim/material.
    """
    rule_id: str
    title: str
    severity: Severity
    passed: bool
    message: str
    suggestion: Optional[str] = None

class ComplianceReport(BaseModel):
    """
    Informe de compliance para un claim/material.
    - score: 0..100. Penalizaciones por severidad.
    - passed: True si no hay fallos critical/major (o umbral definido).
    """
    standard: Literal["EMA", "FDA", "ALL"]
    issues: List[ComplianceIssue] = Field(default_factory=list)
    score: int = 100
    passed: bool = True
    notes: Optional[str] = None
