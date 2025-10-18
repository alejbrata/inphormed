from qdrant_client import QdrantClient

class QdrantService:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)

    def create_collection(self, name: str):
        print(f"📦 Creando colección en Qdrant: {name}")
        # TODO: definir esquema de vectores
