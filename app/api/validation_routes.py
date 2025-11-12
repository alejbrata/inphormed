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
import re
import json # <-- Importar JSON

# Importar el parser de PPTX
try:
    from pptx import Presentation
except ImportError:
    print("ERROR: 'python-pptx' no está instalado. Ejecuta: pip install python-pptx")
    Presentation = None

# --- ¡NUEVO! Importar cliente de OpenAI ---
try:
    from openai import OpenAI
except ImportError:
    print("ERROR: 'openai' no está instalado. Ejecuta: pip install openai")
    OpenAI = None

# Imports de tu lógica de TFM (Arquitectura 3)
from app.domain.core_models import Claim, SlideContext
from app.llm.judge import LLMJudge
from app.agents.sources.registry import get_default_fuentes
from app.agents.orchestrator.llm_first import orchestrate_llm_first
from app.services.annotate_service import annotate_pptx, write_snippets_html

# --- Definición del router ---
router = APIRouter(prefix="/api/claims", tags=["claims"])


# --- ¡NUEVO PARSER BASADO EN LLM! ---
# Este es el "Efecto Wow". Reemplaza el regex.

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

def _get_openai_client() -> Optional[OpenAI]:
    """Crea un cliente de OpenAI. Reutiliza la lógica de tu app."""
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ADVERTENCIA: OPENAI_API_KEY no encontrada. El extractor LLM fallará.")
        return None
    
    # (Si usas Azure, puedes añadir la lógica de 'judge.py' aquí)
    return OpenAI(api_key=api_key)

def _extract_pairs_with_llm(slide_text: str, slide_index: int, client: OpenAI) -> List[Dict[str, Any]]:
    """
    Usa un LLM (gpt-4o-mini) para extraer pares (claim, cita) del texto de una slide.
    """
    if not client:
        return []

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), # Usar un modelo rápido
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Texto de la Diapositiva {slide_index}:\n\n---\n{slide_text}\n---"}
            ]
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        pairs = data.get("pairs", [])
        
        # Añadir el índice de la slide para trazabilidad
        for p in pairs:
            p["slide_index"] = slide_index
        return pairs
    
    except Exception as e:
        print(f"Error en LLM Extractor (Slide {slide_index}): {e}")
        return []


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
    1. Extrae (claim, cita) usando el PARSER LLM.
    2. Pasa el claim + cita al orquestador (llm_first).
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

        # --- ¡CAMBIO CRÍTICO! ---
        # 1. Extracción (usando el NUEVO extractor LLM)
        if Presentation is None:
            raise HTTPException(status_code=500, detail="Dependencia 'python-pptx' no encontrada.")
        
        llm_client = _get_openai_client()
        if llm_client is None:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurada para el extractor.")

        from io import BytesIO
        prs = Presentation(BytesIO(raw))
        items = []

        for i, slide in enumerate(prs.slides, start=1):
            if i == 1: continue # Ignorar portada
            
            slide_text = ""
            for shape in slide.shapes:
                if hasattr(shape, "text_frame") and shape.text_frame:
                    slide_text += shape.text_frame.text + "\n"
            
            # Solo llamamos al LLM si la slide tiene texto
            slide_text = slide_text.strip()
            if len(slide_text) > 50: 
                pairs_from_slide = _extract_pairs_with_llm(slide_text, i, llm_client)
                items.extend(pairs_from_slide)
        # --- FIN DEL CAMBIO ---
        
        if not items:
            return JSONResponse(
                {"file_name": file_name, "total_claims": 0, "results": [], "error": "El LLM no detectó pares de claim/cita válidos."},
                status_code=400
            )

        fuentes = get_default_fuentes()
        judge = LLMJudge(mock=mock_llm)

        results: List[Dict[str, Any]] = []
        findings_for_annotation: List[Dict[str, Any]] = [] 

        for it in items:
            slide_idx = it["slide_index"]
            claim_text = it["claim_text"]
            citation_context = it["citation_text"] # <-- El LLM ya nos lo da separado
            
            # 2. Preparación del Contexto
            claim = Claim(text=claim_text)
            slide = SlideContext(
                title=f"Slide {slide_idx}",
                excerpt=claim_text,
                citation_string=citation_context # <-- Pasamos la cita
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
@router.get("/validate", summary="Valida un claim de texto (LLM-first)")
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