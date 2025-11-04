# app/normalization/normalizer.py
from __future__ import annotations

import re
from datetime import datetime, timezone
import hashlib
from typing import Optional, Dict, Any

from app.schemas import ResultadoFuente, UnifiedDocument
from app.audit.auditor import Auditor


def _stable_id(source: str, id_externo: str | None, title: str | None) -> str:
    """
    ID estable del documento normalizado:
    - Prioriza identificadores fuertes (source + id_externo).
    - Incluye el título para reducir colisiones cuando id_externo no sea único.
    """
    key = f"{source}:{id_externo or ''}:{(title or '').strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _clean_text(text: str) -> str:
    """
    Normaliza texto para hashing y chunking:
    - Colapsa espacios repetidos.
    - Conserva saltos de línea (útiles para split por bullets/encabezados).
    - Recorta BOM/espacios extremos.
    """
    if not text:
        return ""
    # Normaliza CRLF → LF
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # Colapsa espacios múltiples pero respeta saltos de línea
    t = re.sub(r"[ \t\f\v]+", " ", t)
    # Recorta espacios por línea
    t = "\n".join(line.strip() for line in t.split("\n"))
    return t.strip()


def _extract_source_version(meta: Dict[str, Any]) -> Optional[str]:
    """
    Intenta derivar una 'versión' de la fuente (si la hay) para trazabilidad.
    Heurísticas:
    - meta["version"], meta["etag"], meta["last_updated"], meta["updated"], meta["pubdate"]
    - En PubMed/CT.gov/EMA puede venir en varios campos; mantenemos flexible.
    """
    for k in ("version", "etag", "last_updated", "updated", "pubdate", "revision"):
        v = meta.get(k)
        if v:
            return str(v)
    return None


class NormalizadorDocumento:
    """
    Convierte la salida cruda de un AgenteFuente (ResultadoFuente) en un
    UnifiedDocument listo para chunking + embeddings + indexado.
    - Calcula doc_hash (SHA256 del texto normalizado).
    - Añade metadatos de trazabilidad (doc_hash, source_version, source_id).
    - Define un id estable (source + id_externo + title).
    - No escribe en índices ni BD; es puro y determinista.
    """

    def normalizar(self, r: ResultadoFuente) -> UnifiedDocument:
        title = (r.title or "").strip() or None
        text_norm = _clean_text(r.text or "")
        doc_hash = Auditor.compute_doc_hash(text_norm)  # SHA256 del texto normalizado
        source_version = _extract_source_version(r.metadata or {})

        # ID estable (para documentos “iguales” desde la misma fuente)
        uid = _stable_id(r.source, r.id_externo, title)

        # Metadatos ampliados para trazabilidad y compliance
        meta = dict(r.metadata or {})
        meta.update({
            "source_id": r.id_externo,              # PMID/NCT/DOI/URL-id
            "source_name": r.source,                # "pubmed", "ctgov", "ema", ...
            "doc_hash": doc_hash,                   # para citas y chunk_hash
            "source_version": source_version,       # si la fuente lo expone
            "normalized_at": datetime.now(timezone.utc).isoformat(),
        })

        return UnifiedDocument(
            id=uid,
            source=r.source,
            title=title,
            url=r.url,
            published_at=r.published_at,
            license=r.license,
            text=text_norm,
            metadata=meta,
        )

    @staticmethod
    def dedup_key(r: ResultadoFuente) -> str:
        """
        Clave de deduplicación a nivel de fuente. Úsala antes de indexar para
        evitar re-ingestar el mismo documento.
        - Si hay id_externo: (source, id_externo)
        - Fallback: (source, doc_hash_del_texto)
        """
        if r.id_externo:
            base = f"{r.source}:{r.id_externo}"
        else:
            # Fallback por hash de texto crudo (limpiado)
            base = f"{r.source}:{Auditor.compute_doc_hash(_clean_text(r.text or ''))}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
