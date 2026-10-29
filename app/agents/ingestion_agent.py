class IngestionAgent:
    """
    Agente encargado de la ingesta y chunking de documentos.
    """
    def ingest_document(self, file_path: str):
        print(f"📄 Ingestando documento desde {file_path}")
        # TODO: añadir lectura y división en chunks
        return {"status": "ingested", "path": file_path}
