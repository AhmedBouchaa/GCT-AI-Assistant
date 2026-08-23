from typing import List, Optional

import numpy as np


class E5EmbeddingService:
    """Minimal wrapper around sentence-transformers with E5-style prefixes.

    Le modèle est défini par ``settings.embedding_model`` (source unique pour
    l'ingestion ET le retrieval) ; un ``model_name`` explicite reste possible.
    """

    def __init__(self, model_name: Optional[str] = None):
        if model_name is None:
            from app.core.config import settings

            model_name = settings.embedding_model
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: List[str], prefix: str = "passage:") -> np.ndarray:
        if not texts:
            return np.array([])

        prepared_texts = [f"{prefix}{text}" if prefix else text for text in texts]
        model = self._get_model()
        embeddings = model.encode(prepared_texts, normalize_embeddings=True, convert_to_numpy=True)
        return embeddings
