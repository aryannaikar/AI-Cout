"""
Stage-0 Classical ML Intake Classifier (TF-IDF + Linear SGD/SVM).
Provides fast (<10ms) pre-trial case-type classification ('CRL', 'CRA', 'CRM',
'BA', 'REV', 'WP', 'FA', etc.) trained on Indian High Court decisions without
modifying Phase 5 judgment evaluation logic.
"""

from __future__ import annotations

import logging
import threading
import warnings
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "models" / "legal_case_type_classifier.joblib"

_CASE_TYPE_TO_PROCEEDING: dict[str, tuple[str, str]] = {
    "BA": ("bail", "Bail Application"),
    "CRA": ("appeal", "Criminal Appeal"),
    "CRL": ("appeal", "Criminal Petition / Appeal"),
    "CRM": ("other", "Criminal Miscellaneous"),
    "MCRC": ("bail", "Misc. Criminal Case"),
    "REV": ("revision", "Criminal Revision"),
    "WP": ("other", "Writ Petition (Civil/Constitutional)"),
    "CWP": ("other", "Civil Writ Petition"),
    "FA": ("appeal", "First Appeal (Civil)"),
    "SA": ("appeal", "Second Appeal (Civil)"),
    "RSA": ("appeal", "Regular Second Appeal (Civil)"),
    "SCA": ("other", "Special Civil Application"),
}


class MLCaseTypeClassifier:
    """Thread-safe lazy wrapper around legal_case_type_classifier.joblib."""

    _model: Any = None
    _load_attempted: bool = False
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_model(cls) -> Any:
        if cls._model is None and not cls._load_attempted:
            with cls._lock:
                if cls._model is None and not cls._load_attempted:
                    cls._load_attempted = True
                    if _DEFAULT_MODEL_PATH.exists():
                        try:
                            import joblib
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                cls._model = joblib.load(_DEFAULT_MODEL_PATH)
                            logger.info("Loaded Stage-0 ML case classifier from '%s'", _DEFAULT_MODEL_PATH)
                        except Exception as exc:
                            logger.warning("Could not load ML case classifier: %s", exc)
                    else:
                        logger.debug("ML case classifier file not found at '%s'", _DEFAULT_MODEL_PATH)
        return cls._model

    @classmethod
    def classify_text(cls, text: str, top_n: int = 3) -> Optional[dict[str, Any]]:
        """Return predicted case_type, human label, proceeding hint, and top-N scores."""
        if not text or not text.strip():
            return None
        model = cls._get_model()
        if model is None:
            return None
        try:
            import numpy as np
            pred = str(model.predict([text])[0])
            scores = np.asarray(model.decision_function([text]))
            classes = list(model.classes_)
            if scores.ndim > 1:
                scores = scores[0]
            scores_flat = [float(s) for s in scores.reshape(-1)]
            ranked = sorted(zip(classes, scores_flat), key=lambda kv: kv[1], reverse=True)[:top_n]
            proc_hint, label_desc = _CASE_TYPE_TO_PROCEEDING.get(pred, ("other", pred))
            return {
                "case_type": pred,
                "label_description": label_desc,
                "proceeding_hint": proc_hint,
                "top_predictions": [f"{lbl} ({val:+.3f})" for lbl, val in ranked],
            }
        except Exception as exc:
            logger.debug("ML case classifier prediction skipped: %s", exc)
            return None
