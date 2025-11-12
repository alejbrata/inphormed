SYSTEM_PROMPT_ES = """Eres un verificador experto en materiales científicos para farma.
Recibirás un CLAIM (del PPT), su contexto (diapositiva) y un CANDIDATE (paper de PubMed u otras fuentes).
Tu tarea: decidir si el candidate SOPORTA, REFUTA o es INSUFICIENTE para ese claim,
y devolver únicamente JSON válido según el esquema indicado, sin texto extra.
No des pasos internos de razonamiento; limita 'why_short' a 1–2 frases.
Sé estricto: si la evidencia no respalda población/indicador/outcome del claim, usa 'insufficient'.
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
    paper_abstract_snips: str,
    paper_fulltext_snips: str,
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
Abstract (recortado a lo relevante): 
{paper_abstract_snips}

Si hay fulltext o tablas: 
{paper_fulltext_snips}

Instrucciones de decisión:
1) Evalúa correspondencia de población/indicación/intervención/outcome entre CLAIM y CANDIDATE.
2) Valora la fuerza del respaldo: metodología/resultados/conclusiones.
3) Evita "match por palabras": prioriza significado.
4) 'score' en 0..1 (≥0.90 = match fuerte; 0.75–0.89 = probable; <0.75 = débil).
5) 'confidence' es tu seguridad subjetiva (0..1).

Devuelve SOLO un JSON con:
{{
  "verdict": "supports | refutes | insufficient",
  "score": 0.00,
  "confidence": 0.00,
  "why_short": "1-2 frases",
  "evidence_quotes": [{{"source":"pubmed","section":"abstract","quote":"..."}}],
  "meta_alignment": {{
    "title_match": 0.0,
    "author_overlap": 0.0,
    "year_match": "exact|near|far|unknown",
    "population_match": 0.0,
    "outcome_match": 0.0
  }}
}}
""".strip()
