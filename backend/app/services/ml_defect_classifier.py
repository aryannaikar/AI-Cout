"""
Stage-1 Classical ML Evidentiary Defect & Doctrinal-Trigger Classifier
+ Deterministic 5-Link Theft & Recovery Chain Evaluator.

Trained on Supreme Court of India decisions to surface fatal investigative
and procedural loopholes (absent independent panchas, missing prior TIP,
co-accused confession without independent recovery, unidentified property,
open-access recovery, missing Arms sanction/FSL, missing electronic certificate,
chain-of-custody/FIR delay gaps) with zero fabricated witness/exhibit IDs.
"""

from __future__ import annotations

import logging
import re
import threading
import warnings
from pathlib import Path
from typing import Any, Optional

from app.services.legal_transition import detect_case_legal_regime

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "models"
    / "evidentiary_defect_classifier.joblib"
)

_DEFECT_METADATA: dict[str, dict[str, Any]] = {
    "NO_INDEPENDENT_PANCH_WITNESS": {
        "title": "Absence / Hostility of Independent Panch Witnesses",
        "historical_law": "Section 100(4) CrPC & Section 114(g) IEA",
        "modern_law": "Section 103(4) BNSS & Section 119 BSA",
        "doctrinal_explanation": (
            "Search/seizure lacks independent civilian public witnesses (or independent panchas turned hostile), "
            "casting doubt on exclusive police-witnessed recovery."
        ),
        "requires_any": ("independent", "panch", "public witness", "seizure", "recovery", "search", "hostile"),
        "rule_patterns": (
            r"\b(?:no|without|absence of|failed to join|non-examination of)\s+(?:any\s+)?independent\s+(?:public\s+|local\s+|civilian\s+)?(?:witness|panch)",
            r"\bpanch(?:as|\s+witness(?:es)?)?\s+turned\s+hostile\b",
            r"\bonly\s+police\s+(?:witness(?:es)?|personnel)\b",
        ),
    },
    "GENERIC_UNIDENTIFIED_PROPERTY": {
        "title": "Generic / Unidentified Property Without Ownership Proof",
        "historical_law": "Sections 410 & 411 IPC / Sections 101-102 IEA",
        "modern_law": "Section 317 BNS / Sections 104-105 BSA",
        "doctrinal_explanation": (
            "Recovered property appears generic or unnumbered without serial numbers, distinctive marks, "
            "or Article TIP linking it conclusively to the alleged theft."
        ),
        "requires_any": ("stolen", "theft", "411", "379", "317", "303", "cash", "currency", "scrap", "railway property", "3(a)", "unmarked", "unnumbered", "serial number"),
        "rule_patterns": (
            r"\b(?:no|without|lacking)\s+(?:serial\s+number|distinctive\s+mark|identification\s+mark|ownership\s+proof)",
            r"\b(?:unnumbered|unmarked)\s+(?:cash|currency|notes|scrap|iron|articles|property)\b",
            r"\bidentity\s+of\s+(?:the\s+)?stolen\s+property\s+(?:not|never)\s+established\b",
        ),
    },
    "NO_PRIOR_TIP_DOCK_ID": {
        "title": "First-Time Dock Identification Without Prior TIP",
        "historical_law": "Section 9 IEA",
        "modern_law": "Section 7 BSA",
        "doctrinal_explanation": (
            "In-court dock identification of an unfamiliar accused or article without a prior Test Identification Parade (TIP) "
            "carries weak evidentiary weight unless independently corroborated."
        ),
        "requires_any": ("tip", "test identification", "dock identification", "first time in court"),
        "rule_patterns": (
            r"\b(?:no|without|absence of)\s+(?:prior\s+)?(?:test\s+identification\s+parade|t\.?i\.?p\.?)\b",
            r"\bdock\s+identification\b.*?\bfirst\s+time\b",
        ),
    },
    "CO_ACCUSED_CONFESSION_ONLY": {
        "title": "Reliance on Co-Accused Confessional Statement",
        "historical_law": "Sections 25, 27 & 30 IEA",
        "modern_law": "Sections 23 & 24 BSA",
        "doctrinal_explanation": (
            "Confessional statement of a co-accused made in custody is inadmissible against another accused as substantive proof "
            "and cannot sustain conviction without independent physical recovery or corroboration."
        ),
        "requires_any": ("co-accused", "coaccused", "confessional statement", "disclosure of co-accused", "named by co-accused"),
        "rule_patterns": (
            r"\bconfession(?:al)?\s+(?:statement\s+)?of\s+co-?accused\b",
            r"\bco-?accused\s+confession(?:al)?(?:\s+statement)?\b",
            r"\b(?:implicated|named)\s+(?:solely|only)\s+(?:by|on\s+(?:the\s+)?basis\s+of)\s+co-?accused\b",
        ),
    },
    "OPEN_OR_JOINT_ACCESS_RECOVERY": {
        "title": "Recovery from Open or Jointly Accessible Place",
        "historical_law": "Section 27 IEA",
        "modern_law": "Section 23(2) Proviso BSA",
        "doctrinal_explanation": (
            "Articles recovered from an open place or shared premises accessible to others fail to establish "
            "exclusive and conscious possession."
        ),
        "requires_any": ("open place", "accessible", "conscious possession", "exclusive possession", "joint", "recovery", "seizure"),
        "rule_patterns": (
            r"\brecover(?:ed|y)\s+from\s+(?:an?\s+)?open\s+(?:place|field|area|bush)",
            r"\baccessible\s+to\s+(?:all|general\s+public|others|public)\b",
            r"\bexclusive\s+(?:and\s+conscious\s+)?possession\s+not\s+(?:proved|established)\b",
        ),
    },
    "MISSING_STATUTORY_SANCTION_OR_FSL": {
        "title": "Missing Statutory Sanction or Forensic/Ballistic Report",
        "historical_law": "Section 39 Arms Act, 1959 & Expert Proof Rules",
        "modern_law": "Section 39 Arms Act, 1959 & Expert Proof Rules",
        "doctrinal_explanation": (
            "Prosecution under firearm/special provisions requires valid previous statutory sanction and "
            "armourer/FSL operability verification."
        ),
        "requires_any": ("sanction", "arms act", "pistol", "firearm", "fsl", "ballistic", "armourer"),
        "rule_patterns": (
            r"\b(?:no|without|absence of|missing)\s+(?:valid\s+|previous\s+)?sanction\b",
            r"\b(?:no|without|missing)\s+(?:fsl|forensic|ballistic|armourer)\s+report\b",
        ),
    },
    "MISSING_ELECTRONIC_CERTIFICATE": {
        "title": "Unaccompanied Secondary Electronic Evidence",
        "historical_law": "Section 65B(4) IEA",
        "modern_law": "Section 63(4) BSA",
        "doctrinal_explanation": (
            "Secondary electronic evidence (CCTV/CDR/digital logs) is inadmissible unless accompanied by the mandatory statutory certificate."
        ),
        "requires_any": ("electronic", "cctv", "cdr", "call log", "65b", "section 63", "video", "server"),
        "rule_patterns": (
            r"\b(?:65\s*b|section\s+63(?:\s+bsa)?)\s+certificate\b",
            r"\belectronic\s+record.*?(?:missing|without\s+certificate|inadmissible)\b",
        ),
    },
    "UNEXPLAINED_DELAY_OR_CHAIN_GAP": {
        "title": "Unexplained FIR Delay or Broken Malkhana Chain of Custody",
        "historical_law": "Section 154 CrPC & Seal/Custody Integrity Rules",
        "modern_law": "Section 173 BNSS & Seal/Custody Integrity Rules",
        "doctrinal_explanation": (
            "Unexplained delay in FIR/dispatch or missing seal/Malkhana custody transfers diminishes evidentiary reliability."
        ),
        "requires_any": ("delay", "malkhana", "seal", "chain of custody", "tamper"),
        "rule_patterns": (
            r"\b(?:unexplained|inordinate)\s+delay\s+in\s+(?:lodging\s+)?(?:the\s+)?f\.?i\.?r\b",
            r"\bchain\s+of\s+custody.*?(?:broken|doubtful|not\s+established)\b",
            r"\bmalkhana\s+register\s+not\s+produced\b",
        ),
    },
}

