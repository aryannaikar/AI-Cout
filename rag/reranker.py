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
        self.last_status: str = "not_run"

    @property
    def model(self):
        if self.model_name not in self._model_cache and not self._load_failed:
            if not config.use_reranker:
                self._load_failed = True
                self.last_status = "skipped_disabled"
                return None
            with self._cache_lock:
                if self.model_name not in self._model_cache:
                    try:
                        logger.info("Loading shared Cross-Encoder reranker: %s", self.model_name)
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

                        from sentence_transformers import CrossEncoder
                        self._model_cache[self.model_name] = CrossEncoder(self.model_name)
                    except Exception as e:
                        logger.warning("Failed to load Cross-Encoder %s: %s", self.model_name, e)
                        self._load_failed = True
                        self.last_status = "fallback_unavailable"
        return self._model_cache.get(self.model_name)

    def rerank(self, query: str, results: list) -> list:
        """
        Rerank a list of RetrievalResult objects.
        Records explicit reranker_status in each result's metadata.
        """
        if not results:
            self.last_status = "not_run"
            return results

        model = self.model
        if model is None:
            status = self.last_status if self.last_status in {"skipped_disabled", "fallback_unavailable"} else "fallback_unavailable"
            self.last_status = status
            for r in results:
                r.metadata["reranker_status"] = status
                r.metadata["reranker_model"] = self.model_name
            return sorted(results, key=lambda x: x.score, reverse=True)

        # Prepare (query, document) pairs
        pairs = [[query, r.text] for r in results]

        try:
            import math
            scores = model.predict(pairs)
            max_rrf = max((float(r.metadata.get("rrf_score", 0.0)) for r in results), default=0.0)
            self.last_status = "applied"
            for r, score in zip(results, scores):
                ce_raw = float(score)
                r.metadata["cross_encoder_score"] = ce_raw
                r.metadata["reranker_status"] = "applied"
                r.metadata["reranker_model"] = self.model_name
                if max_rrf > 0.0 and "rrf_score" in r.metadata:
                    # Blend normalized Cross-Encoder probability with normalized RRF consensus
                    ce_prob = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, ce_raw))))
                    rrf_norm = float(r.metadata["rrf_score"]) / max_rrf
                    r.score = 0.65 * ce_prob + 0.35 * rrf_norm
                else:
                    r.score = ce_raw

            # Sort descending by the new score
            return sorted(results, key=lambda x: x.score, reverse=True)
        except Exception as e:
            logger.error("Reranking failed: %s. Falling back to original scores.", e)
            self.last_status = "fallback_error"
            for r in results:
                r.metadata["reranker_status"] = "fallback_error"
                r.metadata["reranker_model"] = self.model_name
            return sorted(results, key=lambda x: x.score, reverse=True)
