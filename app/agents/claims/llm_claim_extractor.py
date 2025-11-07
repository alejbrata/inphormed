# -*- coding: utf-8 -*-
"""
LLM-first extractor: detecta qué frases de cada slide son CLAIM y cuáles son DATOS/REFERENCIAS,
sin imponer formato al PPT de origen. Usa:
  1) Split heurístico de texto a "líneas candidatas".
  2) Clasificación por LLM (JSON estricto) claim|data|reference + confidence 0..1.
  3) Reglas ligeras de verificación y deduplicado.
  4) Fallback heurístico si el LLM falla.

Requisitos:
  - python-pptx
  - openai>=1.0.0 (cliente nuevo)
  - pydantic

Variables de entorno:
  - OPENAI_API_KEY (obligatoria)
  - OPENAI_MODEL (opcional; por defecto 'gpt-4o-mini')

Uso rápido:
  from app.claims.llm_claim_extractor import extract_claims_from_pptx_llm
  claims = extract_claims_from_pptx_llm("claims_ppt_01.pptx", max_claims_per_slide=1)
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
import os, re, json, hashlib, time
from difflib import SequenceMatcher

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from pydantic import BaseModel, ValidationError, Field

# -------------------------- Utilidades base --------------------------

def _norm(txt: str) -> str:
    t = (txt or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def _split_candidates(text: str) -> List[str]:
    """
    Divide un cuadro de texto en frases "candidatas" a claim.
    Conservadora: tira lo muy corto/larguísimo y limpia bullets.
    """
    if not text:
        return []
    t = text.replace("•", "\n").replace("▪", "\n").replace("·", "\n").replace("●", "\n")
    # Partición por líneas y por punto+espacio (evitando abreviaturas típicas)
    raw = re.split(r"\n+|(?<=[^A-ZÁÉÍÓÚ0-9])\.\s+", t)
    out = []
    for chunk in raw:
        c = re.sub(r"\s+", " ", chunk).strip()
        c = re.sub(r"^\s*(claim|conclusión|conclusion)[:#\-\s]*", "", c, flags=re.I)
        if not c:
            continue
        if len(c) < 20:
            continue
        if len(c) > 300:
            continue
        out.append(c)
    return out

# Señales "de datos" (p-values, CI, %, n=, DOIs/PMIDs, métricas)
PAT_REF = re.compile(r"(pmid|doi|https?://|et al\.)", re.I)
PAT_P   = re.compile(r"\bp\s*([<=>]|=)\s*0?\.\d+\b", re.I)
PAT_CI  = re.compile(r"(ic\s*95%|95%\s*ci|ci\s*95%)", re.I)
PAT_N   = re.compile(r"\bn\s*=\s*\d+", re.I)
PAT_PCT = re.compile(r"\d{1,3}(\.\d+)?\s*%")
PAT_METRIC = re.compile(r"\b(hr|or|rr|sd|se|i2|i²|md)\b", re.I)

def _is_data_like(line: str) -> bool:
    return any(p.search(line) for p in (PAT_REF, PAT_P, PAT_CI, PAT_N, PAT_PCT, PAT_METRIC))

# -------------------------- Esquema de salida del LLM --------------------------

class LLMItem(BaseModel):
    index: int = Field(..., description="Índice del candidato en la lista de entrada")
    label: str = Field(..., description="Una de: claim | data | reference")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza 0..1")
    reason: str = Field(..., description="Razonamiento breve (≤ 25 palabras)")
    claim_text: str | None = Field(None, description="Texto del claim normalizado, si aplica")

class LLMResponse(BaseModel):
    items: List[LLMItem]

# -------------------------- Cliente OpenAI --------------------------

def _get_openai_client_and_model():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAI(api_key=api_key), model

def llm_classify_candidates(title: str, candidates: List[str], retries: int = 2) -> List[LLMItem]:
    """
    Envía hasta ~30 líneas candidatas de una slide al LLM en un único batch.
    Devuelve lista de LLMItem alineada por 'index'.
    """
    if not candidates:
        return []

    client, model = _get_openai_client_and_model()

    # Prompt compacto y normativo
    sys = (
        "Eres analista médico-regulatorio. Clasifica cada texto como:\n"
        "- 'claim': afirmación promocional o conclusiva (p.ej., superioridad, eficacia, seguridad, efecto clínico).\n"
        "- 'data': datos/soporte (p-valores, IC, porcentajes, tamaños muestrales, metodología, descripciones de estudio).\n"
        "- 'reference': citas, DOIs, URLs, 'et al.'\n"
        "Devuelve JSON estricto con 'items'. NO inventes, NO mezcles candidatos.\n"
        "Si 'label'='claim', rellena 'claim_text' con la frase resumida y clara (sin datos ni paréntesis).\n"
        "Usa confianza 0..1. Sé conservador: si dudas, no lo marques como claim."
    )

    user_payload = {
        "title": title or "",
        "candidates": [{"index": i, "text": c} for i, c in enumerate(candidates)]
    }

    # Few-shot mínimo dentro del prompt de usuario
    fewshot = {
        "examples": [
            {"text": "El tratamiento X reduce las exacerbaciones un 30% frente a placebo.", "label": "claim"},
            {"text": "p=0.03; HR=0.82 (IC95% 0.70–0.96).", "label": "data"},
            {"text": "García et al. 2021; doi:10.1000/xyz123", "label": "reference"},
            {"text": "X demostró no-inferioridad vs Y en control glucémico.", "label": "claim"},
        ]
    }

    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": json.dumps({"slide_title": title, **fewshot, **user_payload}, ensure_ascii=False)}
    ]

    for attempt in range(1 + retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            data = json.loads(raw)
            parsed = LLMResponse(**data)
            return parsed.items
        except Exception as e:
            if attempt >= retries:
                # último intento fallido -> devolvemos lista vacía (fallback arriba)
                return []
            time.sleep(0.5 * (attempt + 1))

# -------------------------- Pipeline por slide --------------------------

@dataclass
class ClaimHit:
    slide_index: int
    text: str
    score: float
    debug: Dict[str, Any]

def _dedupe(hits: List[ClaimHit], threshold: float = 0.90) -> List[ClaimHit]:
    out: List[ClaimHit] = []
    seen: set[str] = set()
    for h in sorted(hits, key=lambda x: x.score, reverse=True):
        n = _norm(h.text)
        hsh = hashlib.sha1(n.encode("utf-8")).hexdigest()
        if hsh in seen:
            continue
        if any(_similar(_norm(o.text), n) >= threshold for o in out):
            continue
        seen.add(hsh)
        out.append(h)
    return out

def _fallback_label(line: str) -> Tuple[str, float]:
    """
    Fallback muy simple: si huele a datos, 'data', si no, 'claim' bajito.
    """
    if _is_data_like(line):
        return "data", 0.25
    # pistas de claim (comparativos/verbos)
    if re.search(r"\b(reduce|reduces|mejora|improves|aumenta|increases|demuestra|demonstrates|superior|non[- ]?inferior)\b", _norm(line)):
        return "claim", 0.55
    return "data", 0.30

def process_slide(idx: int, slide, max_claims_per_slide: int) -> List[ClaimHit]:
    # título (ayuda contextual)
    try:
        title = slide.shapes.title.text or ""
    except Exception:
        title = ""

    # 1) Recolectar shapes textuales (sin tablas)
    shapes: List[Tuple[str, str, bool, bool]] = []
    for sh in slide.shapes:
        if getattr(sh, "has_table", False) and sh.has_table:
            continue
        if not getattr(sh, "has_text_frame", False):
            continue
        txt = (sh.text or "").strip()
        if not txt:
            continue
        is_title = is_body = False
        try:
            if getattr(sh, "is_placeholder", False):
                pht = sh.placeholder_format.type
                is_title = (pht == PP_PLACEHOLDER.TITLE)
                is_body  = (pht == PP_PLACEHOLDER.BODY)
        except Exception:
            pass
        shapes.append((txt, getattr(sh, "name", "") or "", is_title, is_body))

    # 2) Split a candidatos
    candidates: List[str] = []
    for txt, _, _, _ in shapes:
        candidates.extend(_split_candidates(txt))

    # 3) Clasificación por LLM en batch
    labeled: Dict[int, LLMItem] = {}
    if candidates:
        items = llm_classify_candidates(title, candidates) or []
        for it in items:
            if 0 <= it.index < len(candidates):
                labeled[it.index] = it

    # 4) Selección de CLAIMs
    hits: List[ClaimHit] = []
    for i, cand in enumerate(candidates):
        if i in labeled:
            it = labeled[i]
            lab = it.label.lower().strip()
            if lab == "claim":
                # verificación ligera: si el texto está repleto de números, baja la puntuación
                penalty = 0.0
                if _is_data_like(cand):
                    penalty = 0.15
                score = max(0.0, min(1.0, it.confidence - penalty))
                text_final = (it.claim_text or cand).strip()
                hits.append(ClaimHit(
                    slide_index=idx,
                    text=text_final,
                    score=score,
                    debug={"llm": it.model_dump(), "penalty_data_like": penalty, "original": cand, "slide_title": title}
                ))
        else:
            # Fallback si el LLM falló/timeout
            lab, conf = _fallback_label(cand)
            if lab == "claim":
                hits.append(ClaimHit(
                    slide_index=idx,
                    text=cand.strip(),
                    score=conf,
                    debug={"fallback": True, "original": cand, "slide_title": title}
                ))

    # 5) Ordenar por score y limitar por slide
    hits.sort(key=lambda h: (-h.score, h.text))
    if max_claims_per_slide > 0:
        hits = hits[:max_claims_per_slide]
    return hits

# -------------------------- API principal --------------------------

def extract_claims_from_pptx_llm(path: str,
                                 max_claims_per_slide: int = 1,
                                 global_dedupe: bool = True) -> List[Dict[str, Any]]:
    """
    Extrae claims con ayuda del LLM. Por defecto 1 claim/slide (ajústalo si tu deck trae varios).
    """
    prs = Presentation(path)
    all_hits: List[ClaimHit] = []
    for idx, slide in enumerate(prs.slides):
        all_hits.extend(process_slide(idx, slide, max_claims_per_slide=max_claims_per_slide))

    if global_dedupe:
        all_hits = _dedupe(all_hits, threshold=0.90)

    # Orden final estable
    all_hits.sort(key=lambda h: (h.slide_index, -h.score, h.text))
    return [asdict(h) for h in all_hits]


# -------------------------- CLI rápido (opcional) --------------------------

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx_path")
    ap.add_argument("--per_slide", type=int, default=1)
    args = ap.parse_args()

    res = extract_claims_from_pptx_llm(args.pptx_path, max_claims_per_slide=args.per_slide)
    print(json.dumps(res, ensure_ascii=False, indent=2))
