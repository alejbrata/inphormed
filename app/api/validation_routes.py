# app/api/validation_routes.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse 
import base64
import tempfile
import os
import shutil
import re
import json 
import urllib.parse 

try:
    from pptx import Presentation
except ImportError:
    print("ERROR: 'python-pptx' no está instalado. Ejecuta: pip install python-pptx")
    Presentation = None

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: 'openai' no está instalado. Ejecuta: pip install openai")
    OpenAI = None

from app.services.llm_service import LLMService, LLMServiceError
from app.domain.core_models import Claim, SlideContext
from app.llm.judge import LLMJudge
from app.agents.sources.registry import get_default_fuentes
from app.agents.orchestrator.llm_first import orchestrate_llm_first
from app.services.annotate_service import annotate_pptx, write_snippets_html

router = APIRouter(prefix="/api", tags=["claims"])

EXTRACTOR_SYSTEM_PROMPT = """
Eres un asistente de IA para análisis de documentos farmacéuticos.
Tu tarea es analizar el texto de una DIAPOSITIVA de PowerPoint y extraer los "pares de validación".
Un "par de validación" consiste en:
1. El "claim" (la afirmación principal de eficacia, seguridad, etc.).
2. La "cita" (el texto de la referencia bibliográfica, ej: "Kimball AB, et al...").

Busca patrones como "Claim X..." y "Cita (Vancouver):...".
Ignora texto de "Notas:", portadas, o títulos de sección.

Devuelve SÓLO un objeto JSON con la clave "pairs", así:
{
  "pairs": [
    {
      "claim_text": "El texto del claim 1...",
      "citation_text": "El texto de la cita 1..."
    }
  ]
}
Si no hay pares, devuelve {"pairs": []}.
"""

# --- ¡NUEVO! Caché en memoria para los snippets ---
SNIPPET_CACHE: Dict[str, Dict[str, Any]] = {}

