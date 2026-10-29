from app.services.llm_service import LLMService
from app.schemas import BattleCardAnalysis
import json

class BattleCardService:
    def __init__(self):
        # Usamos gpt-4o para mayor capacidad de razonamiento crítico
        self.llm = LLMService(model="gpt-4o", temperature=0.0)

    def generate_competitor_analysis(self, paper_text: str) -> BattleCardAnalysis:
        system_prompt = """Eres un Director Médico Senior de una farmacéutica rival. Tu trabajo es encontrar CUALQUIER debilidad en este paper científico para proteger nuestra cuota de mercado.

Analiza el texto buscando activamente:
1. 'P-hacking' o manipulación estadística.
2. Criterios de exclusión que eliminan pacientes difíciles (Cherry picking).
3. Dosis sub-terapéuticas del fármaco comparador.
4. Endpoints primarios fallidos o cambiados a posteriori.

Sé cínico, técnico y directo. Tu salida debe ser munición pura para un debate científico.

Debes responder EXCLUSIVAMENTE con un objeto JSON válido que cumpla con este esquema:
{
  "study_design_flaws": ["lista de debilidades metodológicas"],
  "safety_signals": ["lista de efectos adversos minimizados"],
  "strategic_counter_arguments": ["frases cortas para rebatir"],
  "overall_threat_level": "Bajo" | "Medio" | "Alto"
}
"""

        # Truncar texto si es excesivo (aprox 100k chars para gpt-4o es seguro, pero por si acaso)
        max_chars = 100000
        truncated_text = paper_text[:max_chars] + "..." if len(paper_text) > max_chars else paper_text

        user_prompt = f"Analiza este paper clínico:\n\n{truncated_text}"

        data = self.llm.chat_with_json(system_prompt, user_prompt)
        
        if not data:
            raise ValueError("El LLM no generó una respuesta válida.")

        return BattleCardAnalysis(**data)
