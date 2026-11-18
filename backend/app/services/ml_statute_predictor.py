"""
Stage-0 Classical ML Statutory & Companion-Section Predictor
(TF-IDF + OneVsRest LogisticRegression trained on Supreme Court decisions).
Provides fast (<10ms) multi-label prediction of applicable penal, evidentiary,
and procedural provisions without mutating Phase 5 judgment evaluation logic.
"""

from __future__ import annotations

import logging
import threading
import warnings
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "models"
    / "statutory_section_predictor.joblib"
)

# code -> (act_name, short_name, section, label, search_key, historical_only, requires_any)
_SECTION_METADATA: dict[str, tuple[str, str, str, str, str, bool, tuple[str, ...]]] = {
    "IPC_302": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 302",
        "Section 302 IPC",
        "302",
        True,
        ("302", "murder", "homicide", "deceased", "killed", "post-mortem", "post mortem", "autopsy", "dead body", "fatal"),
    ),
    "IPC_304": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 304",
        "Section 304 IPC",
        "304",
        True,
        ("304", "culpable homicide", "deceased", "death"),
    ),
    "IPC_307": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 307",
        "Section 307 IPC",
        "307",
        True,
        ("307", "attempt to murder", "attempted murder", "gunshot", "stabbed"),
    ),
    "IPC_323": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 323",
        "Section 323 IPC",
        "323",
        True,
        ("323", "hurt", "assault", "beaten", "injury"),
    ),
    "IPC_324": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 324",
        "Section 324 IPC",
        "324",
        True,
        ("324", "dangerous weapon", "sharp", "knife", "incised", "sword", "rod"),
    ),
    "IPC_325": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 325",
        "Section 325 IPC",
        "325",
        True,
        ("325", "grievous hurt", "fracture"),
    ),
    "IPC_326": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 326",
        "Section 326 IPC",
        "326",
        True,
        ("326", "grievous hurt", "acid", "dangerous weapon"),
    ),
    "IPC_376": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 376",
        "Section 376 IPC",
        "376",
        True,
        ("376", "rape", "sexual assault", "prosecutrix"),
    ),
    "IPC_379": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 379",
        "Section 379 IPC",
        "379",
        True,
        ("379", "411", "theft", "stolen", "dishonestly taking"),
    ),
    "IPC_392": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 392",
        "Section 392 IPC",
        "392",
        True,
        ("392", "robbery", "looted", "snatched"),
    ),
    "IPC_395": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 395",
        "Section 395 IPC",
        "395",
        True,
        ("395", "412", "dacoity"),
    ),
    "IPC_397": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 397",
        "Section 397 IPC",
        "397",
        True,
        ("397", "robbery", "dacoity", "deadly weapon"),
    ),
    "IPC_411": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 411",
        "Section 411 IPC",
        "411",
        True,
        ("411", "379", "stolen property", "receiving stolen", "scrap", "recovered property"),
    ),
    "IPC_420": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 420",
        "Section 420 IPC",
        "420",
        True,
        ("420", "cheating", "fraud", "dishonestly inducing", "forged", "forgery", "loan", "bank"),
    ),
    "IPC_467": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 467",
        "Section 467 IPC",
        "467",
        True,
        ("467", "forgery", "forged", "valuable security", "will"),
    ),
    "IPC_468": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 468",
        "Section 468 IPC",
        "468",
        True,
        ("468", "420", "forgery", "forged", "fabricated", "cheating"),
    ),
    "IPC_471": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 471",
        "Section 471 IPC",
        "471",
        True,
        ("471", "468", "forgery", "forged", "fabricated", "genuine"),
    ),
    "IPC_34": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 34",
        "Section 34 IPC",
        "section 34",
        True,
        (),
    ),
    "IPC_120B": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 120B",
        "Section 120B IPC",
        "120b",
        True,
        ("120b", "conspiracy", "conspired", "cheating", "forged", "420"),
    ),
    "IPC_147": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 147",
        "Section 147 IPC",
        "147",
        True,
        ("147", "rioting", "unlawful assembly", "mob"),
    ),
    "IPC_148": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 148",
        "Section 148 IPC",
        "148",
        True,
        ("148", "rioting", "armed with deadly"),
    ),
    "IPC_149": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 149",
        "Section 149 IPC",
        "149",
        True,
        ("149", "unlawful assembly", "common object"),
    ),
    "IPC_201": (
        "Indian Penal Code, 1860",
        "IPC",
        "Section 201",
        "Section 201 IPC",
        "201",
        True,
        ("201", "disappearance of evidence", "destroyed evidence", "concealed body"),
    ),
    "IEA_27": (
        "Indian Evidence Act, 1872",
        "IEA",
        "Section 27",
        "Section 27 IEA",
        "27",
        True,
        ("27", "disclosure", "custody", "recovery", "confess", "seizure", "recovered"),
    ),
    "IEA_32": (
        "Indian Evidence Act, 1872",
        "IEA",
        "Section 32",
        "Section 32 IEA",
        "32",
        True,
        ("32", "dying declaration"),
    ),
    "IEA_102": (
        "Indian Evidence Act, 1872",
        "IEA",
        "Section 102",
        "Section 102 IEA",
        "102",
        True,
        (),
    ),
    "IEA_106": (
        "Indian Evidence Act, 1872",
        "IEA",
        "Section 106",
        "Section 106 IEA",
        "106",
        True,
        ("106", "especially within knowledge", "last seen", "custody", "explanation"),
    ),
    "IEA_114": (
        "Indian Evidence Act, 1872",
        "IEA",
        "Section 114",
        "Section 114 IEA",
        "114",
        True,
        ("114", "presum", "stolen", "possession", "recovery", "independent", "379", "411", "3(a)"),
    ),
    "CRPC_100": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 100",
        "Section 100 CrPC",
        "100",
        True,
        ("100", "search", "seizure", "independent", "panch", "recovery", "godown", "memo"),
    ),
    "CRPC_154": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 154",
        "Section 154 CrPC",
        "154",
        True,
        ("154", "fir", "first information report", "delay"),
    ),
    "CRPC_164": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 164",
        "Section 164 CrPC",
        "164",
        True,
        ("164", "magistrate", "confession"),
    ),
    "CRPC_313": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 313",
        "Section 313 CrPC",
        "313",
        True,
        ("313", "examination of accused", "statement of accused"),
    ),
    "CRPC_439": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 439",
        "Section 439 CrPC",
        "439",
        True,
        ("439", "bail"),
    ),
    "CRPC_482": (
        "Code of Criminal Procedure, 1973",
        "CrPC",
        "Section 482",
        "Section 482 CrPC",
        "482",
        True,
        ("482", "quash"),
    ),
    "ARMS_25": (
        "Arms Act, 1959",
        "Arms_Act",
        "Section 25",
        "Section 25 Arms Act",
        "25",
        False,
        ("arms act", "pistol", "firearm", "katta", "revolver", "cartridge", "ammunition", "unlicensed"),
    ),
    "ARMS_27": (
        "Arms Act, 1959",
        "Arms_Act",
        "Section 27",
        "Section 27 Arms Act",
        "27",
        False,
        ("arms act", "pistol", "firearm"),
    ),
    "ARMS_39": (
        "Arms Act, 1959",
        "Arms_Act",
        "Section 39",
        "Section 39 Arms Act",
        "39",
        False,
        ("arms act", "sanction", "pistol", "firearm"),
    ),
    "NDPS_20": (
        "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "NDPS",
        "Section 20",
        "Section 20 NDPS Act",
        "20",
        False,
        ("ndps", "ganja", "charas", "cannabis"),
    ),
    "NDPS_21": (
        "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "NDPS",
        "Section 21",
        "Section 21 NDPS Act",
        "21",
        False,
        ("ndps", "heroin", "smack", "psychotropic", "contraband"),
    ),
}


