"""
Lightweight Cross-Encoder Reranker for Legal RAG.
"""
import logging
import threading
from typing import Any, Optional

from rag.config import config

logger = logging.getLogger(__name__)

class LegalReranker:
    """
    Uses a Cross-Encoder to re-score candidate provisions for higher semantic precision.
    Uses class-level singleton cache to avoid duplicate reloading.
    """
    _model_cache: dict[str, Any] = {}
    _cache_lock: threading.Lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.reranker_model_name
        self._load_failed = False

    @property
    def model(self):
        if self.model_name not in self._model_cache and not self._load_failed:
            if not config.use_reranker:
                self._load_failed = True
                return None
            with self._cache_lock:
                if self.model_name not in self._model_cache:
                    try:
                        logger.info("Loading shared Cross-Encoder reranker: %s", self.model_name)
                        from sentence_transformers import CrossEncoder
                        self._model_cache[self.model_name] = CrossEncoder(self.model_name)
                    except Exception as e:
                        logger.warning("Failed to load Cross-Encoder %s: %s", self.model_name, e)
                        self._load_failed = True
        return self._model_cache.get(self.model_name)

    def rerank(self, query: str, results: list) -> list:
        """
        Rerank a list of RetrievalResult objects.
        Returns the list sorted by CrossEncoder score.
        """
        if not results:
            return results
        
        model = self.model
        if model is None:
            # Fallback to original scores
            return sorted(results, key=lambda x: x.score, reverse=True)

        # Prepare (query, document) pairs
        pairs = [[query, r.text] for r in results]
        
        try:
            scores = model.predict(pairs)
            for r, score in zip(results, scores):
                # We replace the cosine similarity score with the cross-encoder score
                r.score = float(score)
            
            # Sort descending by the new score
            return sorted(results, key=lambda x: x.score, reverse=True)
        except Exception as e:
            logger.error("Reranking failed: %s. Falling back to original scores.", e)
            return sorted(results, key=lambda x: x.score, reverse=True)
