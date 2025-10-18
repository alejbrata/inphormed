class RAGService:
    """
    Servicio central que orquesta el flujo Retrieve → Augment → Generate.
    """
    def retrieve(self, query: str):
        print(f"🔎 Recuperando contexto para: {query}")
        # TODO: implementar búsqueda semántica
        return ["Documento A", "Documento B"]

    def augment(self, query: str, context: list):
        # TODO: combinar contexto y preparar prompt
        return f"Contexto: {context}\nPregunta: {query}"
