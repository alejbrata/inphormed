# app/retrieval/hybrid.py
from __future__ import annotations

from typing import List, Dict, Optional
from collections import defaultdict
from time import perf_counter

from app.schemas import SearchHit, Citation
from app.indexers.vector_indexer import VectorIndexer
from app.indexers.lexical_indexer import LexicalIndexer
from app.audit.auditor import Auditor
from app.config import settings


class RecuperadorHibrido:
    """
    Recuperación híbrida (vectorial + BM25) con reescalado y fusión lineal.

    - Usa Qdrant (vectorial) y Whoosh (BM25) en paralelo.
    - Reescala scores de cada canal a [0,1] y los combina: score = α * vec + (1-α) * bm25
    - Devuelve los mejores 'top_k' hits para el claim.
    - Registra auditoría de la recuperación local (latencia, α, k).

    Trazabilidad:
    - Cada SearchHit incluye un Chunk con doc_hash.
    - Para producir citas (Citation), se calcula chunk_hash = SHA256(doc_hash:span_start:span_end).
    """

    def __init__(
        self,
        *,
        alpha: float = 0.6,
        auditor: Optional[Auditor] = None,
        qdrant_url: Optional[str] = None,
        qdrant_collection: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        whoosh_dir: Optional[str] = None,
    ) -> None:
        self.alpha = alpha
        self.auditor = auditor or Auditor()

        # Config desde settings (sobreescribible por parámetros)
        qdrant_url = qdrant_url or settings.QDRANT_URL
        qdrant_collection = qdrant_collection or settings.QDRANT_COLLECTION
        qdrant_api_key = qdrant_api_key or settings.QDRANT_API_KEY
        embedding_model = embedding_model or settings.EMBEDDING_MODEL
        whoosh_dir = whoosh_dir or settings.WHOOSH_DIR

        # Indexadores
        self.vec = VectorIndexer(
            qdrant_url=qdrant_url,
            collection=qdrant_collection,
            api_key=qdrant_api_key,
            embedding_model=embedding_model,
        )
        self.lex = LexicalIndexer(index_dir=whoosh_dir)

    # ------------------------
    # API principal
    # ------------------------
    def buscar(
        self,
        query: str,
        *,
        top_k: int = 12,
        intake_id: Optional[str] = None,
        claim_id: Optional[str] = None,
        oversample: int = 2,
    ) -> List[SearchHit]:
        """
        Devuelve hits híbridos reordenados por score combinado.
        - oversample: multiplicador para traer más de cada canal antes de fusionar.
        """
        start = perf_counter()
        k_each = max(1, top_k * oversample)

        vhits = self.vec.search(query, top_k=k_each)
        lhits = self.lex.search(query, top_k=k_each)

        # Reescalado y fusión
        pool: Dict[str, float] = defaultdict(float)
        meta: Dict[str, SearchHit] = {}

        if vhits:
            vmax = max(h.score for h in vhits) or 1.0
            for h in vhits:
                key = h.chunk.id
                pool[key] += self.alpha * (h.score / vmax)
                meta[key] = h

        if lhits:
            lmax = max(h.score for h in lhits) or 1.0
            for h in lhits:
                key = h.chunk.id
                pool[key] += (1 - self.alpha) * (h.score / lmax)
                if key not in meta:
                    meta[key] = h

        ranked = sorted(pool.items(), key=lambda x: x[1], reverse=True)[:top_k]
        hits = [meta[k] for k, _ in ranked]

        # Auditoría
        latency_ms = (perf_counter() - start) * 1000.0
        self.auditor.log_local_retrieval(
            intake_id=intake_id or "-",
            claim_id=claim_id or "-",
            k=top_k,
            alpha=self.alpha,
            latency_ms=latency_ms,
        )
        return hits

    def a_citas(self, hits: List[SearchHit], limit: int = 3) -> List[Citation]:
        """
        Convierte SearchHit -> Citation con doc_hash y chunk_hash.
        """
        citations: List[Citation] = []
        for h in hits[:limit]:
            c = h.chunk
            # chunk_hash derivado de doc_hash + [span_start, span_end]
            chunk_hash = None
            if c.doc_hash:
                chunk_hash = Auditor.compute_chunk_hash(c.doc_hash, c.span_start, c.span_end)

            citations.append(
                Citation(
                    chunk_id=c.id,
                    doc_id=c.doc_id,
                    source=c.source,
                    url=c.url,
                    title=c.title,
                    span_start=c.span_start,
                    span_end=c.span_end,
                    doc_hash=c.doc_hash,
                    chunk_hash=chunk_hash,
                )
            )
        return citations
