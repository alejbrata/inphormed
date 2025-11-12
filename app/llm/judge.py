from __future__ import annotations
import json
import os
from typing import Optional
from .prompts import SYSTEM_PROMPT_ES, build_user_prompt
from app.domain.core_models import CandidateDoc, Claim, SlideContext, JudgeResult

class LLMJudge:
    def __init__(self,
                 model: Optional[str] = None,
                 temperature: float = 0.2,
                 mock: bool = False):
        self.temperature = temperature
        self.model = model or os.getenv("LLM_MODEL", "gpt-4.1")
        self.mock = mock or (os.getenv("MOCK_LLM_JUDGE", "0") == "1")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            base_url = os.getenv("OPENAI_BASE_URL")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY no configurada.")
            if base_url:
                self._client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self._client = OpenAI(api_key=api_key)
        return self._client

    def decide(self, claim: Claim, slide: SlideContext, cand: CandidateDoc) -> JudgeResult:
        if self.mock:
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

        client = self._get_client()
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
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ES},
                {"role": "user", "content": user_prompt},
            ],
        )
        payload = resp.choices[0].message.content
        data = json.loads(payload)
        return JudgeResult(**data)
