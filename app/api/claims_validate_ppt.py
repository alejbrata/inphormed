# -*- coding: utf-8 -*-
"""
/api/claims/validate-ppt (LLM-first)
- Extrae claims del PPTX con utils.claim_extractor (→ LLM).
- Reutiliza el validador de texto llamando a /api/claims/validate-text (loopback).
- Devuelve {"file_name", "total_claims", "results"} donde cada result
  es igual al de /validate-text pero con el campo where="slide:X".
"""

import os
import shutil
import tempfile
from typing import List, Dict, Any

from fastapi import APIRouter, UploadFile, File, Query
import httpx

from app.utils.claim_extractor import extract_claims_with_debug

router = APIRouter(prefix="/api/claims", tags=["claims"])

BACKEND_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
VALIDATE_TEXT_PATH = "/api/claims/validate-text"

@router.post("/validate-ppt")
async def validate_ppt(
    file: UploadFile = File(...),
    topk: int = Query(8),
    thr_green: float = Query(0.82),
    thr_yellow: float = Query(0.70),
    require_llm: bool = Query(True),
    render_ppt: bool = Query(False),      # ahora mismo no lo usamos aquí
    per_slide: int = Query(1),            # para ajustar N claims/slide si quieres
) -> Dict[str, Any]:
    # 1) Guarda el PPTX a temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # 2) EXTRAER (LLM → anti-datos + confianza)
    items = extract_claims_with_debug(tmp_path, max_claims_per_slide=int(per_slide))
    claim_texts: List[str] = [it["text"] for it in items]
    claim_where: List[str] = [f"slide:{int(it.get('slide_index', 0))}" for it in items]

    # 3) Validar cada claim reutilizando /api/claims/validate-text
    results: List[Dict[str, Any]] = []
    validate_url = f"{BACKEND_BASE}{VALIDATE_TEXT_PATH}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, text in enumerate(claim_texts):
            payload = {
                "text": text,
                "topk": int(topk),
                "thr_green": float(thr_green),
                "thr_yellow": float(thr_yellow),
                "require_llm": bool(require_llm),
            }
            try:
                r = await client.post(validate_url, json=payload)
                r.raise_for_status()
                res = r.json()
            except Exception as e:
                res = {
                    "where": claim_where[i],
                    "text": text,
                    "status": "red",
                    "best_score": 0.0,
                    "hits": [],
                    "_error": f"{type(e).__name__}: {e}",
                }
            res["where"] = claim_where[i]
            results.append(res)

    return {
        "file_name": file.filename,
        "total_claims": len(results),
        "results": results,
    }
