# scripts/qdrant_setup.py
import os
from uuid import uuid4
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


# ENV
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION = os.getenv("QDRANT_COLLECTION", "biomed_evidence_v1")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

assert QDRANT_URL, "Falta QDRANT_URL en .env"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Crear colección si no existe (sin métodos deprecados)
if not client.collection_exists(collection_name=COLLECTION):
    print(f"➕ Creando colección '{COLLECTION}' (dim={EMBED_DIM}, metric=Cosine)")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
    )
else:
    print(f"✅ Colección '{COLLECTION}' ya existe")

# Puntos dummy con IDs UUID válidos
vecA = [1.0] + [0.0] * (EMBED_DIM - 1)
vecB = [0.0] * (EMBED_DIM - 1) + [1.0]

points = [
    qm.PointStruct(
        id=str(uuid4()),
        vector=vecA,
        payload={
            "doc_id": "test:doc1",
            "text": "Este es un chunk de prueba relacionado con hidradenitis.",
            "source": "test",
            "year": 2025,
            "section": "abstract",
        },
    ),
    qm.PointStruct(
        id=str(uuid4()),
        vector=vecB,
        payload={
            "doc_id": "test:doc2",
            "text": "Otro chunk de prueba que no se parece al anterior.",
            "source": "test",
            "year": 2024,
            "section": "results",
        },
    ),
]

client.upsert(collection_name=COLLECTION, points=points)
print("✅ Upsert de puntos dummy")

#consulta de prueba sin filtros
hits = client.query_points(
    collection_name=COLLECTION,
    query=vecA,
    limit=2,
    with_payload=True
)
for h in hits.points:
    print(f" - id={h.id} | score={h.score:.3f} | doc_id={h.payload.get('doc_id')} | text='{h.payload.get('text')}'")
