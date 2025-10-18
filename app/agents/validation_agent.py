class ValidationAgent:
    """
    Agente responsable de validar claims científicos mediante RAG.
    """
    def validate_claim(self, claim_text: str):
        print(f"🔍 Validando claim: {claim_text}")
        # TODO: integrar RAG y evaluación de groundedness
        return {"claim": claim_text, "valid": True, "score": 0.95}
