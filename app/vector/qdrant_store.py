# app/vector/qdrant_store.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


@dataclass
class QdrantStore:
    url: str
    api_key: Optional[str]
    collection: str
    dim: int = 384
    distance: str = "COSINE"  # COSINE | EUCLID | DOT

    def __post_init__(self) -> None:
        self.client = QdrantClient(url=self.url, api_key=self.api_key)

    # ─────────────────────────────────────────────────────────────
    # Administración de colección
    # ─────────────────────────────────────────────────────────────
    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            dist = getattr(qm.Distance, self.distance.upper(), qm.Distance.COSINE)
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.dim, distance=dist),
            )

    # ─────────────────────────────────────────────────────────────
    # Escritura
    # ─────────────────────────────────────────────────────────────
    def upsert(self, points: Sequence[qm.PointStruct]) -> None:
        self.client.upsert(collection_name=self.collection, points=points)

    # ─────────────────────────────────────────────────────────────
    # Lectura (compatible con distintas versiones de qdrant-client)
    # ─────────────────────────────────────────────────────────────
    def _query_points(
        self,
        vector: List[float],
        k: int,
        flt: Optional[qm.Filter],
        with_payload: bool,
    ):
        """
        Intenta usar query_points (API nueva). Si NearVector no existe en tu versión,
        cae a search(...) (API antigua, deprecada pero funcional).
        """
        # Intento con API nueva
        try:
            if hasattr(self.client, "query_points") and hasattr(qm, "NearVector"):
                res = self.client.query_points(
                    collection_name=self.collection,
                    query=qm.NearVector(vector=vector),
                    limit=k,
                    with_payload=with_payload,
                    query_filter=flt,
                )
                return res.points
        except Exception:
            # Fallback más abajo
            pass

        # Fallback API antigua
        return self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=k,
            with_payload=with_payload,
            query_filter=flt,
        )

    def search_vectors(
        self,
        vector: List[float],
        k: int = 5,
        with_payload: bool = True,
        query_filter: Optional[qm.Filter] = None,
    ):
        return self._query_points(vector, k, query_filter, with_payload)