_COMPILED_RULE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    code: tuple(re.compile(pat, re.IGNORECASE) for pat in meta["rule_patterns"])
    for code, meta in _DEFECT_METADATA.items()
}


def _collect_text_from_case_and_package(case: Any = None, package: Any = None) -> str:
    parts: list[str] = []
    if case is not None:
        for attr in ("case_title", "court_identifier", "allegations_summary", "procedural_history"):
            val = getattr(case, attr, None)
            if val:
                parts.append(str(val))
        for list_attr in ("prosecution_facts", "defense_facts", "legal_issues", "disputed_facts", "missing_or_uncertain_info"):
            for item in getattr(case, list_attr, []) or []:
                parts.append(str(item))
        for ch in getattr(case, "charges", []) or []:
            parts.append(f"{ch.statute} {ch.section} {ch.description}".strip())
        for w in getattr(case, "witnesses", []) or []:
            parts.append(f"{w.witness_type} {w.testimony_summary} {' '.join(w.key_assertions or [])}")
        for ex in getattr(case, "exhibits", []) or []:
            parts.append(f"{ex.title} {ex.exhibit_type} {ex.description} {ex.admissibility_notes or ''}")

    if package is not None:
        for attr_list in ("prosecution_witnesses", "defence_witnesses"):
            for w in getattr(package, attr_list, []) or []:
                parts.append(f"{getattr(w, 'role', '')} {' '.join(getattr(w, 'facts_testified', []) or [])}")
        for ex in getattr(package, "exhibits", []) or []:
            parts.append(f"{getattr(ex, 'evidence_type', '')} {getattr(ex, 'description', '')}")
        for pe in getattr(package, "physical_evidence", []) or []:
            parts.append(f"{getattr(pe, 'item_description', '')} {getattr(pe, 'recovered_from', '')}")
        for m in getattr(package, "missing_evidence", []) or []:
            parts.append(str(getattr(m, "description", "")))
        for c in getattr(package, "contradictions", []) or []:
            parts.append(str(getattr(c, "description", "")))

    return " ".join(p for p in parts if p).strip()


