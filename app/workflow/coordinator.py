# app/workflow/coordinator.py
from __future__ import annotations

from typing import List, Optional, Dict, Any
from time import perf_counter

from app.audit.auditor import Auditor
from app.retrieval.hybrid import RecuperadorHibrido
from app.orchestrator.orchestrator import Orquestador
from app.pipeline.ingest import PipelineIngesta
from app.schemas import ResultadoClaim, Citation
from app.compliance.engine import ComplianceEngine, ComplianceReport

# Opcionales (si no están aún, degradamos a stub dentro de esta clase)
try:
    from app.retrieval.reranker import Reranker  # cross-encoder (opcional)
except Exception:  # pragma: no cover
    Reranker = None  # type: ignore

try:
    from app.utils.query_rewriter import QueryRewriter  # LLM para rewriting (opcional)
except Exception:  # pragma: no cover
    QueryRewriter = None  # type: ignore

try:
    # Validador de claims con LLM (lo añadiremos en la siguiente clase)
    from app.agents.claims.validator import ClaimsValidator
except Exception:  # pragma: no cover
    ClaimsValidator = None  # type: ignore


class WorkflowCoordinator:
    """
    Coordina el ciclo completo para un claim (slide/línea):
        0) (Opcional) Query Rewriting con LLM
        1) RAG local (RecuperadorHibrido [+ Reranker])
        2) Si evidencia insuficiente → Orquestador de fuentes (race)
           2.a) Ingesta (PipelineIngesta) de lo encontrado
           2.b) Reintento RAG local
        3) (Opcional) Validador de Claims con LLM → etiqueta (GREEN/AMBER/RED)
           (fallback heurístico si no hay LLM)
        4) Compliance (EMA/FDA/ALL) sobre claim + citas [+ texto generado si aplica]
        5) Auditoría: decisión final, latencias por fase, modelos usados, costes LLM (si aplica)

    Esta clase NO hace parsing de archivos (PPT/DOC); se invoca por claim.
    """

    def __init__(
        self,
        *,
        retriever: Optional[RecuperadorHibrido] = None,
        reranker: Optional[Any] = None,       # instancia de Reranker o None
        orchestrador: Optional[Orquestador] = None,
        ingesta: Optional[PipelineIngesta] = None,
        compliance: Optional[ComplianceEngine] = None,
        auditor: Optional[Auditor] = None,
        query_rewriter: Optional[Any] = None, # instancia de QueryRewriter o None
        validator: Optional[Any] = None,      # instancia de ClaimsValidator o None
        min_hits: int = 2,                    # umbral para considerar "evidencia suficiente"
        citations_limit: int = 3,             # nº máx de citas que adjuntamos
    ) -> None:
        self.auditor = auditor or Auditor()
        self.retriever = retriever or RecuperadorHibrido(auditor=self.auditor)
        self.reranker = reranker  # puede ser None
        self.orchestrador = orchestrador or Orquestador()
        self.ingesta = ingesta or PipelineIngesta(auditor=self.auditor)
        self.compliance = compliance or ComplianceEngine(auditor=self.auditor)
        self.query_rewriter = query_rewriter  # puede ser None
        self.validator = validator            # puede ser None

        self.min_hits = max(1, min_hits)
        self.citations_limit = max(1, citations_limit)

    # ----------------------------
    # API principal (por claim)
    # ----------------------------
    def resolver_claim(
        self,
        *,
        claim: str,
        intake_id: str,
        claim_id: str,
        agentes_fuente: Optional[List[Any]] = None,  # lista de AgenteFuente
        timeout_agentes_s: int = 8,
        top_k: int = 12,
        generated_text: Optional[str] = None,        # si ya generaste borrador de material
        meta: Optional[dict] = None,                 # approved_indications, etc.
        costs: Optional[Dict[str, float]] = None,    # costes LLM si aplica
    ) -> Dict[str, Any]:
        timings: Dict[str, float] = {}
        models_info: Dict[str, Any] = {}
        costs = costs or {}

        # ---------------- 0) Query Rewriting (opcional, IA generativa) ----------------
        t0 = perf_counter()
        query = claim
        rewrites_used: List[str] = []

        if self.query_rewriter is not None:
            try:
                rewrites: List[str] = self.query_rewriter.rewrite(claim)
                if rewrites:
                    # Usamos la primera reescritura como query principal; guardamos el resto para fallback si quisieras.
                    query = rewrites[0]
                    rewrites_used = rewrites
                models_info["llm_query_rewriter"] = getattr(self.query_rewriter, "model_name", "unknown")
            except Exception:
                # degradamos a identidad
                rewrites_used = []
        timings["rewrite_ms"] = (perf_counter() - t0) * 1000.0

        # ---------------- 1) RAG local ----------------
        t1 = perf_counter()
        hits = self.retriever.buscar(query, top_k=top_k, intake_id=intake_id, claim_id=claim_id)

        # Reranker opcional
        if self.reranker is not None:
            try:
                hits = self.reranker.reordenar(query, hits)
                models_info["reranker_model"] = getattr(self.reranker, "model_name", "unknown")
            except Exception:
                pass

        timings["retrieval_ms"] = (perf_counter() - t1) * 1000.0

        # ---------------- 2) Escalado a agentes (si evidencia insuficiente) -----------
        t2 = perf_counter()
        escalated = False
        if len(hits) < self.min_hits and agentes_fuente:
            self.orchestrador.set_agentes(agentes_fuente)
            res = self.orchestrador.resolver_claim(claim, timeout_seconds=timeout_agentes_s)
            if res is not None:
                escalated = True
                # Ingestamos lo encontrado y repetimos RAG
                meta_ing = self.ingesta.ingerir_resultado(res, intake_id=intake_id)
                # Reintento RAG (podrías reusar 'query' o regenerar con rewrites)
                hits = self.retriever.buscar(query, top_k=top_k, intake_id=intake_id, claim_id=claim_id)
                if self.reranker is not None:
                    try:
                        hits = self.reranker.reordenar(query, hits)
                    except Exception:
                        pass
                models_info.setdefault("ingest", {})["last"] = meta_ing
        timings["agents_plus_ingest_ms"] = (perf_counter() - t2) * 1000.0

        # ---------------- 3) Citas (pasajes concretos) --------------------------------
        t3 = perf_counter()
        citations: List[Citation] = self.retriever.a_citas(hits, limit=self.citations_limit)
        timings["citations_ms"] = (perf_counter() - t3) * 1000.0

        # ---------------- 4) Etiqueta del claim (LLM o heurística) --------------------
        t4 = perf_counter()
        label = "AMBER"  # por defecto, conservador
        rationale = None
        if self.validator is not None:
            try:
                result = self.validator.validate(claim=claim, citations=citations, generated_text=generated_text, meta=meta or {})
                # Se espera que el validador devuelva dict con "label" y opcional "rationale"
                label = str(result.get("label", "AMBER")).upper()
                rationale = result.get("rationale")
                models_info["llm_claims_validator"] = getattr(self.validator, "model_name", "unknown")
                costs.update(result.get("costs", {}))
            except Exception:
                label = self._heuristic_label(citations)
        else:
            label = self._heuristic_label(citations)
        timings["classify_ms"] = (perf_counter() - t4) * 1000.0

        # ---------------- 5) Compliance ------------------------------------------------
        t5 = perf_counter()
        comp_report: ComplianceReport = self.compliance.run_checks(
            claim=claim,
            citations=citations,
            generated_text=generated_text,
            meta=meta or {},
            intake_id=intake_id,
            claim_id=claim_id,
        )
        timings["compliance_ms"] = (perf_counter() - t5) * 1000.0

        # ---------------- 6) Resultado + Auditoría -----------------------------------
        top_url = citations[0].url if citations else None
        resultado = ResultadoClaim(
            claim=claim,
            label=label,         # GREEN / AMBER / RED
            top_url=top_url,
            citations=citations,
            meta={
                "escalated": escalated,
                "rewrites_used": rewrites_used,
                "rationale": rationale,
                "compliance_score": comp_report.score,
                "compliance_passed": comp_report.passed,
                "compliance_issues": [i.model_dump() for i in comp_report.issues],
            },
        )

        # Modelos usados (embedding viene del retriever.vector_indexer)
        try:
            models_info["embedding_model"] = getattr(self.retriever.vec, "model_name", None)
        except Exception:
            pass

        # Auditoría final
        self.auditor.log_decision(
            intake_id=intake_id,
            claim_id=claim_id,
            resultado_claim=resultado,
            citations=citations,
            timings_ms=timings,
            costs=costs,
            model_info=models_info,
        )

        return {
            "resultado": resultado,
            "compliance": comp_report,
            "timings_ms": timings,
            "models": models_info,
        }

    # ---------------- Helpers ----------------
    @staticmethod
    def _heuristic_label(citations: List[Citation]) -> str:
        """
        Fallback rápido y conservador si no hay LLM:
        - 0 citas → RED
        - 1 cita  → AMBER
        - >=2     → GREEN
        """
        n = len(citations)
        if n == 0:
            return "RED"
        if n == 1:
            return "AMBER"
        return "GREEN"
