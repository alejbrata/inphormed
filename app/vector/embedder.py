from __future__ import annotations
import os
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer

@dataclass
class EmbedderMiniLM:
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    _model: SentenceTransformer | None = None
    dim: int = 384

    def _ensure(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        model = self._ensure()
        X = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        if X.shape[1] != self.dim:
            raise ValueError(f"Dimensión inesperada: {X.shape[1]} (esperada {self.dim})")
        return X
