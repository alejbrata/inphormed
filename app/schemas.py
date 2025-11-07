# app/schemas.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# Índice vectorial / RAG
# ─────────────────────────────────────────────────────────────
class Chunk(BaseModel):
    """
    Fragmento indexable (Qdrant). Incluye trazabilidad mínima.
    """
    id: str
    doc_id: str
    source: str
    title: Optional[str] = None
    url: Optional[str] = None

    span_start: int
    span_end: int
    text: str

    doc_hash: Optional[str] = None
    chunk_hash: Optional[str] = None  # opcional si lo añades al payload


class SearchHit(BaseModel):
    """
    Resultado de búsqueda vectorial.
    """
    chunk: Chunk
    score: float


# ─────────────────────────────────────────────────────────────
# Ingesta / Normalización de fuentes
# ─────────────────────────────────────────────────────────────
class ResultadoFuente(BaseModel):
    """
    Salida cruda de un agente de fuente antes de normalizar.
    """
    source: str                     # "pubmed", "ctgov", "ema", ...
    id_externo: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    license: Optional[str] = None
    text: str
    metadata: Optional[Dict[str, Any]] = None
    confianza_fuente: Optional[float] = None


class UnifiedDocument(BaseModel):
    """
    Documento normalizado, listo para chunking/embeddings/indexado.
    """
    id: str
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    license: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────
# Citas, Validación y Compliance (usados por el orquestador/validator)
# ─────────────────────────────────────────────────────────────
class Citation(BaseModel):
    """
    Cita utilizada para justificar un claim.
    """
    source: Optional[str] = None         # "pubmed", "ctgov", "ema", ...
    url: Optional[str] = None
    title: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    doc_hash: Optional[str] = None
    score: Optional[float] = None        # score de retrieval (si aplica)


class ValidationResult(BaseModel):
    """
    Resultado de la validación de un claim por el LLM.
    label: semáforo (GREEN/YELLOW/RED).
    """
    label: Literal["GREEN", "YELLOW", "RED"]
    explanation: Optional[str] = None
    top_url: Optional[str] = None
    citations: List[Citation] = []       # citas usadas para la decisión


class ComplianceResult(BaseModel):
    """
    Resultado del módulo de compliance (EMA/FDA) para el texto generado/claim.
    score: 0..100 o 0..1 (elige tu escala; nosotros solemos 0..100).
    passed: booleano global (apto/no apto).
    issues: lista de incumplimientos detectados (texto o dicts).
    """
    score: Optional[float] = None
    passed: Optional[bool] = None
    issues: Optional[List[Any]] = None    # puedes tiparlo a List[str] si prefieres
