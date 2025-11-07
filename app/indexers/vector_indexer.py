from __future__ import annotations

from typing import List
from datetime import datetime, timezone
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from app.schemas import Chunk, SearchHit
from app.audit.auditor import Auditor
from app.config import settings


def _stable_int_id(s: str) -> int:
    """ID numérico determinista a partir de SHA256 (evita hash() de Python)."""
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16], 16)


class VectorIndexer:
    """
    Indexador vectorial (Qdrant) con trazabilidad:
    - Guarda doc_hash y chunk_hash en payload.
    - 'ingested_at' para versionado temporal.
    - Dimensión deducida del modelo de embeddings.
    """

    def __init__(
        self,
        qdrant_url: str,
        collection: str,
        api_key: str | None = None,
        embedding_model: str | None = None,
    ):
        # Modelo por defecto desde settings (multilingüe ES↔EN)
        self.model_name = embedding_model or settings.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)

        self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        self.collection = collection
        self._ensure_collection()

    def _ensure_collection(self):
        dim = self.model.get_sentence_embedding_dimension()
        try:
            # Si existe, la dejamos tal cual. Si quieres detectar mismatch de dimensión y recrear,
            # puedes añadir comprobación aquí y llamar a recreate_collection().
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def _embed(self, texts: list[str]):
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def index(self, chunks: List[Chunk]) -> int:
        """
        Inserta/actualiza chunks con trazabilidad en Qdrant.
        Devuelve el número de chunks indexados.
        """
        if not chunks:
            return 0

        vectors = self._embed([c.text for c in chunks])
        now_iso = datetime.now(timezone.utc).isoformat()

        points: List[PointStruct] = []
        for i, c in enumerate(chunks):
            # chunk_hash exige doc_hash + rango
            doc_hash = c.doc_hash or ""
            chunk_hash = Auditor.compute_chunk_hash(doc_hash, c.span_start, c.span_end) if doc_hash else None

            payload = {
                "chunk_id": c.id,
                "doc_id": c.doc_id,
                "source": c.source,
                "title": c.title,
                "url": c.url,
                "span_start": c.span_start,
                "span_end": c.span_end,
                "text": c.text,
                "doc_hash": doc_hash,
                "chunk_hash": chunk_hash,
                "ingested_at": now_iso,
                # trazabilidad adicional
                "embedding_model": self.model_name,
            }

            points.append(
                PointStruct(
                    id=_stable_int_id(c.id),
                    vector=vectors[i].tolist(),
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(self, query: str, top_k: int = 20) -> list[SearchHit]:
        qvec = self._embed([query])[0].tolist()
        res = self.client.search(collection_name=self.collection, query_vector=qvec, limit=top_k)
        hits: list[SearchHit] = []
        for r in res:
            p = r.payload
            hits.append(SearchHit(
                chunk=Chunk(
                    id=p["chunk_id"],
                    doc_id=p["doc_id"],
                    source=p["source"],
                    title=p.get("title"),
                    url=p.get("url"),
                    span_start=p["span_start"],
                    span_end=p["span_end"],
                    text=p["text"],
                    doc_hash=p.get("doc_hash"),
                ),
                score=float(r.score),
            ))
        return hits
