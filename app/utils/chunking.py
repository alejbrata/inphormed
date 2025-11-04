# app/utils/chunking.py
from __future__ import annotations
from typing import List
from app.schemas import UnifiedDocument, Chunk

def chunkear(
    doc: UnifiedDocument,
    target_tokens: int = 400,   # 300–600 tokens recomendado
    overlap: int = 60           # 10–20% de solape
) -> List[Chunk]:
    """
    Split por 'tokens aproximados' usando palabras como proxy (simple y rápido).
    Más adelante podemos pasar a un tokenizer real (p.ej. tiktoken) sin romper la interfaz.

    Reglas clave:
    - Cada chunk arrastra doc_hash desde doc.metadata (para chunk_hash).
    - span_* son índices de palabra (estables para hashing y citación mínima viable).
    """
    words = doc.text.split()
    chunks: List[Chunk] = []
    i = 0
    cid = 0
    doc_hash = (doc.metadata or {}).get("doc_hash")

    while i < len(words):
        start = max(0, i - overlap if cid > 0 else i)
        end = min(len(words), i + target_tokens)
        span_words = words[start:end]
        text = " ".join(span_words)

        chunks.append(Chunk(
            id=f"{doc.id}::chunk::{cid}",
            doc_id=doc.id,
            source=doc.source,
            title=doc.title,
            url=doc.url,
            span_start=start,
            span_end=end,
            text=text,
            doc_hash=doc_hash,
        ))
        cid += 1
        i += target_tokens

    return chunks
