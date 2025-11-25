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

# Caché en memoria
SNIPPET_CACHE: Dict[str, Dict[str, Any]] = {}

def _extract_pairs_with_llm(
    slide_text: str, 
    slide_index: int, 
    llm_service: LLMService
) -> List[Dict[str, Any]]:
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
            if isinstance(p, dict):
                p["slide_index"] = slide_index
        return pairs
    
    except Exception as e:
        print(f"Error en LLM Extractor (Slide {slide_index}): {e}")
        return []


@router.post("/claims/validate-ppt", summary="Valida un PPTX con claims (LLM-first)")
async def validate_pptx_llm_first(
    request: Request,
    pptx: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    upload: UploadFile | None = File(None),
    ppt: UploadFile | None = File(None),
    pptx_b64: Optional[str] = Body(None),
    topk: int = Query(8),
    thr_green: float = Query(0.82),
    thr_yellow: float = Query(0.70),
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
                
                # --- ¡CAMBIO CLAVE! Guardar en caché SIEMPRE que haya candidato ---
                # (Incluso si no hay snippet/evidencia encontrada)
                if orch.best.id:
                    snippet_id = f"pmid_{orch.best.id}_slide_{slide_idx}"
                    # Preferimos full_text, si no abstract, si no un aviso
                    full_text_to_show = orch.best.full_text or orch.best.abstract or "Texto no recuperado."
                    
                    SNIPPET_CACHE[snippet_id] = {
                        "claim": claim_text,
                        "snippet": best_snippet or "(No se encontró evidencia específica en el texto)",
                        "full_text": full_text_to_show,
                        "paper_title": best_title,
                        "pubmed_url": best_url
                    }
                    # Forzamos que el link del PPTX vaya a nuestro visor
                    best_url = f"/api/viewer?id={snippet_id}"
                # -----------------------------------------------------------------

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
            
            # Preparamos el hallazgo para el PPTX
            findings_for_annotation.append({
                "slide": slide_idx,
                "color": color,
                "claim": claim_text,
                "source_url": best_url, # Ahora siempre apunta al visor si hay candidato
                "snippet_url": None,
                "ref_raw": best_title[:100], 
                "score": api_result["best_score"],
                # Si no hay snippet, ponemos el veredicto como excerpt
                "source_excerpt": (best_snippet or api_result["best_verdict"])[:300],
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
    file: UploadFile | None = File(None),
    upload: UploadFile | None = File(None),
    ppt: UploadFile | None = File(None),
    pptx_b64: Optional[str] = Body(None),
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
                
                # --- ¡CAMBIO CLAVE! Guardar en caché SIEMPRE que haya candidato ---
                # (Incluso si no hay snippet/evidencia encontrada)
                if orch.best.id:
                    snippet_id = f"pmid_{orch.best.id}_slide_{slide_idx}"
                    # Preferimos full_text, si no abstract, si no un aviso
                    full_text_to_show = orch.best.full_text or orch.best.abstract or "Texto no recuperado."
                    
                    SNIPPET_CACHE[snippet_id] = {
                        "claim": claim_text,
                        "snippet": best_snippet or "(No se encontró evidencia específica en el texto)",
                        "full_text": full_text_to_show,
                        "paper_title": best_title,
                        "pubmed_url": best_url
                    }
                    # Forzamos que el link del PPTX vaya a nuestro visor
                    best_url = f"/api/viewer?id={snippet_id}"
                # -----------------------------------------------------------------

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
            
            # Preparamos el hallazgo para el PPTX
            findings_for_annotation.append({
                "slide": slide_idx,
                "color": color,
                "claim": claim_text,
                "source_url": best_url, # Ahora siempre apunta al visor si hay candidato
                "snippet_url": None,
                "ref_raw": best_title[:100], 
                "score": api_result["best_score"],
                # Si no hay snippet, ponemos el veredicto como excerpt
                "source_excerpt": (best_snippet or api_result["best_verdict"])[:300],
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


import json
import re
import html as html_lib

@router.get("/viewer", response_class=HTMLResponse)
async def get_snippet_viewer(id: str = Query(..., description="ID del snippet cacheado")):
    data = SNIPPET_CACHE.get(id)
    if not data:
        return HTMLResponse("<h1>Error</h1><p>Snippet no encontrado o caché expirada.</p>", status_code=404)

    full_text = data.get("full_text", "")
    snippet = data.get("snippet", "")
    
    is_abstract_only = len(full_text) < 3000
    source_label = "⚠️ ABSTRACT (Texto completo no disponible)" if is_abstract_only else "📄 TEXTO COMPLETO (Extraído)"
    source_class = "warning" if is_abstract_only else "success"

    # Lógica de resaltado difuso en Python (más robusta que JS para esto)
    # 1. Dividimos el snippet en palabras
    snippet_words = re.findall(r'\w+', snippet)
    
    match_found = False
    content_html = ""

    if snippet_words:
        # 2. Construimos regex: palabra + separadores no alfanuméricos + palabra...
        #    re.escape evita problemas con caracteres especiales en las palabras
        #    \W+ coincide con espacios, saltos de línea, puntuación, etc.
        pattern = r'\W+'.join([re.escape(w) for w in snippet_words])
        
        # 3. Buscamos en el texto completo (ignorando mayúsculas/minúsculas)
        #    Usamos re.DOTALL por si acaso, aunque \W ya incluye saltos de línea.
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            match = regex.search(full_text)
            
            if match:
                match_found = True
                start, end = match.span()
                
                # 4. Construimos el HTML resaltado
                #    Escapamos cada parte por seguridad HTML
                safe_pre = html_lib.escape(full_text[:start])
                safe_match = html_lib.escape(full_text[start:end])
                safe_post = html_lib.escape(full_text[end:])
                
                content_html = f'{safe_pre}<span id="evidence-target" class="highlight">{safe_match}</span>{safe_post}'
        except Exception as e:
            print(f"Error en regex highlighting: {e}")

    if not match_found:
        # Fallback: mostramos el texto sin resaltar
        content_html = html_lib.escape(full_text)

    # Convertimos saltos de línea a <br> para visualización
    content_html = content_html.replace("\n", "<br>")
    
    # Escapamos el snippet para usarlo en JS (solo para el fallback box)
    snippet_safe = json.dumps(snippet)

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Visor de Evidencia</title>
        <style>
            body {{ font-family: "Georgia", serif; line-height: 1.6; margin: 0; padding: 0; background: #f9f9f9; color: #333; }}
            .container {{ max-width: 800px; margin: 40px auto; padding: 40px; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ font-family: "Segoe UI", sans-serif; color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .meta {{ background: #f0f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #3498db; }}
            .source-tag {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-family: sans-serif; font-size: 0.8em; margin-bottom: 10px; }}
            .source-tag.warning {{ background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }}
            .source-tag.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            
            .highlight {{ 
                background-color: #ffff00; 
                color: #000;
                border-bottom: 3px solid #ffcc00; 
                font-weight: bold; 
                padding: 2px 4px;
                border-radius: 3px;
                box-shadow: 0 0 5px rgba(255, 255, 0, 0.5);
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ box-shadow: 0 0 0 0 rgba(255, 204, 0, 0.7); }}
                70% {{ box-shadow: 0 0 0 10px rgba(255, 204, 0, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(255, 204, 0, 0); }}
            }}

            .highlight-box {{ background-color: #fff3cd; padding: 15px; border: 1px solid #ffeeba; border-radius: 5px; margin-bottom: 20px; color: #856404; }}
            a.btn {{ display: inline-block; padding: 8px 15px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; font-family: sans-serif; font-size: 0.9em; }}
            .content {{ font-size: 1.1em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visor de Trazabilidad</h1>
            <div class="meta">
                <div class="source-tag {source_class}">{source_label}</div>
                <p><strong>Claim:</strong> "{data['claim']}"</p>
                <p><strong>Fuente:</strong> {data['paper_title']}</p>
                <a href="{data['pubmed_url']}" target="_blank" class="btn">Ver fuente original</a>
            </div>
            
            <!-- Caja flotante si no se encuentra en el texto -->
            <div id="not-found-box" class="highlight-box" style="display:none">
                <strong>Evidencia citada (no encontrada exacta en texto):</strong><br>
                <span id="snippet-display"></span>
            </div>

            <div id="content-area" class="content">{content_html}</div>
        </div>
        <script>
            window.onload = function() {{
                const element = document.getElementById("evidence-target");
                if (element) {{ 
                    // Si el backend encontró el match, hacemos scroll
                    element.scrollIntoView({{ behavior: "smooth", block: "center" }}); 
                }} else {{
                    // Si no, mostramos la caja de aviso
                    const snippet = {snippet_safe};
                    if (snippet && snippet.length > 5) {{
                        document.getElementById("not-found-box").style.display = "block";
                        document.getElementById("snippet-display").textContent = snippet;
                    }}
                }}
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)