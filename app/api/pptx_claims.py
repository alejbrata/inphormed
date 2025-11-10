# -*- coding: utf-8 -*-
"""
/api/claims/validate-ppt  → LLM-first
- Extrae claims con app.utils.claim_extractor (que usa el LLM).
- Reutiliza /api/claims/validate-text mediante loopback HTTP.
- Incluye LOGS explícitos para verificar que el endpoint nuevo se está usando.
"""

import os, shutil, tempfile, logging
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Query
import httpx

from app.utils.claim_extractor import extract_claims_with_debug

router = APIRouter(prefix="/api/claims", tags=["claims"])

# Logs visibles en consola
LOG = logging.getLogger("pptx_claims_llm")
if not LOG.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOG.addHandler(handler)
LOG.setLevel(logging.INFO)

BACKEND_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
VALIDATE_TEXT_PATH = "/api/claims/validate-text"

@router.post("/validate-ppt")
async def validate_ppt(
    file: UploadFile = File(...),
    topk: int = Query(8),
    thr_green: float = Query(0.82),
    thr_yellow: float = Query(0.70),
    require_llm: bool = Query(True),
    per_slide: int = Query(1),   # tope de claims/slide
) -> Dict[str, Any]:
    LOG.info("➡️  /api/claims/validate-ppt (LLM-first) — per_slide=%s", per_slide)

    # 1) Guardar temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # 2) EXTRAER claims con LLM
    items = extract_claims_with_debug(tmp_path, max_claims_per_slide=int(per_slide))
    claim_texts: List[str] = [it["text"] for it in items]
    where: List[str] = [f"slide:{int(it.get('slide_index', 0))}" for it in items]
    LOG.info("   → claims extraídos (LLM): %s", len(claim_texts))

    # 3) Validar cada claim reutilizando /validate-text
    validate_url = f"{BACKEND_BASE}{VALIDATE_TEXT_PATH}"
    results: List[Dict[str, Any]] = []
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
                res = {"where": where[i], "text": text, "status": "red",
                       "best_score": 0.0, "hits": [], "_error": f"{type(e).__name__}: {e}"}
            res["where"] = where[i]
            results.append(res)

    out = {"file_name": file.filename, "total_claims": len(results), "results": results}
    LOG.info("⬅️  /api/claims/validate-ppt — total_claims=%s", out["total_claims"])
    return out
