# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Body, Request
from fastapi.responses import JSONResponse
import base64
import tempfile

from app.utils.claim_extractor import extract_claims_with_debug
from app.domain.core_models import Claim, SlideContext
from app.llm.judge import LLMJudge
from app.agents.sources.registry import get_default_fuentes
from app.agents.orchestrator.llm_first import orchestrate_llm_first
from app.services.annotate_service import annotate_pptx, write_snippets_html

router = APIRouter(prefix="/api/claims", tags=["claims"])

@router.post("/validate-ppt", summary="Valida un PPTX con claims (LLM-first)")
async def validate_pptx_llm_first(
    request: Request,
    pptx: UploadFile | None = File(None, description="Archivo .pptx"),
    file: UploadFile | None = File(None, description="Archivo .pptx (alias)"),
    upload: UploadFile | None = File(None, description="Archivo .pptx (alias)"),
    ppt: UploadFile | None = File(None, description="Archivo .pptx (alias)"),
    pptx_b64: Optional[str] = Body(None),
    topk: int = Query(8, ge=1, le=15),
    thr_green: float = Query(0.82, ge=0.0, le=1.0),
    thr_yellow: float = Query(0.70, ge=0.0, le=1.0),
    require_llm: bool = Query(True),
    render_ppt: bool = Query(True),
    mock_llm: bool = Query(False),
):
    raw: bytes | None = None
    up: UploadFile | None = pptx or file or upload or ppt

    if up is not None:
        if not up.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="Sube un .pptx válido")
        raw = await up.read()
        file_name = up.filename
    elif pptx_b64:
        raw = base64.b64decode(pptx_b64)
        file_name = "upload.pptx"
    else:
        ct = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ct in {"application/octet-stream","application/vnd.openxmlformats-officedocument.presentationml.presentation"}:
            raw = await request.body()
            file_name = "upload.pptx"
        else:
            raise HTTPException(status_code=422, detail="No se recibió el PPTX.")

    # Guardar temporal para extractor/anotación
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    items = extract_claims_with_debug(tmp_path, max_claims_per_slide=1)
    if not items:
        return JSONResponse({"file_name": file_name, "total_claims": 0, "results": []})

    fuentes = get_default_fuentes()
    judge = LLMJudge(mock=mock_llm)

    results: List[Dict[str, Any]] = []
    for it in items:
        slide_idx = int(it.get("slide_index", 0))
        claim_text = (it.get("text") or "").strip()
        claim = Claim(text=claim_text)
        slide = SlideContext(title=it.get("title",""), excerpt=it.get("body_excerpt",""))

        orch = await orchestrate_llm_first(
            claim=claim,
            slide_ctx=slide,
            sources=fuentes,
            llm_judge=judge,
            topk=topk
        )

        if orch.best:
            score = float(orch.best.score)
            color = "green" if score >= thr_green else ("yellow" if score >= thr_yellow else "red")
            results.append({
                "where": f"slide:{slide_idx}",
                "slide_number": slide_idx,
                "text": claim_text,
                "status": color,
                "best_score": score,
                "best_verdict": orch.best.verdict,
                "best_title": orch.best.title,
                "best_url": orch.best.url,
                "ranked": [ri.model_dump() for ri in orch.topk],
                "timings_ms": orch.timings_ms,
            })
        else:
            results.append({
                "where": f"slide:{slide_idx}",
                "slide_number": slide_idx,
                "text": claim_text,
                "status": "red",
                "best_score": 0.0,
                "best_verdict": "insufficient",
                "best_title": "",
                "best_url": None,
                "ranked": [],
                "timings_ms": {},
            })

    payload: Dict[str, Any] = {
        "file_name": file_name,
        "total_claims": len(results),
        "results": results,
        "thresholds": {"green": thr_green, "yellow": thr_yellow},
    }

       # 4) PPTX anotado embebido (opcional)
        # 4) PPTX anotado embebido (opcional)
    if render_ppt:
        # Normaliza registros -> lo que TU annotate_service espera
        def to_annotation(rec: dict) -> dict:
            return {
                "slide": rec["slide_number"],  # clave que usa tu servicio
                "color": rec["status"],        # green/yellow/red
                "verdict": rec.get("best_verdict", "insufficient"),
                "score": rec.get("best_score", 0.0),
            }

        def to_finding(rec: dict) -> dict:
            top = (rec.get("ranked") or [])
            snippet = ""
            if top:
                t0 = top[0]
                snippet = t0.get("why_short") or t0.get("title") or ""
            return {
                "slide": rec["slide_number"],             # OBLIGATORIO
                "color": rec["status"],                   # OBLIGATORIO -> evita KeyError
                "claim": rec["text"],                     # texto del claim
                "citation": rec.get("best_title", ""),    # título paper (si hay)
                "url": rec.get("best_url"),               # url (si hay)
                "snippet": snippet,                       # breve por qué / título
                "score": rec.get("best_score", 0.0),
                "verdict": rec.get("best_verdict", "insufficient"),
            }

        annotations = [to_annotation(r) for r in results]
        findings = [to_finding(r) for r in results]

        snippets_uid = uuid.uuid4().hex
        snippets_path = write_snippets_html(snippets_uid, findings)
        snippets_uri = Path(snippets_path).resolve().as_uri()
        for idx, finding in enumerate(findings, start=1):
            finding["snippet_url"] = f"{snippets_uri}#claim-{idx}"

        try:
            # Tu firma actual: (ruta, annotations, findings)
            annotated = annotate_pptx(tmp_path, annotations, findings)
        except TypeError:
            # Compatibilidad con versión 2-args
            annotated = annotate_pptx(tmp_path, annotations)

        payload["annotated_pptx_b64"] = base64.b64encode(annotated).decode("utf-8")
        payload["annotated_file_name"] = file_name.replace(".pptx", "_validated.pptx")
        payload["snippets_html"] = snippets_path



    return JSONResponse(payload)
