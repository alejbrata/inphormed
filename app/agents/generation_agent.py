class GenerationAgent:
    """
    Agente generador de materiales o resúmenes a partir de evidencias validadas.
    """
    def generate_material(self, topic: str):
        print(f"🧠 Generando material sobre: {topic}")
        # TODO: implementar generación controlada (GPT / Azure)
        return {"topic": topic, "content": "Resumen generado."}
