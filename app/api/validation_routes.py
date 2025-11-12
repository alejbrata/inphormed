# app/api/validation_routes.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Body, Request
from fastapi.responses import JSONResponse
import base64
import tempfile
import os
import shutil

# Imports de tu lógica de TFM (Arquitectura 3)
from app.utils.claim_extractor import extract_claims_with_debug
from app.domain.core_models import Claim, SlideContext # <-- Usando el modelo modificado
from app.llm.judge import LLMJudge
from app.agents.sources.registry import get_default_fuentes
from app.agents.orchestrator.llm_first import orchestrate_llm_first
from app.services.annotate_service import annotate_pptx, write_snippets_html

# --- Definición del router ---
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
    render_ppt: bool = Query(True),
    mock_llm: bool = Query(False),
):
    """
    Endpoint principal para validar un PPTX.
    1. Extrae claims (y su contexto de cita) usando el extractor LLM.
    2. Pasa el claim + contexto de cita al orquestador (llm_first).
    3. El orquestador usa el AgentePubMed (modificado) para buscar por cita.
    4. El LLMJudge puntúa el paper encontrado.
    5. Genera un PPTX anotado con colores e hipervínculos.
    """
    raw: bytes | None = None
    up: UploadFile | None = pptx or file or upload or ppt
    file_name = "upload.pptx" # Default

    if up is not None:
        if not up.filename or not up.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="Sube un .pptx válido")
        raw = await up.read()
        file_name = up.filename
    elif pptx_b64:
        raw = base64.b64decode(pptx_b64)
    else:
        ct = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ct in {"application/octet-stream","application/vnd.openxmlformats-officedocument.presentationml.presentation"}:
            raw = await request.body()
        else:
            raise HTTPException(status_code=422, detail="No se recibió el PPTX.")

    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, f"in_{uuid.uuid4().hex}.pptx")
    out_path = os.path.join(tmp_dir, f"out_{uuid.uuid4().hex}.pptx")

    try:
        with open(tmp_path, "wb") as tmp:
            tmp.write(raw)

        # 1. Extracción (usando el extractor LLM)
        items = extract_claims_with_debug(tmp_path, max_claims_per_slide=1)
        if not items:
            return JSONResponse({"file_name": file_name, "total_claims": 0, "results": []})

        fuentes = get_default_fuentes()
        judge = LLMJudge(mock=mock_llm)

        results: List[Dict[str, Any]] = []
        findings_for_annotation: List[Dict[str, Any]] = [] 

        for it in items:
            slide_idx = int(it.get("slide_index", 0))
            claim_text = (it.get("text") or "").strip()
            
            # 2. Preparación del Contexto (con la lógica de cita que implementamos)
            debug_info = it.get("debug", {})
            slide_title = debug_info.get("title", "")
            slide_body_text = debug_info.get("slide_body_preview", "") 
            citation_context = f"{slide_title}\n{slide_body_text}"

            claim = Claim(text=claim_text)
            slide = SlideContext(
                title=slide_title,
                excerpt=slide_body_text,
                citation_string=citation_context 
            )

            # 3. Orquestación
            orch = await orchestrate_llm_first(
                claim=claim,
                slide_ctx=slide,
                sources=fuentes,
                llm_judge=judge,
                topk=topk
            )

            # 4. Procesamiento de resultados
            best_url = None
            best_title = ""
            best_snippet = ""
            
            if orch.best:
                score = float(orch.best.score)
                color = "green" if score >= thr_green else ("yellow" if score >= thr_yellow else "red")
                best_url = orch.best.url
                best_title = orch.best.title
                best_snippet = orch.best.why_short
                
                api_result = {
                    "where": f"slide:{slide_idx}",
                    "text": claim_text,
                    "status": color,
                    "best_score": score,
                    "best_verdict": orch.best.verdict,
                    "best_title": best_title,
                    "best_url": best_url,
                    "ranked": [ri.model_dump() for ri in orch.topk],
                    "timings_ms": orch.timings_ms,
                }
            else:
                color = "red"
                api_result = {
                    "where": f"slide:{slide_idx}",
                    "text": claim_text,
                    "status": "red",
                    "best_score": 0.0,
                    "best_verdict": "insufficient",
                    "best_title": "",
                    "best_url": None,
                    "ranked": [],
                    "timings_ms": {},
                }
            
            results.append(api_result)
            
            # 5. Preparar datos para el PPTX coloreado
            findings_for_annotation.append({
                "slide": slide_idx,
                "color": color,
                "claim": claim_text,
                "source_url": best_url,      # <-- El hipervínculo
                "snippet_url": None,
                "ref_raw": best_title[:100], 
                "score": api_result["best_score"],
                "source_excerpt": best_snippet,
            })

        payload: Dict[str, Any] = {
            "file_name": file_name,
            "total_claims": len(results),
            "results": results,
            "thresholds": {"green": thr_green, "yellow": thr_yellow},
        }

        # 6. Generar PPTX anotado
        if render_ppt:
            try:
                annotated_bytes = annotate_pptx(tmp_path, out_path, findings_for_annotation)
                payload["annotated_pptx_b64"] = base64.b64encode(annotated_bytes).decode("utf-8")
                payload["annotated_file_name"] = file_name.replace(".pptx", "_validated.pptx")
            
            except Exception as e_annotate:
                print(f"Error annotating PPTX: {e_annotate}")
                payload["annotated_pptx_b64"] = None
                payload["annotated_file_name"] = None


        return JSONResponse(payload)

    finally:
        # Limpiar directorio temporal
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

# --- FUSIÓN: Endpoint de /validate-text ---
# (Este endpoint venía de app/api/claims.py)
@router.get("/validate", summary="Valida un claim de texto (LLM-first)")
async def validate_claim_llm_first(
    claim_text: str = Query(..., description="Texto del claim"),
    slide_title: Optional[str] = Query("", description="Título de la slide (contexto)"),
    slide_excerpt: Optional[str] = Query("", description="Contexto/Cita (autores, año...)"),
    topk: int = Query(5, ge=1, le=10),
    mock_llm: bool = Query(False, description="Usa juez simulado para pruebas")
):
    claim = Claim(text=claim_text)
    
    # Usamos el campo 'slide_excerpt' para pasar la cita
    slide = SlideContext(
        title=slide_title or "", 
        excerpt=slide_excerpt or "",
        citation_string=f"{slide_title}\n{slide_excerpt}" # Pasamos el contexto de cita
    )

    fuentes = get_default_fuentes()
    judge = LLMJudge(mock=mock_llm)

    result = await orchestrate_llm_first(
        claim=claim,
        slide_ctx=slide,
        sources=fuentes,
        llm_judge=judge,
        topk=topk,
    )
    return result