def _build_entry(code: str, prob: float) -> Optional[dict[str, Any]]:
    meta = _SECTION_METADATA.get(code)
    if meta is None:
        return None
    act_name, short_name, section, label, search_key, historical_only, _ = meta
    return {
        "code": code,
        "label": label,
        "act_name": act_name,
        "short_name": short_name,
        "section": section,
        "search_key": search_key,
        "historical_only": historical_only,
        "confidence": round(float(prob), 4),
    }


class MLStatutePredictor:
    """Thread-safe lazy wrapper around statutory_section_predictor.joblib."""

    _bundle: Any = None
    _load_attempted: bool = False
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_bundle(cls) -> Any:
        if cls._bundle is None and not cls._load_attempted:
            with cls._lock:
                if cls._bundle is None and not cls._load_attempted:
                    cls._load_attempted = True
                    if _DEFAULT_MODEL_PATH.exists():
                        try:
                            import joblib

                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                cls._bundle = joblib.load(_DEFAULT_MODEL_PATH)
                            logger.info(
                                "Loaded Stage-0 ML statutory predictor from '%s'",
                                _DEFAULT_MODEL_PATH,
                            )
                        except Exception as exc:
                            logger.warning("Could not load ML statutory predictor: %s", exc)
                    else:
                        logger.debug(
                            "ML statutory predictor file not found at '%s'",
                            _DEFAULT_MODEL_PATH,
                        )
        return cls._bundle

    @classmethod
    def predict_statutes(
        cls,
        text: str,
        top_k: int = 6,
        threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Predict applicable statutory and companion provisions for raw case text."""
        if not text or not text.strip():
            return []
        bundle = cls._get_bundle()
        if bundle is None:
            return []

        try:
            import numpy as np

            pipeline = bundle.get("pipeline")
            classes = list(bundle.get("classes") or [])
            if pipeline is None or not classes:
                return []

            probs = np.asarray(pipeline.predict_proba([text])[0], dtype=float)
            ranked = np.argsort(probs)[::-1]
            text_lower = text.lower()

            prob_by_code = {str(classes[idx]): float(probs[idx]) for idx in range(len(classes))}
            results: list[dict[str, Any]] = []
            seen_codes: set[str] = set()

            for idx in ranked:
                if len(results) >= top_k:
                    break
                code = str(classes[idx])
                prob = float(probs[idx])
                if prob < threshold:
                    break
                meta = _SECTION_METADATA.get(code)
                if meta is None:
                    continue
                requires_any = meta[6]
                if requires_any and not any(kw in text_lower for kw in requires_any):
                    continue
                entry = _build_entry(code, prob)
                if entry is not None:
                    results.append(entry)
                    seen_codes.add(code)

            # Companion safeguards when primary domain keywords are present
            if any(kw in text_lower for kw in ("arms act", "country made pistol", "unlicensed firearm")):
                for arm_code in ("ARMS_25", "ARMS_39"):
                    if arm_code not in seen_codes and arm_code in _SECTION_METADATA:
                        entry = _build_entry(arm_code, max(prob_by_code.get(arm_code, 0.0), threshold))
                        if entry is not None:
                            results.append(entry)
                            seen_codes.add(arm_code)

            if any(kw in text_lower for kw in ("stolen", "411")):
                if "IEA_114" not in seen_codes:
                    entry = _build_entry("IEA_114", max(prob_by_code.get("IEA_114", 0.0), threshold))
                    if entry is not None:
                        results.append(entry)
                        seen_codes.add("IEA_114")

            return results[:top_k]
        except Exception as exc:
            logger.debug("ML statutory prediction skipped: %s", exc)
            return []

    @classmethod
    def predict_for_case(
        cls,
        case: Any,
        question: str = "",
        top_k: int = 6,
        threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Predict statutes from a StructuredCase instance and optional research query."""
        if case is None:
            return cls.predict_statutes(question, top_k=top_k, threshold=threshold)

        parts: list[str] = []
        if getattr(case, "case_title", ""):
            parts.append(str(case.case_title))
        if getattr(case, "allegations_summary", ""):
            parts.append(str(case.allegations_summary))
        for ch in getattr(case, "charges", []) or []:
            parts.append(f"{ch.statute} {ch.section} {ch.description}".strip())
        for fact in getattr(case, "prosecution_facts", []) or []:
            parts.append(str(fact))
        for fact in getattr(case, "defense_facts", []) or []:
            parts.append(str(fact))
        if getattr(case, "procedural_history", None):
            parts.append(str(case.procedural_history))
        for gap in getattr(case, "missing_or_uncertain_info", []) or []:
            parts.append(str(gap))
        if question:
            parts.append(question)

        combined = " ".join(p for p in parts if p).strip()
        return cls.predict_statutes(combined, top_k=top_k, threshold=threshold)
