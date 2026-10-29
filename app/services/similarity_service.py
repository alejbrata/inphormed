from rapidfuzz import fuzz
from typing import Tuple

# Umbrales orientativos; luego ajustamos con casos reales
GREEN  = 86
YELLOW = 75

def similarity(a: str, b: str) -> Tuple[float, str]:
    """Devuelve (score 0-100, color)."""
    if not a or not b:
        return 0.0, "red"
    # token_set_ratio tolera reordenación y ruido
    score = fuzz.token_set_ratio(a, b)
    if score >= GREEN:
        color = "green"
    elif score >= YELLOW:
        color = "yellow"
    else:
        color = "red"
    return float(score), color
