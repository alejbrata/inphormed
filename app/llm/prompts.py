# app/llm/prompts.py

SYSTEM_PROMPT_ES = """Eres un auditor estricto de cumplimiento científico (Medical Compliance).
Tu ÚNICA fuente de verdad son los FRAGMENTOS RELEVANTES proporcionados.
NO uses tu conocimiento previo sobre el estudio, el fármaco o los autores.

Reglas de Oro:
0. RELEVANCIA TEMÁTICA: Si el CLAIM habla de un fármaco (ej: Secukinumab) y el TEXTO habla de otra cosa (ej: Monkeypox), el veredicto ES 'insufficient' y score 0.0.
1. Si la información del CLAIM no aparece explícitamente en los FRAGMENTOS, el veredicto ES 'insufficient'.
2. No asumas que el claim es cierto porque "suena correcto" o porque conoces el estudio. Si no está en el texto provisto, NO EXISTE.
3. Para dar GREEN (supports), el texto debe respaldar el claim sin ambigüedad.

Tu tarea: decidir si los fragmentos SOPORTAN, REFUTAN o son INSUFICIENTES para ese claim.
Devuelve únicamente JSON válido.
"""

def build_user_prompt(
    claim_texto: str,
    slide_title: str,
    slide_text_excerpt: str,
    fuente: str,
    paper_id: str,
    paper_title: str,
    paper_authors: str,
    journal: str,
    year: str,
    relevant_chunks: str, 
) -> str:
    return f"""
CLAIM A VERIFICAR:
«{claim_texto}»

CONTEXTO DEL DOCUMENTO (PPT):
Título: {slide_title}
Texto: {slide_text_excerpt}

EVIDENCIA DISPONIBLE (Exclusivamente estos fragmentos):
---
{relevant_chunks}
---

Metadatos de la fuente: {paper_title} ({journal}, {year})

Instrucciones de Decisión:
1. Busca la frase o dato exacto del CLAIM dentro de EVIDENCIA DISPONIBLE.
2. Si el CLAIM menciona datos específicos (ej: "633 pacientes", "41.8%") y esos números NO están en la EVIDENCIA: devuelve 'insufficient'.
3. 'best_snippet': Debe ser una copia EXACTA del texto encontrado en EVIDENCIA. Si no lo encuentras, déjalo vacío.

Devuelve SOLO un JSON con:
{{
  "verdict": "supports | refutes | insufficient",
  "score": 0.00,
  "confidence": 0.00,
  "why_short": "Explica por qué (ej: 'El dato 633 no aparece en el texto disponible').",
  "best_snippet": "Texto exacto copiado de los fragmentos (o null si no está).",
  "evidence_quotes": [{{"source":"pubmed","section":"fulltext","quote":"..."}}],
  "meta_alignment": {{
    "title_match": 0.0,
    "author_overlap": 0.0,
    "year_match": "exact|near|far|unknown",
    "population_match": 0.0,
    "outcome_match": 0.0
  }}
}}
""".strip()