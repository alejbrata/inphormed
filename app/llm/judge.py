# app/llm/judge.py
from __future__ import annotations
import json
import os
from typing import Optional
from .prompts import SYSTEM_PROMPT_ES, build_user_prompt
from app.domain.core_models import CandidateDoc, Claim, SlideContext, JudgeResult

# --- ¡CAMBIO! Importamos nuestro servicio ---
from app.services.llm_service import LLMService, LLMServiceError

class LLMJudge:
    def __init__(self,
                 model: Optional[str] = None,
                 temperature: float = 0.2,
                 mock: bool = False):
        self.temperature = temperature
        self.model_name = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.mock = mock or (os.getenv("MOCK_LLM_JUDGE", "0") == "1")
        
        # --- ¡CAMBIO! Creamos el cliente de nuestro servicio ---
        # Pasamos el modelo y temperatura específicos para el Juez
        self.llm_service = LLMService(model=self.model_name, temperature=self.temperature)

    def decide(self, claim: Claim, slide: SlideContext, cand: CandidateDoc) -> JudgeResult:
        if self.mock:
            # (Lógica de mock se queda igual)
            score = 0.93 if "hidradenitis" in (cand.title + cand.abstract_snippets).lower() else 0.62
            verdict = "supports" if score >= 0.9 else "insufficient"
            return JudgeResult(
                verdict=verdict,
                score=score,
                confidence=0.9 if score >= 0.9 else 0.7,
                why_short="Coincide población y outcome principal según el abstract resumido.",
                evidence_quotes=[{"source": cand.source, "section": "abstract", "quote": cand.abstract_snippets[:180]}],
                meta_alignment={"title_match": 0.9, "author_overlap": 0.5, "year_match": "near",
                                "population_match": 0.85, "outcome_match": 0.9},
            )

        # --- ¡CAMBIO! ---
        # Ya no creamos un cliente, usamos el servicio
        
        user_prompt = build_user_prompt(
            claim_texto=claim.text,
            slide_title=slide.title,
            slide_text_excerpt=slide.excerpt,
            fuente=cand.source,
            paper_id=cand.id,
            paper_title=cand.title,
            paper_authors=", ".join(cand.authors or []),
            journal=cand.journal or "",
            year=str(cand.year or ""),
            paper_abstract_snips=cand.abstract_snippets,
            paper_fulltext_snips=cand.fulltext_snippets
        )
        
        try:
            # ¡Llamada al "USB"!
            data = self.llm_service.chat_with_json(
                system_prompt=SYSTEM_PROMPT_ES,
                user_prompt=user_prompt
            )
            if data is None:
                raise LLMServiceError("El servicio LLM devolvió None")
                
            return JudgeResult(**data)
            
        except (LLMServiceError, Exception) as e:
            # Fallback si el LLM falla o el JSON es inválido
            print(f"Error en LLMService (Judge): {e}")
            return JudgeResult(
                verdict="insufficient",
                score=0.0,
                confidence=0.0,
                why_short=f"Fallo del LLM: {e}",
                evidence_quotes=[],
                meta_alignment={"title_match": 0.0, "author_overlap": 0.0, "year_match": "unknown",
                                "population_match": 0.0, "outcome_match": 0.0},
            )