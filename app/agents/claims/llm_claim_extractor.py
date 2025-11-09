# -*- coding: utf-8 -*-
"""
Extractor LLM de CLAIMS desde PPTX (IA generativa primero).
- Ignora líneas "de datos" (%, p-values, n=..., HR/OR/RR, DOI/PMID, metadatos).
- Aplica umbral de confianza.
- Devuelve items con slide_index (1-based), text, score y debug.

Requisitos:
  pip install python-pptx openai
Variables:
  OPENAI_API_KEY   (obligatoria)
  OPENAI_MODEL     (opcional, por defecto: gpt-4o-mini)
"""

from __future__ import annotations
import io
import os
import re
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Iterable

from pptx import Presentation
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """Eres un extractor de CLAIMS científicos en material farmacéutico.
Tu tarea: dado el texto de UNA DIAPOSITIVA, devuelve a lo sumo N *claims* claros.
Qué es un claim: afirmación sustantiva verificable (eficacia, seguridad, comparación con SOC, reducción de riesgo, endpoints clínicos, etc.).
Qué NO es un claim: cifras sueltas, porcentajes, p-values, "n =", IC 95%, notas legales, referencias, DOI/PMID, fechas o metadatos.

Devuelve SOLO JSON con esta forma:
{
  "claims": [
    {"text": "...", "confidence": 0.0-1.0},
    ...
  ]
}

Reglas:
- No incluyas líneas que "huelan a datos" (%/p=/n=/IC/HR/OR/RR/PMID/DOI/fechas).
- Resume el claim si aparece fragmentado.
- Máximo N claims (según te indique el usuario).
- Si no hay claims, devuelve {"claims": []}.
"""

USER_PROMPT_TMPL = """Extrae como máximo {max_n} claims del siguiente texto de una diapositiva.
Devuelve SOLO el JSON pedido (sin comentarios).

[Slide title]: {title}
[Slide text]:
{body}
"""

# -------- Heurísticas anti "datos" --------

DATA_PATTERNS = [
    r"\b\d{1,3}\s?%\b",                  # porcentajes
    r"\bp\s*[<=>]\s*0\.\d+",             # p-values
    r"\bIC\s*95%|\bCI\s*95%",            # intervalos de confianza
    r"\bn\s*=\s*\d+",                    # tamaño muestral
    r"\b(HR|OR|RR)\s*=\s*\d+(\.\d+)?",   # hazard/odds/risk ratios
    r"\bDOI\b|\bPMID\b",                 # bibliografía
    r"\b(Generado|Fecha|Updated)\s*:\s*\d{4}-\d{2}-\d{2}",  # metadatos slide
]
DATA_REGEX = re.compile("|".join(DATA_PATTERNS), flags=re.IGNORECASE)

def _is_data_like(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(DATA_REGEX.search(t))

# -------- Utils --------

def _clean_line(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _slide_texts(slide) -> List[str]:
    lines: List[str] = []
    for shape in slide.shapes:
        if hasattr(shape, "text_frame") and getattr(shape, "has_text_frame", False):
            txt = (shape.text_frame.text or "").strip()
            if txt:
                for raw in txt.splitlines():
                    ln = _clean_line(raw)
                    if ln:
                        lines.append(ln)
    return lines

def _slide_title(slide) -> str:
    try:
        t = slide.shapes.title
        if t and t.has_text_frame:
            return _clean_line(t.text_frame.text or "")
    except Exception:
        pass
    for ln in _slide_texts(slide):
        if len(ln) >= 12:
            return ln
    return ""

# -------- Modelo --------

@dataclass
class ClaimHit:
    slide_index: int      # 1-based
    text: str
    score: float          # [0..1]
    debug: Dict[str, Any]

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

# -------- LLM --------

def _call_llm_extract_claims(client: OpenAI, title: str, body: str, max_n: int) -> List[Dict[str, Any]]:
    user_prompt = USER_PROMPT_TMPL.format(max_n=max_n, title=title or "(sin título)", body=body)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        claims = data.get("claims", [])
        if not isinstance(claims, list):
            return []
        out = []
        for it in claims:
            if not isinstance(it, dict):
                continue
            txt = _clean_line(it.get("text", ""))
            if not txt:
                continue
            conf = it.get("confidence", 0.75)
            try:
                conf = float(conf)
            except Exception:
                conf = 0.75
            out.append({"text": txt, "confidence": conf})
        return out[:max_n]
    except Exception:
        # Fallback si llega texto plano
        lines = [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]
        lines = [ln for ln in lines if len(ln) >= 8]
        lines = _dedupe_keep_order(lines)[:max_n]
        return [{"text": ln, "confidence": 0.70} for ln in lines]

# -------- Público --------

def extract_claims_from_pptx_llm(path_pptx: str,
                                 max_claims_per_slide: int = 1,
                                 min_confidence: float = 0.60) -> List[Dict[str, Any]]:
    """
    Procesa un PPTX con un LLM y devuelve:
      [ { "slide_index": 1, "text": "...", "score": 0.82, "debug": {...} }, ... ]
    """
    with open(path_pptx, "rb") as f:
        data = io.BytesIO(f.read())
    pres = Presentation(data)

    client = OpenAI()

    hits: List[ClaimHit] = []

    for idx, slide in enumerate(pres.slides, start=1):
        title = _slide_title(slide)
        lines = _slide_texts(slide)
        if not lines:
            continue

        # Pre-filtrado local de ruido "de datos"
        body_lines = [ln for ln in lines if not _is_data_like(ln)]
        if not body_lines:
            continue

        body = "\n".join(body_lines)

        # LLM: extrae hasta N claims por slide
        llm_items = _call_llm_extract_claims(client, title, body, max_claims_per_slide)
        for it in llm_items:
            cand = it.get("text", "").strip()
            if not cand:
                continue
            if _is_data_like(cand):
                continue
            score = float(it.get("confidence", 0.0))
            if score < min_confidence:
                continue

            hit = ClaimHit(
                slide_index=idx,
                text=_clean_line(cand),
                score=score,
                debug={
                    "title": title,
                    "slide_body_preview": body[:600],
                    "llm_raw": it,
                    "filters": {"min_confidence": min_confidence, "anti_data": True},
                },
            )
            hits.append(hit)

    # Dedupe por (slide_index, text)
    key = set()
    unique: List[ClaimHit] = []
    for h in hits:
        k = (h.slide_index, h.text.lower())
        if k not in key:
            key.add(k)
            unique.append(h)

    unique.sort(key=lambda h: (h.slide_index, -h.score))
    return [h.model_dump() for h in unique]
