# app/ingest/chunker.py
from __future__ import annotations
from typing import List
import re

from app.schemas import UnifiedDocument, Chunk

_WS = re.compile(r"\s+", flags=re.UNICODE)

def _clamp_boundary(text: str, start: int, end: int) -> tuple[int, int]:
    """
    Intenta ajustar el corte a límites “amables” (espacios / saltos de línea),
    sin salirse del rango.
    """
    n = len(text)
    if start <= 0:
        start = 0
    if end >= n:
        end = n

    # Ajusta el inicio hacia la izquierda hasta un espacio/salto si no empieza en uno
    if start > 0 and not text[start - 1].isspace():
        s = text.rfind(" ", 0, start)
        if s != -1:
            start = s + 1

    # Ajusta el final hacia la derecha hasta un espacio/salto si no acaba en uno
    if end < n and not text[end:end + 1].isspace():
        e = text.find(" ", end, min(n, end + 200))
        if e != -1:
            end = e
    return start, end


class Chunker:
    """
    Creador de chunks para indexación (aprox 300–800 tokens).
    Usamos ventana por caracteres: ~1800 chars con solape 300 (≈ 450 tokens).
    No requiere dependencias externas.

    - Respeta límites de palabra cuando se puede.
    - Devuelve app.schemas.Chunk con span_start/span_end y doc_hash.
    """

    def __init__(self, max_chars: int = 1800, overlap: int = 300):
        assert max_chars > 0 and overlap >= 0 and overlap < max_chars
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk(self, doc: UnifiedDocument) -> List[Chunk]:
        text = (doc.text or "").strip()
        if not text:
            return []

        chunks: List[Chunk] = []
        n = len(text)
        step = self.max_chars - self.overlap

        start = 0
        while start < n:
            end = min(start + self.max_chars, n)
            s, e = _clamp_boundary(text, start, end)
            if s >= e:  # safety
                s, e = start, end

            frag = text[s:e].strip()
            if frag:
                # ID estable por doc + rango
                chunk_id = f"{doc.id}::{s}:{e}"
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        doc_id=doc.id,
                        source=doc.source,
                        title=doc.title,
                        url=doc.url,
                        span_start=s,
                        span_end=e,
                        text=frag,
                        doc_hash=(doc.metadata or {}).get("doc_hash"),
                    )
                )

            if end >= n:
                break
            start = start + step

        return chunks
