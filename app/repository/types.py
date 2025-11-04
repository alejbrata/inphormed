from __future__ import annotations
from typing import TypedDict, NotRequired

__all__ = ["EvidenceDoc", "ClaimRec"]

class EvidenceDoc(TypedDict):
    # Requerido
    text: str
    # Opcionales (metadatos de cita)
    title: NotRequired[str]
    journal: NotRequired[str]
    year: NotRequired[int]
    pmid: NotRequired[str]
    doi: NotRequired[str]
    landing_url: NotRequired[str]
    section: NotRequired[str]
    source: NotRequired[str]

class ClaimRec(TypedDict):
    # Requeridos para traza
    text: str
    file_name: str
    where: str            # slide:7 / paragraph:12...
    doc_id: str           # hash del archivo
    claim_id: str         # hash del claim
    source: str           # "pptx"/"docx"/"txt"
