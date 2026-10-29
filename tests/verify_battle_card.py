import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.services.battle_card_service import BattleCardService
from app.schemas import BattleCardAnalysis

# Dummy clinical text with obvious flaws
dummy_text = """
We conducted a randomized controlled trial to compare Drug X with Placebo in 50 patients with mild hypertension.
The study duration was 2 weeks.
Drug X showed a significant reduction in blood pressure (p=0.049).
Patients with history of cardiovascular events were excluded.
Adverse events were not systematically recorded but some patients reported dizziness.
"""

def test_battle_card_generation():
    print("Initializing BattleCardService...")
    service = BattleCardService()
    
    print("Generating analysis...")
    try:
        analysis = service.generate_competitor_analysis(dummy_text)
        
        print("\n--- Analysis Result ---")
        print(f"Threat Level: {analysis.overall_threat_level}")
        print("\nDesign Flaws:")
        for flaw in analysis.study_design_flaws:
            print(f"- {flaw}")
            
        print("\nSafety Signals:")
        for signal in analysis.safety_signals:
            print(f"- {signal}")
            
        print("\nCounter Arguments:")
        for arg in analysis.strategic_counter_arguments:
            print(f"- {arg}")
            
        assert isinstance(analysis, BattleCardAnalysis)
        print("\n✅ Verification Successful!")
        
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")

if __name__ == "__main__":
    test_battle_card_generation()
