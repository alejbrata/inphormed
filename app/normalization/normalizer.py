from __future__ import annotations

import re
from datetime import datetime, timezone
import hashlib
from typing import Optional, Dict, Any

from app.schemas import ResultadoFuente, UnifiedDocument
from app.audit.auditor import Auditor


# --- Detección de idioma (sin dependencias; usa heurística y, si está, langid) ---
try:
    import langid  # type: ignore

    def _detect_lang(text: str) -> str:
        return langid.classify(text or "")[0]
except Exception:
    def _detect_lang(text: str) -> str:
        t = f" { (text or '').lower() } "
        es_hits = sum(kw in t for kw in [" el ", " la ", " los ", " las ", " que ", " con ", " por ", " una ", " más ", " según "])
        en_hits = sum(kw in t for kw in [" the ", " of ", " and ", " with ", " in ", " to ", " for ", " as ", " is "])
        if es_hits > en_hits:
            return "es"
        if en_hits > es_hits:
            return "en"
        return "en"  # por defecto


# --- Utilidades de normalización ---

def _stable_id(source: str, id_externo: str | None, title: str | None) -> str:
    """
    ID estable del documento normalizado:
    - Prioriza identificadores fuertes (source + id_externo).
    - Incluye el título para reducir colisiones cuando id_externo no sea único.
    (Se mantiene tu estrategia para no romper nada aguas abajo.)
    """
    key = f"{source}:{id_externo or ''}:{(title or '').strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _clean_text(text: str) -> str:
    """
    Normaliza texto para hashing y chunking (se conserva tu criterio):
    - Conserva saltos de línea (útiles para split por bullets/encabezados).
    - Colapsa espacios múltiples dentro de la línea.
    - Normaliza saltos CRLF→LF y recorta por línea.
    """
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t\f\v]+", " ", t)  # colapsa espacios dentro de línea
    t = "\n".join(line.strip() for line in t.split("\n"))
    return t.strip()


def _sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Sanea URL para trazabilidad:
    - Quita espacios raros y separadores alrededor de '/'.
    - Elimina puntuación final accidental (.,;).
    """
    if not url:
        return None
    u = re.sub(r"\s+", " ", url).strip()
    u = re.sub(r"\s*/\s*", "/", u)
    u = u.rstrip(".,; ")
    return u or None


def _extract_source_version(meta: Dict[str, Any]) -> Optional[str]:
    """
    Intenta derivar una 'versión' de la fuente (si la hay) para trazabilidad.
    Heurísticas: version, etag, last_updated, updated, pubdate, revision.
    (Se mantiene tu enfoque flexible.)
    """
    for k in ("version", "etag", "last_updated", "updated", "pubdate", "revision"):
        v = meta.get(k)
        if v:
            return str(v)
    return None


class NormalizadorDocumento:
    """
    Convierte ResultadoFuente → UnifiedDocument listo para chunking + embeddings + indexado.
    Cambios mínimos sobre tu versión:
      - Añade `lang` (multi-idioma ES/EN) a metadata.
      - Sanea URL y añade `url_hash` a metadata.
      - Mantiene tu estrategia de ID estable y de doc_hash (Auditor).
    Es puro y determinista; no escribe en índices ni BD.
    """

    def normalizar(self, r: ResultadoFuente) -> UnifiedDocument:
        title = (r.title or "").strip() or None
        text_norm = _clean_text(r.text or "")
        if not text_norm:
            raise ValueError("ResultadoFuente.text está vacío tras normalización")

        # Hash canónico del texto normalizado (se mantiene tu uso de Auditor)
        doc_hash = Auditor.compute_doc_hash(text_norm)

        # Versión expuesta por la fuente (si existe)
        source_version = _extract_source_version(r.metadata or {})

        # ID estable (compatible con tu deduplicación actual)
        uid = _stable_id(r.source, r.id_externo, title)

        # URL saneada + hash corto (para trazabilidad y UI)
        url_norm = _sanitize_url(r.url)
        url_hash = hashlib.sha256((url_norm or "").encode("utf-8")).hexdigest()[:16] if url_norm else None

        # Detección de idioma (útil para métricas, UI y estrategias ES↔EN)
        lang = _detect_lang(text_norm)

        # Metadatos ampliados (se conservan los existentes)
        meta = dict(r.metadata or {})
        meta.update({
            "source_id": r.id_externo,       # PMID/NCT/DOI/URL-id
            "source_name": r.source,         # "pubmed", "ctgov", "ema", ...
            "doc_hash": doc_hash,            # para citas y chunk_hash
            "source_version": source_version,
            "normalized_at": datetime.now(timezone.utc).isoformat(),
            "lang": lang,                    # <<< NUEVO multi-idioma
            "url_hash": url_hash,            # <<< NUEVO trazabilidad URL
        })

        return UnifiedDocument(
            id=uid,
            source=r.source,
            title=title,
            url=url_norm,
            published_at=r.published_at,
            license=r.license,
            text=text_norm,
            metadata=meta,
        )

    @staticmethod
    def dedup_key(r: ResultadoFuente) -> str:
        """
        Clave de deduplicación a nivel de fuente (se mantiene tu lógica):
        - Si hay id_externo: (source, id_externo)
        - Fallback: (source, doc_hash_del_texto_normalizado)
        """
        if r.id_externo:
            base = f"{r.source}:{r.id_externo}"
        else:
            base = f"{r.source}:{Auditor.compute_doc_hash(_clean_text(r.text or ''))}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
