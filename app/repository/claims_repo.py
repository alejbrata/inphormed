from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List
from uuid import uuid4

from qdrant_client.http import models as qm
from app.repository.types import ClaimRec
from app.vector.qdrant_store import QdrantStore
from app.vector.embedder import EmbedderMiniLM

@dataclass
class ClaimsRepository:
    store: QdrantStore
    embedder: EmbedderMiniLM

    def ensure_ready(self) -> None:
        self.store.ensure_collection()

    def add_claims(self, claims: Iterable[ClaimRec]) -> int:
        claims_list = list(claims)
        if not claims_list:
            return 0
        texts = [c["text"] for c in claims_list]
        vecs = self.embedder.encode(texts)

        points: List[qm.PointStruct] = []
        for c, v in zip(claims_list, vecs):
            payload = dict(c)
            payload.setdefault("kind", "claim")
            points.append(
                qm.PointStruct(
                    id=str(uuid4()),
                    vector=v.tolist(),
                    payload=payload,
                )
            )
        self.store.upsert(points)
        return len(points)