# --- ¡CORREGIDO! ---
# Esta es la función que daba el SyntaxError.
# Reemplazamos '...' con los argumentos reales.
def _extract_pairs_with_llm(
    slide_text: str, 
    slide_index: int, 
    llm_service: LLMService
) -> List[Dict[str, Any]]:
# --- FIN DE LA CORRECCIÓN ---
    """
    Usa un LLM (vía LLMService) para extraer pares (claim, cita).
    """
    try:
        user_prompt = (
            f"Texto de la Diapositiva {slide_index}:\n\n---\n{slide_text}\n---\n\n"
            "Extrae los pares (claim, cita) de este texto y devuelve un objeto JSON."
        )
        
        data = llm_service.chat_with_json(
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        if data is None or "pairs" not in data:
            return []
            
        pairs = data.get("pairs", [])
        for p in pairs:
            if isinstance(p, dict): # Asegurarnos de que el LLM devuelve lo que queremos
                p["slide_index"] = slide_index
        return pairs
    
    except Exception as e:
        print(f"Error en LLM Extractor (Slide {slide_index}): {e}")
        return []


@router.post("/claims/validate-ppt", summary="Valida un PPTX con claims (LLM-first)")
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
    raw: bytes | None = None
    up: UploadFile | None = pptx or file or upload or ppt
    file_name = "upload.pptx" 

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

        if Presentation is None:
            raise HTTPException(status_code=500, detail="Dependencia 'python-pptx' no encontrada.")
        
        try:
            llm_extractor_service = LLMService(
                model=os.getenv("OPENAI_EXTRACTOR_MODEL", "gpt-4o-mini"),
                temperature=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al iniciar LLMService: {e}")

        from io import BytesIO
        prs = Presentation(BytesIO(raw))
        items = []

        for i, slide in enumerate(prs.slides, start=1):
            if i == 1: continue
            
            slide_text = ""
            for shape in slide.shapes:
                if hasattr(shape, "text_frame") and shape.text_frame:
                    slide_text += shape.text_frame.text + "\n"
            
            slide_text = slide_text.strip()
            if len(slide_text) > 50: 
                pairs_from_slide = _extract_pairs_with_llm(slide_text, i, llm_extractor_service)
                items.extend(pairs_from_slide)
        
        if not items:
            return JSONResponse(
                {"file_name": file_name, "total_claims": 0, "results": [], "error": "El LLM no detectó pares de claim/cita válidos."},
                status_code=400
            )

        fuentes = get_default_fuentes()
        judge = LLMJudge(mock=mock_llm) 

        results: List[Dict[str, Any]] = []
        findings_for_annotation: List[Dict[str, Any]] = [] 

        SNIPPET_CACHE.clear()

        for it in items:
            slide_idx = it["slide_index"]
            claim_text = it["claim_text"]
            citation_context = it["citation_text"] 
            
            claim = Claim(text=claim_text)
            slide = SlideContext(
                title=f"Slide {slide_idx}",
                excerpt=claim_text,
                citation_string=citation_context 
            )

            orch = await orchestrate_llm_first(
                claim=claim,
                slide_ctx=slide,
                sources=fuentes,
                llm_judge=judge,
                topk=topk
            )

            best_url = None
            best_title = ""
            best_snippet = None
            
            if orch.best:
                score = float(orch.best.score)
                color = "green" if score >= thr_green else ("yellow" if score >= thr_yellow else "red")
                best_url = orch.best.url 
                best_title = orch.best.title
                best_snippet = orch.best.best_snippet
                
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
            
            snippet_id = None
            if best_snippet and orch.best and orch.best.id:
                snippet_id = f"pmid_{orch.best.id}_slide_{slide_idx}"
                SNIPPET_CACHE[snippet_id] = {
                    "claim": claim_text,
                    "snippet": best_snippet,
                    "paper_title": best_title,
                    "pubmed_url": best_url
                }

            findings_for_annotation.append({
                "slide": slide_idx,
                "color": color,
                "claim": claim_text,
                "source_url": f"/api/viewer?id={snippet_id}" if snippet_id else best_url,
                "snippet_url": None,
                "ref_raw": best_title[:100], 
                "score": api_result["best_score"],
                "source_excerpt": best_snippet[:300] if best_snippet else "",
            })

        payload: Dict[str, Any] = {
            "file_name": file_name,
            "total_claims": len(results),
            "results": results,
            "thresholds": {"green": thr_green, "yellow": thr_yellow},
        }

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
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


@router.get("/claims/validate", summary="Valida un claim de texto (LLM-first)")
async def validate_claim_llm_first(
    claim_text: str = Query(..., description="Texto del claim"),
    slide_title: Optional[str] = Query("", description="Título de la slide (contexto)"),
    slide_excerpt: Optional[str] = Query("", description="Contexto/Cita (autores, año...)"),
    topk: int = Query(5, ge=1, le=10),
    mock_llm: bool = Query(False, description="Usa juez simulado para pruebas")
):
    claim = Claim(text=claim_text)
    slide = SlideContext(
        title=slide_title or "", 
        excerpt=slide_excerpt or "",
        citation_string=f"{slide_title}\n{slide_excerpt}"
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


@router.get("/viewer", response_class=HTMLResponse)
async def get_snippet_viewer(id: str = Query(..., description="ID del snippet cacheado")):
    """
    Esta es la página del "efecto wow". Muestra la evidencia resaltada.
    """
    data = SNIPPET_CACHE.get(id)
    if not data:
        return HTMLResponse("<h1>Error</h1><p>Snippet no encontrado o caché expirada.</p>", status_code=404)

    snippet_html = data['snippet']
    try:
        claim_words = re.findall(r'\b\w{4,}\b', data['claim'].lower())
        for word in set(claim_words):
            snippet_html = re.sub(
                f"({re.escape(word)})", 
                r"<mark>\1</mark>", 
                snippet_html, 
                flags=re.IGNORECASE
            )
    except Exception:
        snippet_html = data['snippet'] # Fallback

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Visor de Evidencia</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; }}
            .container {{ max-width: 900px; margin: 20px auto; padding: 30px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a3a53; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
            h2 {{ color: #333; }}
            .claim {{ background-color: #e6f7ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; font-style: italic; }}
            .paper {{ font-size: 0.9em; color: #555; }}
            .snippet {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 20px; border-radius: 5px; line-height: 1.7; }}
            mark {{ background-color: #fff799; padding: 2px 0; }}
            footer {{ margin-top: 20px; font-size: 0.8em; color: #888; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visor de Evidencia</h1>
            
            <h2>Claim Validado:</h2>
            <div class="claim">"{data['claim']}"</div>
            
            <h2>Evidencia (Fragmento del Texto Completo):</h2>
            <div class="snippet">
                <p>{snippet_html.replace(r'\n', '<br><br>')}</p>
            </div>
            
            <footer>
                <p><strong>Paper:</strong> {data['paper_title']}</p>
                <p><strong>Enlace a PubMed:</strong> <a href="{data['pubmed_url']}" target="_blank">{data['pubmed_url']}</a></p>
                <p>ID de Snippet: {id}</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)