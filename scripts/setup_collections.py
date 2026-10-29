import os
from dotenv import load_dotenv
from app.vector.qdrant_store import QdrantStore

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, ".env"))

URL  = os.getenv("QDRANT_URL")
KEY  = os.getenv("QDRANT_API_KEY")
DIM  = int(os.getenv("EMBED_DIM", "384"))

EVID = os.getenv("QDRANT_EVIDENCE_COLLECTION", "biomed_evidence_v1")
CLMS = os.getenv("QDRANT_CLAIMS_COLLECTION", "biomed_claims_v1")

def ensure(name: str):
    store = QdrantStore(url=URL, api_key=KEY, collection=name, dim=DIM)
    store.ensure_collection()
    print(f"✅ Colección lista: {name}")

if __name__ == "__main__":
    ensure(EVID)
    ensure(CLMS)
