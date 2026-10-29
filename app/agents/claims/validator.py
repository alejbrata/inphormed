# app/agents/claims/validator.py
from __future__ import annotations

from typing import List, Optional, Any, Dict
import math

# Soporta SDK nuevo y legacy sin romper
_OPENAI_CLIENT = None
def _get_openai_client(api_key: str):
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT
    try:
        from openai import OpenAI  # type: ignore
        _OPENAI_CLIENT = OpenAI(api_key=api_key)
        return _OPENAI_CLIENT
    except Exception:
        pass
    try:
        import openai  # type: ignore
        openai.api_key = api_key
        _OPENAI_CLIENT = openai
        return _OPENAI_CLIENT
    except Exception:
        return None

from app.config.settings import settings
from app.schemas import Citation, ValidationResult, ComplianceResult


def _best_score(citations: List[Citation]) -> float:
    vals = [float(c.score) for c in citations if isinstance(getattr(c, "score", None), (int, float))]
    return max(vals) if vals else 0.0


class ClaimsValidator:
    """
    Valida un claim usando:
    - Heurística por score de recuperación (umbral verde/amarillo).
    - (Opcional) LLM para explicación y veredicto más fino.
    Incluye un checker mínimo de compliance.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        thr_green: float = 0.82,
        thr_yellow: float = 0.70,
    ) -> None:
        self._model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self._thr_green = thr_green
        self._thr_yellow = thr_yellow
        self._used_model: Optional[str] = None

    def model_used(self) -> Optional[str]:
        return self._used_model

    # ------------------- VALIDACIÓN -------------------
    def validate(
        self,
        *,
        claim: str,
        citations: List[Citation],
        generated_text: str,
        require_llm: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:

        md = metadata or {}
        thr_g = float(md.get("thr_green", self._thr_green))
        thr_y = float(md.get("thr_yellow", self._thr_yellow))
        if thr_g < thr_y:
            thr_g, thr_y = self._thr_green, self._thr_yellow  # sanea si vienen mal

        # Heurística base por score
        best = _best_score(citations)
        base_label = "RED"
        if best >= thr_g:
            base_label = "GREEN"
        elif best >= thr_y:
            base_label = "YELLOW"

        # Si no hay API key o no queremos LLM, devolvemos heurístico
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not require_llm or not api_key:
            top_url = None
            if citations:
                top_url = next((c.url for c in sorted(citations, key=lambda x: (x.score or 0.0), reverse=True) if c.url), None)
            return ValidationResult(
                label=base_label,
                explanation=f"Heurística por score (best={best:.3f} / green≥{thr_g:.2f} / yellow≥{thr_y:.2f}).",
                top_url=top_url,
                citations=citations[:3],
            )

        client = _get_openai_client(api_key)
        if client is None:
            # Fallback sin LLM
            top_url = None
            if citations:
                top_url = next((c.url for c in sorted(citations, key=lambda x: (x.score or 0.0), reverse=True) if c.url), None)
            return ValidationResult(
                label=base_label,
                explanation=f"Heurística por score (best={best:.3f}).",
                top_url=top_url,
                citations=citations[:3],
            )

        # Prepara contexto breve con las mejores citas
        top = sorted(citations, key=lambda c: (c.score or 0.0), reverse=True)[:3]
        ctx_lines = []
        for i, c in enumerate(top, 1):
            ctx_lines.append(f"[{i}] {c.title or ''} — {c.url or ''}")

        sys = (
            "You are a scientific claims validator. Decide if the claim is supported by the given citations. "
            "Return one of GREEN (supported), YELLOW (partially/uncertain), RED (unsupported). "
            "Be concise and avoid hallucinations."
        )
        user = (
            f"CLAIM:\n{claim}\n\n"
            f"CITATIONS (top-{len(top)}):\n" + "\n".join(ctx_lines) + "\n\n"
            "Answer in JSON with fields: label (GREEN|YELLOW|RED), explanation (1-3 sentences), top_url (one of the citations' URLs or null)."
        )

        label = base_label
        explanation = f"Heuristic label={base_label} (best={best:.3f})."
        top_url = next((c.url for c in top if c.url), None)

        try:
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                    temperature=0.1,
                    max_tokens=200,
                    response_format={"type": "json_object"} if hasattr(client.chat.completions, "create") else None,
                )
                txt = (resp.choices[0].message.content or "").strip()
                self._used_model = self._model
            elif hasattr(client, "ChatCompletion"):
                resp = client.ChatCompletion.create(
                    model=self._model,
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                    temperature=0.1,
                    max_tokens=200,
                )
                txt = (resp["choices"][0]["message"]["content"] or "").strip()
                self._used_model = self._model
            else:
                txt = ""
        except Exception:
            txt = ""

        # Intenta parsear JSON simple
        if txt:
            import json
            try:
                data = json.loads(txt)
                _lbl = str(data.get("label", "")).upper().strip()
                if _lbl in ("GREEN", "YELLOW", "RED"):
                    label = _lbl
                explanation = str(data.get("explanation", explanation))[:800]
                _top = data.get("top_url")
                if isinstance(_top, str) and _top:
                    top_url = _top
            except Exception:
                # si no es JSON, mantenemos heurística/LMM mix anterior
                pass

        return ValidationResult(
            label=label,
            explanation=explanation,
            top_url=top_url,
            citations=top,
        )

    # ------------------- COMPLIANCE -------------------
    def compliance_for(self, text: str, citations: List[Citation]) -> ComplianceResult:
        """
        Checker mínimo:
        - Sin citas → penaliza fuerte.
        - Si hay comparativos absolutos ('el mejor', 'cura', '100%') sin contexto → penaliza.
        - Si hay 'puede', 'podría', 'en estudio' → suaviza.
        """
        t = (text or "").lower()
        issues: List[str] = []

        has_cites = len([c for c in citations if c.url or c.doc_hash]) > 0
        if not has_cites:
            issues.append("No se proporcionan citas trazables para el claim/material.")

        absolutos = ["cura", "curación", "el mejor", "100%", "sin riesgo", "garantizado", "definitivo"]
        if any(k in t for k in absolutos):
            issues.append("Lenguaje absoluto/no permitido (p.ej., 'cura', '100%', 'el mejor').")

        comparativos = ["mejor que", "superior a", "más eficaz que", "reduce un", "incrementa un"]
        if any(k in t for k in comparativos) and not has_cites:
            issues.append("Comparativa sin citar evidencia.")

        suavizantes = ["puede", "podría", "podrían", "en estudio", "sugiere", "preliminar"]
        soft = any(k in t for k in suavizantes)

        base = 85.0 if has_cites else 40.0
        if issues:
            base -= 20.0 * len(issues)
        if soft:
            base += 5.0

        score = max(0.0, min(100.0, base))
        passed = score >= 60.0 and not (not has_cites)

        return ComplianceResult(
            score=round(score, 1),
            passed=bool(passed),
            issues=issues or None,
        )
