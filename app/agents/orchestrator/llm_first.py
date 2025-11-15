# app/agents/orchestrator/llm_first.py
from __future__ import annotations
import time, heapq, asyncio
from typing import List, Tuple

from app.domain.core_models import (
    Claim, SlideContext, CandidateDoc,
    OrchestratorResult, RankedItem
)
from app.llm.judge import LLMJudge
from app.agents.sources.base import BaseSourceAgent

LLM_MIN_CANCEL = 0.92
LLM_PATIENCE_MS = 1200
GLOBAL_DEADLINE_S = 15.0 # Aumentado para dar tiempo al crawler
TOPK_RETURN = 5

async def _gather_from_sources(
    sources: List[BaseSourceAgent], 
    claim: Claim, 
    slide_ctx: SlideContext, 
    limit: int
) -> List[CandidateDoc]:
    
    async def run_agent(agent: BaseSourceAgent):
        try:
            start = time.time()
            cands = await agent.fetch_candidates(claim, slide_ctx, limit=limit)
            elapsed = (time.time() - start) * 1000
            for c in cands:
                c.latency_ms = int(elapsed)
            return cands
        except Exception:
            return []

    tasks = [asyncio.create_task(run_agent(s)) for s in sources]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    out: List[CandidateDoc] = []
    for lst in results:
        out.extend(lst or [])
    return out

async def orchestrate_llm_first(
    claim: Claim,
    slide_ctx: SlideContext,
    sources: List[BaseSourceAgent],
    llm_judge: LLMJudge,
    topk: int = TOPK_RETURN,
) -> OrchestratorResult:
    t0 = time.time()
    fetch_start = time.time()
    
    candidates = await _gather_from_sources(sources, claim, slide_ctx, limit=max(2, topk * 2))
    fetch_ms = (time.time() - fetch_start) * 1000

    judged_heap: List[Tuple[float, CandidateDoc]] = []
    best: CandidateDoc | None = None
    canceled_early = False

    start_eval = time.time()
    patience_deadline = start_eval + (LLM_PATIENCE_MS / 1000.0)
    global_deadline = t0 + GLOBAL_DEADLINE_S

    for cand in candidates:
        if time.time() > global_deadline:
            break
        
        # El Juez ahora hace RAG interno (puede tardar más)
        jr = llm_judge.decide(claim, slide_ctx, cand)
        cand.llm_judgement = jr
        cand.score = jr.score
        cand.verdict = jr.verdict

        heapq.heappush(judged_heap, (-cand.score, cand))
        if best is None or cand.score > (best.score or 0.0):
            best = cand

        if best and best.score is not None and best.score >= LLM_MIN_CANCEL and time.time() >= patience_deadline:
            canceled_early = True
            break

    # (Lógica de 'while idx < len(candidates)'... se queda igual)

    ranked: List[RankedItem] = []
    k = 0
    while judged_heap and k < topk:
        _, cand = heapq.heappop(judged_heap)
        k += 1
        jr = cand.llm_judgement
        ranked.append(RankedItem(
            rank=k,
            source=cand.source,
            id=cand.id,
            title=cand.title,
            score=float(jr.score if jr else cand.score or 0.0),
            verdict=(jr.verdict if jr else (cand.verdict or "insufficient")),
            why_short=(jr.why_short if jr else ""),
            url=cand.url,
            year=cand.year,
            journal=cand.journal,
            # --- ¡CAMBIO! Pasamos el snippet al resultado ---
            best_snippet=(jr.best_snippet if jr else None)
        ))

    best_item = ranked[0] if ranked else None
    timings = {"fetch_ms": round(fetch_ms, 1), "eval_ms": round((time.time() - start_eval) * 1000, 1),
               "total_ms": round((time.time() - t0) * 1000, 1)}

    return OrchestratorResult(
        claim_id=claim.id,
        claim_text=claim.text,
        best=best_item,
        topk=ranked,
        canceled_early=canceled_early,
        thresholds={"LLM_MIN_CANCEL": LLM_MIN_CANCEL, "LLM_PATIENCE_MS": LLM_PATIENCE_MS},
        timings_ms=timings,
    )