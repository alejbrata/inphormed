import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.generation_agent import GenerationAgent

def test_one_pager_generation():
    print("Testing Executive One-Pager Generation...")

    # Mock LLM Service
    mock_llm = MagicMock()
    mock_llm.chat_with_json.return_value = {
        "title": "Estudio Clínico X",
        "main_insight": "El fármaco A reduce significativamente los síntomas en comparación con el placebo.",
        "key_stats": [
            {"value": "45%", "label": "Eficacia"},
            {"value": "N=500", "label": "Pacientes"},
            {"value": "p<0.01", "label": "Significancia"}
        ],
        "takeaways": [
            "Reducción del 45% en síntomas primarios.",
            "Perfil de seguridad comparable al placebo.",
            "Inicio de acción rápido (2 semanas).",
            "Mejora sostenida a largo plazo."
        ],
        "conclusion": "El fármaco A representa una opción terapéutica prometedora para pacientes con condición Y."
    }

    # Initialize Agent with Mock LLM
    agent = GenerationAgent()
    agent.llm = mock_llm

    # Generate Presentation
    try:
        pptx_bytes = agent.generate_presentation(
            text="Texto simulado del paper...",
            num_slides=1,
            image_paths=[],
            style="one_pager"
        )
        
        # Save to file to verify manually if needed (or just check if bytes are returned)
        output_path = "tests/test_one_pager.pptx"
        with open(output_path, "wb") as f:
            f.write(pptx_bytes)
            
        print(f"SUCCESS: One-Pager generated and saved to {output_path}")
        print(f"File size: {len(pptx_bytes)} bytes")
        
    except Exception as e:
        print(f"FAILURE: Error generating One-Pager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_one_pager_generation()
