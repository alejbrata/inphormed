# app/pipeline/ingest.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.schemas import ResultadoFuente, UnifiedDocument, Chunk
from app.normalization.normalizer import NormalizadorDocumento
from app.utils.chunking import chunkear
from app.indexers.vector_indexer import VectorIndexer
from app.indexers.lexical_indexer import LexicalIndexer
from app.audit.auditor import Auditor
from app.config import settings


class PipelineIngesta:
    """
    Pipeline de ingesta canónica:
      1) Normaliza (ResultadoFuente -> UnifiedDocument)
      2) Chunking (300–600 tokens aprox, con solape)
      3) Indexa en:
         - Qdrant (vectorial) con doc_hash + chunk_hash + ingested_at
         - Whoosh (BM25) con doc_hash + chunk_hash + ingested_at
      4) Auditoría: registra el upsert con hashes/versionado

    Notas:
    - No hace retrieval ni semáforo aquí. Solo prepara el corpus para RAG.
    - Idempotente a nivel lógico: si llega el mismo doc, el ID estable y
      los indexadores con update_document (Whoosh) y upsert (Qdrant) evitan
      duplicados prácticos.
    """

    def __init__(
        self,
        *,
        auditor: Optional[Auditor] = None,
        qdrant_url: Optional[str] = None,
        qdrant_collection: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        whoosh_dir: Optional[str] = None,
    ) -> None:
        self.auditor = auditor or Auditor()
        self.normalizador = NormalizadorDocumento()

        # Config por defecto desde settings; se puede inyectar por parámetro
        qdrant_url = qdrant_url or settings.QDRANT_URL
        qdrant_collection = qdrant_collection or settings.QDRANT_COLLECTION
        qdrant_api_key = qdrant_api_key or settings.QDRANT_API_KEY
        embedding_model = embedding_model or settings.EMBEDDING_MODEL
        whoosh_dir = whoosh_dir or settings.WHOOSH_DIR

        # Indexadores híbridos
        self.vec = VectorIndexer(
            qdrant_url=qdrant_url,
            collection=qdrant_collection,
            api_key=qdrant_api_key,
            embedding_model=embedding_model,
        )
        self.lex = LexicalIndexer(index_dir=whoosh_dir)

    # -------- API principal --------

    def ingerir_resultado(
        self,
        r: ResultadoFuente,
        *,
        intake_id: Optional[str] = None,
        target_tokens: int = 400,
        overlap: int = 60,
    ) -> Dict[str, Any]:
        """
        Ingiere un ResultadoFuente completo (normaliza, trocea e indexa).
        Devuelve metadatos útiles para logging y pasos siguientes.

        Args:
            r: ResultadoFuente devuelto por un AgenteFuente
            intake_id: id del proceso de carga (para auditoría)
            target_tokens: tamaño deseado de chunk (aprox por palabras)
            overlap: solape entre chunks (palabras)

        Returns:
            dict con:
              - doc_id
              - url
              - n_chunks
              - doc_hash
              - source
              - source_version
              - ingested_at
        """
        # 1) Normalización
        doc: UnifiedDocument = self.normalizador.normalizar(r)

        # 2) Chunking
        chunks: List[Chunk] = chunkear(doc, target_tokens=target_tokens, overlap=overlap)

        if not chunks:
            # Aún así registramos un evento de ingesta nula para traza
            ingested_at = datetime.now(timezone.utc).isoformat()
            self.auditor.log_ingest_upsert(
                intake_id=intake_id or "-",
                source=doc.source,
                doc_id=doc.id,
                url=doc.url,
                n_chunks=0,
                doc_hash=(doc.metadata or {}).get("doc_hash", ""),
                ingested_at=ingested_at,
                version=(doc.metadata or {}).get("source_version"),
            )
            return {
                "doc_id": doc.id,
                "url": doc.url,
                "n_chunks": 0,
                "doc_hash": (doc.metadata or {}).get("doc_hash", ""),
                "source": doc.source,
                "source_version": (doc.metadata or {}).get("source_version"),
                "ingested_at": ingested_at,
            }

        # 3) Indexado híbrido (vectorial + BM25)
        n_vec = self.vec.index(chunks)
        n_lex = self.lex.index(chunks)
        n_chunks = max(n_vec, n_lex)  # referencia

        # 4) Auditoría
        ingested_at = datetime.now(timezone.utc).isoformat()
        self.auditor.log_ingest_upsert(
            intake_id=intake_id or "-",
            source=doc.source,
            doc_id=doc.id,
            url=doc.url,
            n_chunks=n_chunks,
            doc_hash=(doc.metadata or {}).get("doc_hash", ""),
            ingested_at=ingested_at,
            version=(doc.metadata or {}).get("source_version"),
        )

        return {
            "doc_id": doc.id,
            "url": doc.url,
            "n_chunks": n_chunks,
            "doc_hash": (doc.metadata or {}).get("doc_hash", ""),
            "source": doc.source,
            "source_version": (doc.metadata or {}).get("source_version"),
            "ingested_at": ingested_at,
        }
