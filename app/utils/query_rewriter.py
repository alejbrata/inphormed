# app/utils/query_rewriter.py
from __future__ import annotations

from typing import Optional, List, Dict, Any

# Soporta SDK nuevo y legacy sin romper
_OPENAI_CLIENT = None
def _get_openai_client(api_key: str):
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT
    try:
        # SDK >= 1.0
        from openai import OpenAI  # type: ignore
        _OPENAI_CLIENT = OpenAI(api_key=api_key)
        return _OPENAI_CLIENT
    except Exception:
        pass
    try:
        # SDK legacy
        import openai  # type: ignore
        openai.api_key = api_key
        _OPENAI_CLIENT = openai
        return _OPENAI_CLIENT
    except Exception:
        return None

from app.config.settings import settings


class QueryRewriter:
    """
    Reescribe una consulta/claim en un **query corto optimizado** para RAG/recuperación.
    - Multi-idioma: intenta generar consulta en INGLÉS (mejor para PubMed/CTGov/EMA).
    - Si no hay LLM disponible o `require_llm=False`, devuelve la query original.
    """

    def __init__(self, model: Optional[str] = None) -> None:
        self._model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self._used_model: Optional[str] = None

    def model_used(self) -> Optional[str]:
        return self._used_model

    def rewrite(self, query: str, require_llm: bool = True) -> str:
        q = (query or "").strip()
        if not q:
            return q

        # Si no exigimos LLM o no hay API key → sin reescritura
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not require_llm or not api_key:
            return q

        client = _get_openai_client(api_key)
        if client is None:
            return q

        prompt_sys = (
            "You are a query rewriter for biomedical retrieval. "
            "Rewrite the user's statement into a short, high-recall, boolean-style query in ENGLISH suitable "
            "for PubMed/ClinicalTrials/EMA search and vector retrieval. "
            "Prefer disease names, synonyms, drug names, endpoints, and core metrics. "
            "Output ONLY the rewritten query (one line), no quotes, no explanations."
        )
        user_msg = f"User statement:\n{q}\n\nReturn: one-line boolean-style query in English."

        try:
            # SDK nuevo
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": prompt_sys},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=120,
                )
                out = (resp.choices[0].message.content or "").strip()
                self._used_model = self._model
                return out or q

            # SDK legacy
            if hasattr(client, "ChatCompletion"):
                resp = client.ChatCompletion.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": prompt_sys},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=120,
                )
                out = (resp["choices"][0]["message"]["content"] or "").strip()
                self._used_model = self._model
                return out or q
        except Exception:
            # Cualquier fallo → query sin reescritura
            return q

        # Fallback conservador
        return q
