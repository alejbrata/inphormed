# app/audit/auditor.py
from __future__ import annotations

import json, os, uuid, hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    # Import opcional: solo para tipado; no romper si aún no existen
    from app.schemas import Citation, ResultadoClaim
except Exception:  # pragma: no cover
    Citation = Any  # type: ignore
    ResultadoClaim = Any  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Auditor:
    """
    Auditoría y trazabilidad en formato JSONL.
    - Escribe eventos atómicos (una línea JSON por evento).
    - Sin dependencias externas. Listo para enviar a ELK/Datadog si quieres.
    - Incluye helpers para hashes estables (doc_hash y chunk_hash).

    Convenciones:
    - timestamps: ISO-8601 en UTC
    - ids: usa siempre intake_id (archivo/subida), claim_id (línea/slide), y run_id (sesión)
    - metadatos críticos: doc_hash, chunk_hash, source, url, versionado, latencias, costes LLM
    """

    def __init__(self, path: str = "logs/audit.log", app_name: str = "inphormed"):
        self.path = path
        self.app_name = app_name
        self.run_id = str(uuid.uuid4())
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # -----------------------------
    # Hashes de trazabilidad
    # -----------------------------
    @staticmethod
    def compute_doc_hash(text: str) -> str:
        """SHA256 del documento normalizado (texto completo)."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_chunk_hash(doc_hash: str, span_start: int, span_end: int) -> str:
        """SHA256 estable para el rango del chunk dentro del documento."""
        key = f"{doc_hash}:{span_start}:{span_end}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    # -----------------------------
    # Escritura de eventos JSONL
    # -----------------------------
    def _write_jsonl(self, payload: Dict[str, Any]) -> None:
        record = {
            "ts": _now_iso(),
            "run_id": self.run_id,
            "app": self.app_name,
            **payload,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # -----------------------------
    # Eventos genéricos
    # -----------------------------
    def log_event(
        self,
        event_type: str,
        *,
        intake_id: Optional[str] = None,
        claim_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._write_jsonl(
            {
                "type": event_type,
                "intake_id": intake_id,
                "claim_id": claim_id,
                "data": data or {},
            }
        )

    # -----------------------------
    # Eventos específicos del flujo
    # -----------------------------
    def log_intake_started(self, intake_id: str, filename: str, file_kind: str, size_bytes: int) -> None:
        self.log_event(
            "IntakeStarted",
            intake_id=intake_id,
            data={"filename": filename, "kind": file_kind, "size_bytes": size_bytes},
        )

    def log_claim_extracted(self, intake_id: str, claim_id: str, raw_text: str, idx: int) -> None:
        self.log_event(
            "ClaimExtracted",
            intake_id=intake_id,
            claim_id=claim_id,
            data={"index": idx, "text": raw_text},
        )

    def log_local_retrieval(self, intake_id: str, claim_id: str, k: int, alpha: float, latency_ms: float) -> None:
        self.log_event(
            "LocalRetrieval",
            intake_id=intake_id,
            claim_id=claim_id,
            data={"top_k": k, "alpha_hybrid": alpha, "latency_ms": latency_ms},
        )

    def log_agent_winner(
        self,
        intake_id: str,
        claim_id: str,
        agent_name: str,
        ok: bool,
        latency_ms: float,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.log_event(
            "AgentWinner",
            intake_id=intake_id,
            claim_id=claim_id,
            data={"agent": agent_name, "ok": ok, "latency_ms": latency_ms, "meta": meta or {}},
        )

    def log_ingest_upsert(
        self,
        intake_id: str,
        source: str,
        doc_id: str,
        url: Optional[str],
        n_chunks: int,
        doc_hash: str,
        ingested_at: str,
        version: Optional[str] = None,
    ) -> None:
        self.log_event(
            "IngestUpsert",
            intake_id=intake_id,
            data={
                "source": source,
                "doc_id": doc_id,
                "url": url,
                "n_chunks": n_chunks,
                "doc_hash": doc_hash,
                "ingested_at": ingested_at,
                "source_version": version,
            },
        )

    def log_decision(
        self,
        intake_id: str,
        claim_id: str,
        resultado_claim: ResultadoClaim,
        citations: List[Citation],
        timings_ms: Dict[str, float],
        costs: Optional[Dict[str, float]] = None,
        model_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra la decisión final por claim (semáforo), con citas y métricas.
        - timings_ms: latencias por fase (retrieval, agents, ingest, rerank, classify, compliance, render)
        - costs: costes LLM (tokens_prompt, tokens_completion, eur_total, etc.)
        - model_info: modelos usados (embedding, reranker, llm_classifier, llm_query_rewriter)
        """
        try:
            # Pydantic → dict (si los tipos están disponibles)
            rc_dict = resultado_claim.model_dump() if hasattr(resultado_claim, "model_dump") else dict(resultado_claim)
            cits = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in citations]
        except Exception:
            rc_dict = resultado_claim  # best effort
            cits = citations

        self.log_event(
            "Decision",
            intake_id=intake_id,
            claim_id=claim_id,
            data={
                "resultado": rc_dict,
                "citations": cits,
                "timings_ms": timings_ms,
                "costs": costs or {},
                "models": model_info or {},
            },
        )
