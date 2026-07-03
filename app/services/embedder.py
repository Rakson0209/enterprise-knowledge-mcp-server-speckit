"""Dense embeddings via BGE-M3 (constitution: CPU-only, lazy-loaded, L2-normalized).

The heavy ``sentence_transformers`` import and model load happen lazily on first use so importing
this module (and running non-embedding tests) stays cheap and never triggers a model download.
"""

from __future__ import annotations

import threading
from functools import lru_cache

from app.config import get_settings


class Embedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _ensure(self) -> None:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    # device="cpu": target node (Zeabur Arm Ampere A1) has no GPU.
                    self._model = SentenceTransformer(self.model_name, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure()
        vectors = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
        return vectors.tolist()

    @property
    def dim(self) -> int:
        self._ensure()
        return self._model.get_sentence_embedding_dimension()


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(get_settings().embedding_model)
