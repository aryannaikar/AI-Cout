"""
Embedding model wrapper for Indian Legal RAG.
Configurable local SentenceTransformer embedding generator.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from rag.config import config

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    SentenceTransformer embedding wrapper with lazy loading, batching,
    and vector normalization for cosine similarity.
    Reuses a process-wide shared cached model instance to avoid duplicate reloading.
    """

    _model_cache: dict[tuple[str, Optional[str]], Any] = {}
    _cache_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or config.embedding_model_name
        self.device = device

    @property
    def model(self):
        """Thread-safe, shared cached SentenceTransformer model instance."""
        cache_key = (self.model_name, self.device)
        if cache_key not in self._model_cache:
            with self._cache_lock:
                if cache_key not in self._model_cache:
                    logger.info("Loading shared SentenceTransformer model: %s", self.model_name)
                    import importlib.machinery
                    import sys
                    from unittest.mock import MagicMock

                    try:
                        import torchvision  # noqa: F401
                    except Exception:
                        sys.modules["torchvision"] = None  # type: ignore[assignment]
                    try:
                        import pyarrow.dataset  # noqa: F401
                    except Exception:
                        ds_mod = MagicMock()
                        ds_mod.__spec__ = importlib.machinery.ModuleSpec("datasets", None)
                        ds_mod.__version__ = "0.0.0"
                        sys.modules["datasets"] = ds_mod

                    from sentence_transformers import SentenceTransformer

                    self._model_cache[cache_key] = SentenceTransformer(
                        model_name_or_path=self.model_name,
                        device=self.device,
                    )
        return self._model_cache[cache_key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached model instances (primarily for testing)."""
        with cls._cache_lock:
            cls._model_cache.clear()

    def encode(
        self,
        texts: list[str] | str,
        batch_size: Optional[int] = None,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> list[list[float]]:
        """
        Encode list of texts into dense vectors.

        Args:
            texts: Single string or list of strings.
            batch_size: Batch size for encoding.
            normalize_embeddings: If True, vectors have unit length (L2 norm = 1.0).
            show_progress_bar: Whether to display progress bar.

        Returns:
            List of float vectors.
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        bs = batch_size or config.embedding_batch_size
        embeddings = self.model.encode(
            texts,
            batch_size=bs,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=show_progress_bar,
        )

        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()