class MLEvidentiaryDefectClassifier:
    """Thread-safe wrapper around evidentiary_defect_classifier.joblib + 5-Link Theft Audit."""

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
                                "Loaded Stage-1 ML evidentiary defect classifier from '%s'",
                                _DEFAULT_MODEL_PATH,
                            )
                        except Exception as exc:
                            logger.warning("Could not load ML evidentiary defect classifier: %s", exc)
                    else:
                        logger.debug(
                            "ML evidentiary defect classifier file not found at '%s'",
                            _DEFAULT_MODEL_PATH,
                        )
        return cls._bundle

    @classmethod
    def detect_defects(
        cls,
        text: str,
        is_historical: bool = True,
        threshold: float = 0.35,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Detect evidentiary defects using ML classifier scores gated by lexical grounding."""
        if not text or not text.strip():
            return []

        text_lower = text.lower()
        bundle = cls._get_bundle()
        prob_by_code: dict[str, float] = {}

        if bundle is not None:
            try:
                import numpy as np

                pipeline = bundle.get("pipeline")
                classes = list(bundle.get("classes") or [])
                if pipeline is not None and classes:
                    probs = np.asarray(pipeline.predict_proba([text])[0], dtype=float)
                    for idx, code in enumerate(classes):
                        prob_by_code[str(code)] = float(probs[idx])
            except Exception as exc:
                logger.debug("ML defect classifier inference fallback to lexical rules: %s", exc)

        matched: list[dict[str, Any]] = []
        for code, meta in _DEFECT_METADATA.items():
            requires_any: tuple[str, ...] = meta["requires_any"]
            if requires_any and not any(kw in text_lower for kw in requires_any):
                continue

            ml_prob = prob_by_code.get(code, 0.0)
            rule_hit = any(pat.search(text) for pat in _COMPILED_RULE_PATTERNS.get(code, ()))

            if ml_prob >= threshold or rule_hit:
                effective_conf = max(ml_prob, 0.85 if rule_hit else ml_prob)
                law_str = meta["historical_law"] if is_historical else meta["modern_law"]
                matched.append({
                    "code": code,
                    "title": meta["title"],
                    "provision": law_str,
                    "description": f"[{meta['title']} | {law_str}]: {meta['doctrinal_explanation']}",
                    "confidence": round(float(effective_conf), 3),
                })

        matched.sort(key=lambda d: d["confidence"], reverse=True)
        return matched[:top_k]

    @classmethod
    def detect_for_case(
        cls,
        case: Any = None,
        package: Any = None,
        top_k: int = 5,
        threshold: float = 0.35,
    ) -> list[str]:
        """Return formatted defect descriptions grounded in case / EvidencePackage."""
        combined = _collect_text_from_case_and_package(case=case, package=package)
        if not combined:
            return []
        is_hist = detect_case_legal_regime(case).get("is_historical", True) if case is not None else True
        defects = cls.detect_defects(combined, is_historical=is_hist, threshold=threshold, top_k=top_k)
        return [d["description"] for d in defects]

    @classmethod
    def evaluate_theft_recovery_chain(
        cls,
        case: Any = None,
        package: Any = None,
        is_historical: Optional[bool] = None,
    ) -> list[str]:
        """
        Evaluate the 5 mandatory judicial links for theft, robbery, dacoity,
        stolen property, or physical recovery cases. Returns [] for unrelated offences.
        """
        combined = _collect_text_from_case_and_package(case=case, package=package)
        if not combined:
            return []

        low = combined.lower()
        theft_markers = (
            "379", "380", "392", "395", "411", "412", "303", "309", "310", "317",
            "3(a)", "railway property", "stolen", "theft", "robbery", "dacoity",
            "recovery memo", "seizure memo",
        )
        if not any(tok in low for tok in theft_markers):
            return []

        if is_historical is None:
            is_hist = detect_case_legal_regime(case).get("is_historical", True) if case is not None else True
        else:
            is_hist = is_historical

        audit: list[str] = []

        # Link 1: Property Identity & Ownership
        stolen_stat = "Section 410/411 IPC" if is_hist else "Section 317 BNS"
        if any(k in low for k in ("unmarked", "unnumbered", "without serial", "not proved", "ownership", "generic")):
            audit.append(
                f"Link 1 (Property Identity - {stolen_stat}): Recovered articles/cash lack distinctive identification marks, "
                "serial numbers, or completed ownership proof linking them conclusively to the alleged theft."
            )
        else:
            audit.append(
                f"Link 1 (Property Identity - {stolen_stat}): Verify whether stolen property identity and lawful ownership "
                "are proved by distinctive identifying marks, serial numbers, or expert verification on record."
            )

        # Link 2: Exclusive & Conscious Possession
        rec_stat = "Section 27 IEA" if is_hist else "Section 23 BSA"
        if any(k in low for k in ("open place", "accessible", "joint", "planted", "conscious possession")):
            audit.append(
                f"Link 2 (Exclusive Conscious Possession - {rec_stat}): Recovery location or exclusive conscious possession "
                "is contested (open/jointly accessible premises or allegation of planting)."
            )
        else:
            audit.append(
                f"Link 2 (Exclusive Conscious Possession - {rec_stat}): Verify that recovery was from exclusive locked custody "
                "attributable distinctly to the named accused rather than public/joint access."
            )

        # Link 3: Independent Seizure Compliance
        search_stat = "Section 100(4) CrPC & Section 114(g) IEA" if is_hist else "Section 103(4) BNSS & Section 119 BSA"
        if any(k in low for k in ("no independent", "without independent", "hostile", "only police")):
            audit.append(
                f"Link 3 (Independent Seizure Compliance - {search_stat}): Absence or hostility of independent local public "
                "panch witnesses weakens reliability of police seizure memo."
            )
        else:
            audit.append(
                f"Link 3 (Independent Seizure Compliance - {search_stat}): Check attestation and testimony of independent local "
                "panch witnesses supporting the seizure memo."
            )

        # Link 4: Foundational Theft & Presumption Threshold
        presum_stat = "Sections 102 & 114(a) IEA" if is_hist else "Sections 105 & 119 BSA"
        theft_sec = "Section 379 IPC" if is_hist else "Section 303 BNS"
        recv_sec = "Section 411 IPC" if is_hist else "Section 317 BNS"
        audit.append(
            f"Link 4 (Foundational Theft & Presumption - {presum_stat}): Foundational theft and recent possession must be strictly "
            f"proved before any presumption arises; acquittal on foundational theft ({theft_sec}) defeats derivative {recv_sec} liability on the same facts."
        )

        # Link 5: Accused-Wise Liability Separation
        subjects = (
            case.distinct_decision_subjects()
            if case is not None and hasattr(case, "distinct_decision_subjects")
            else (list(getattr(case, "accused", []) or []) if case is not None else [])
        )
        conf_stat = "Sections 25 & 30 IEA" if is_hist else "Sections 23 & 24 BSA"
        if len(subjects) > 1 or "co-accused" in low:
            audit.append(
                f"Link 5 (Accused-Wise Liability Separation - {conf_stat}): Separate accused apprehended with spot recovery "
                "from any co-accused implicated solely through custody/co-accused confessional statements without independent recovery."
            )

        return audit
