# app/llm/judge.py
from __future__ import annotations
import json
import os
import re
from typing import Optional, List
from .prompts import SYSTEM_PROMPT_ES, build_user_prompt
from app.domain.core_models import CandidateDoc, Claim, SlideContext, JudgeResult
from app.services.llm_service import LLMService, LLMServiceError

# --- ¡NUEVO! Helper para RAG "On-the-fly" ---
def _simple_chunker(text: str, min_length: int = 150) -> List[str]:
    """Divide el texto por párrafos (saltos de línea dobles) o frases largas."""
    if not text:
        return []
    # Dividir por párrafos
    chunks = re.split(r'\n\s*\n', text)
    final_chunks = []
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) >= min_length:
            final_chunks.append(chunk)
    
    # Si no hay chunks (ej. un abstract sin saltos), dividir por frases
    if not final_chunks and len(text) > min_length:
        # Split por puntos seguidos de espacio
        chunks = re.split(r'(?<=\.)\s+', text)
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) >= min_length:
                final_chunks.append(chunk)
                
    return final_chunks if final_chunks else [text] # Fallback al texto completo

def _find_best_chunks(claim_text: str, full_text: str, top_k: int = 3) -> List[str]:
    """
    Un RAG "tonto" (sin vectores): trocea y busca por palabras clave.
    """
    claim_words = set(re.findall(r'\b\w{4,}\b', claim_text.lower()))
    if not claim_words:
        return []

    chunks = _simple_chunker(full_text)
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for word in claim_words if word in chunk_lower)
        if score > 0:
            scored_chunks.append((score, chunk))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:top_k]]
# --- FIN DE LOS HELPERS DE RAG ---


class LLMJudge:
    def __init__(self,
                 model: Optional[str] = None,
                 temperature: float = 0.2,
                 mock: bool = False):
        self.temperature = temperature
        self.model_name = model or os.getenv("LLM_JUDGE_MODEL", "gpt-4o-mini") # Modelo Juez
        self.mock = mock or (os.getenv("MOCK_LLM_JUDGE", "0") == "1")
        
        self.llm_service = LLMService(model=self.model_name, temperature=self.temperature)

    def decide(self, claim: Claim, slide: SlideContext, cand: CandidateDoc) -> JudgeResult:
        if self.mock:
            # (Lógica de mock se queda igual)
            score = 0.93
            verdict = "supports"
            snippet = cand.abstract or "Snippet de mock"
            return JudgeResult(
                verdict=verdict,
                score=score,
                confidence=0.9,
                why_short="Coincide población y outcome (Mock).",
                best_snippet=snippet,
                evidence_quotes=[{"source": cand.source, "section": "abstract", "quote": snippet[:180]}],
                meta_alignment={"title_match": 0.9, "author_overlap": 0.5, "year_match": "near",
                                "population_match": 0.85, "outcome_match": 0.9},
            )

        # --- ¡CAMBIO! Lógica de RAG On-the-fly ---
        
        # 1. ¿Tenemos texto completo?
        text_to_search = cand.full_text_content
        search_source = "fulltext"
        
        # 2. Si no hay texto completo (no era PMC), usamos el abstract
        if not text_to_search:
            text_to_search = cand.abstract
            search_source = "abstract"

        if not text_to_search:
             # No tenemos NADA contra lo que validar
            return self._fallback_failure("No se pudo descargar ni abstract ni texto completo.")

        # 3. RAG: Encontrar los mejores chunks
        best_chunks = _find_best_chunks(claim.text, text_to_search, top_k=3)
        
        if not best_chunks:
            # No se encontraron chunks relevantes
            best_chunks = [text_to_search[:2000]] # Usar el inicio del texto

        relevant_chunks_str = "\n\n---\n\n".join(best_chunks)
        # --- FIN DE LA LÓGICA RAG ---

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
            relevant_chunks=relevant_chunks_str # Pasamos los chunks al prompt
        )
        
        try:
            data = self.llm_service.chat_with_json(
                system_prompt=SYSTEM_PROMPT_ES,
                user_prompt=user_prompt
            )
            if data is None:
                raise LLMServiceError("El servicio LLM devolvió None")
                
            # Asegurarnos de que el snippet está en el resultado
            if "best_snippet" not in data:
                data["best_snippet"] = best_chunks[0] # Fallback
            
            # Asegurar que la cita es correcta
            data["evidence_quotes"] = [{"source": cand.source, "section": search_source, "quote": data["best_snippet"][:300]}]
                
            return JudgeResult(**data)
            
        except (LLMServiceError, Exception) as e:
            return self._fallback_failure(f"Fallo del LLM: {e}")

    def _fallback_failure(self, error_msg: str) -> JudgeResult:
        """Devuelve un resultado de fallo estándar."""
        print(f"Error en LLMService (Judge): {error_msg}")
        return JudgeResult(
            verdict="insufficient",
            score=0.0,
            confidence=0.0,
            why_short=error_msg,
            best_snippet=None,
            evidence_quotes=[],
            meta_alignment={"title_match": 0.0, "author_overlap": 0.0, "year_match": "unknown",
                            "population_match": 0.0, "outcome_match": 0.0},
        )