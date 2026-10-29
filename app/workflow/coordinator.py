# app/workflow/coordinator.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import traceback

from app.schemas import Citation, ValidationResult, ComplianceResult, SearchHit
from app.indexers.vector_indexer import VectorIndexer
from app.utils.query_rewriter import QueryRewriter
from app.agents.claims.validator import ClaimsValidator
from app.normalization.normalizer import NormalizadorDocumento
from app.ingest.chunker import Chunker

class WorkflowCoordinator:
    def __init__(
        self,
        *,
        query_rewriter: QueryRewriter,
        validator: ClaimsValidator,
        indexer: VectorIndexer,
        auditor: Any = None,
        citations_limit: int = 3,
        min_hits: int = 1,
    ) -> None:
        self.query_rewriter = query_rewriter
        self.validator = validator
        self.indexer = indexer
        self.auditor = auditor
        self.citations_limit = int(citations_limit)
        self.min_hits = int(min_hits)
        self._normalizador = NormalizadorDocumento()
        self._chunker = Chunker()

    def _audit(self, event: str, intake_id: str, claim_id: str, payload: Dict[str, Any]) -> None:
        if not self.auditor:
            return
        data = {"event": event, "intake_id": intake_id, "claim_id": claim_id, **(payload or {})}
        try:
            if hasattr(self.auditor, "log_event"):
                try:
                    self.auditor.log_event(event, data); return
                except TypeError:
                    self.auditor.log_event(data); return
            for m in ("log", "write", "emit", "record"):
                if hasattr(self.auditor, m):
                    try: getattr(self.auditor, m)(event, data); return
                    except TypeError: getattr(self.auditor, m)(data); return
        except Exception:
            pass

    @staticmethod
    def _hits_to_citations(hits: List[SearchHit], limit: int) -> List[Citation]:
        out: List[Citation] = []
        for h in hits[: max(0, limit)]:
            c = h.chunk
            out.append(
                Citation(
                    source=c.source,
                    url=c.url,
                    title=c.title,
                    span_start=c.span_start,
                    span_end=c.span_end,
                    doc_hash=c.doc_hash,
                    score=h.score,
                    # ← si vienen en payload del indexer, puedes añadir pmid/doi aquí
                )
            )
        return out

    def _call_agent_flex(self, agent: Any, *, claim: str, query: str, top_k: int = 8) -> List[Any]:
        for name in ("buscar", "search", "fetch", "run"):
            if hasattr(agent, name):
                fn = getattr(agent, name)
                try:
                    return fn(claim=claim, query=query, top_k=top_k)
                except TypeError:
                    try:
                        return fn(query)
                    except TypeError:
                        try:
                            return fn(claim, query)
                        except Exception:
                            pass
        return []

    def resolver_claim(
        self,
        *,
        claim: str,
        intake_id: str,
        claim_id: str,
        agentes_fuente: List[Any],
        generated_text: Optional[str],
        meta: Dict[str, Any],
        require_llm: bool = True,
        top_k: int = 8,
    ) -> Dict[str, Any]:
        q0 = (claim or "").strip()
        self._audit("StartClaim", intake_id, claim_id, {"claim": q0})

        # 1) Reescritura
        q_rw = self.query_rewriter.rewrite(q0, require_llm=require_llm)
        self._audit("QueryRewriterLLM", intake_id, claim_id, {"orig": q0, "rewritten": q_rw})

        # 2) Primer RAG
        hits = self.indexer.search(q_rw, top_k=top_k) if q_rw else []
        self._audit("VectorSearch", intake_id, claim_id, {"hits": len(hits)})

        # 3) Agentes solo si no alcanzamos min_hits
        if len(hits) < self.min_hits:
            for ag in (agentes_fuente or []):
                try:
                    raw_results = self._call_agent_flex(ag, claim=q0, query=q_rw, top_k=top_k)
                except Exception as e:
                    self._audit("AgentError", intake_id, claim_id, {"agent": ag.__class__.__name__, "error": str(e)})
                    continue

                ingested = 0
                for r in (raw_results or []):
                    try:
                        udoc = self._normalizador.normalizar(r)
                        chunks = self._chunker.chunk(udoc)
                        if chunks:
                            ingested += self.indexer.index(chunks)
                    except Exception as e:
                        self._audit("IngestError", intake_id, claim_id, {
                            "agent": ag.__class__.__name__,
                            "error": str(e),
                            "trace": traceback.format_exc()[:1200],
                        })

                if ingested:
                    # Reintenta RAG tras este agente y corta si ya es suficiente
                    hits = self.indexer.search(q_rw, top_k=top_k) if q_rw else []
                    self._audit("VectorSearchRetry", intake_id, claim_id, {"hits": len(hits), "after_agent": ag.__class__.__name__})
                    if len(hits) >= self.min_hits:
                        break

        citations = self._hits_to_citations(hits, self.citations_limit)

        thr_meta = {}
        if isinstance(meta, dict):
            for k in ("thr_green", "thr_yellow"):
                if k in meta: thr_meta[k] = meta[k]

        vres: ValidationResult = self.validator.validate(
            claim=q0,
            citations=citations,
            generated_text=(generated_text or q0),
            require_llm=require_llm,
            metadata=thr_meta,
        )
        self._audit("Validated", intake_id, claim_id, {"label": vres.label})

        cres: ComplianceResult = self.validator.compliance_for((generated_text or q0), citations)
        self._audit("Compliance", intake_id, claim_id, {"score": cres.score, "passed": cres.passed})

        return {
            "resultado": vres,
            "compliance": cres,
            "models": {
                "rewriter_model": self.query_rewriter.model_used(),
                "validator_model": self.validator.model_used(),
            },
        }
