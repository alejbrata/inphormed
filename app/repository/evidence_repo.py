from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict, Any
from qdrant_client.http import models as qm
from .types import EvidenceDoc
from app.vector.qdrant_store import QdrantStore
from app.vector.embedder import EmbedderMiniLM

@dataclass
class EvidenceRepository:
    store: QdrantStore
    embedder: EmbedderMiniLM

    def ensure_ready(self) -> None:
        self.store.ensure_collection()

    def add_documents(self, docs: Iterable[EvidenceDoc]) -> int:
        texts = [d["text"] for d in docs]
        vecs = self.embedder.encode(texts)
        points: List[qm.PointStruct] = []
        for d, v in zip(docs, vecs):
            payload = dict(d)
            payload.setdefault("kind", "evidence")
            points.append(qm.PointStruct(id=None, vector=v.tolist(), payload=payload))
        self.store.upsert(points)
        return len(points)

    def search_text(self, query: str, k: int = 5):
        qvec = self.embedder.encode([query])[0].tolist()
        return self.store.search_vectors(qvec, k=k, with_payload=True)
