# app/llm/prompts.py

SYSTEM_PROMPT_ES = """Eres un verificador experto en materiales científicos para farma.
Recibirás un CLAIM (del PPT) y FRAGMENTOS RELEVANTES (del texto completo del paper).
Tu tarea: decidir si los fragmentos SOPORTAN, REFUTAN o son INSUFICIENTES para ese claim,
y devolver únicamente JSON válido según el esquema indicado, sin texto extra.
Sé estricto: si la evidencia no respalda población/indicador/outcome del claim, usa 'insufficient'.
Elige el MEJOR FRAGMENTO ('best_snippet') que justifique tu decisión.
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
    # --- ¡CAMBIO! ---
    # Ya no es 'paper_abstract_snips', ahora son los chunks
    relevant_chunks: str, 
) -> str:
    return f"""
CLAIM:
«{claim_texto}»

CONTEXT (del PPT):
Título de la slide: {slide_title}
Texto visible (extracto): {slide_text_excerpt}

CANDIDATE (fuente: {fuente}, id: {paper_id}):
Título: {paper_title}
Autores: {paper_authors}
Journal/Año: {journal} — {year}

FRAGMENTOS RELEVANTES (extraídos del texto completo): 
---
{relevant_chunks}
---

Instrucciones de decisión:
1) Evalúa si los FRAGMENTOS RELEVANTES respaldan el CLAIM.
2) 'score' en 0..1 (≥0.90 = match fuerte; 0.75–0.89 = probable; <0.75 = débil).
3) 'best_snippet' debe ser el texto del MEJOR FRAGMENTO que justifica tu decisión.

Devuelve SOLO un JSON con:
{{
  "verdict": "supports | refutes | insufficient",
  "score": 0.00,
  "confidence": 0.00,
  "why_short": "1-2 frases",
  "best_snippet": "La frase o párrafo exacto de 'FRAGMENTOS RELEVANTES' que usaste.",
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