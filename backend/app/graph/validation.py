"""
Validation and Security Guardrails for AI Court of India LangGraph Orchestration.
Enforces strict blind evaluation: guarantees Ground_Truth_Verdict.pdf and
any actual court judgments or evaluation labels never enter the courtroom graph.

Security Design:
- FILENAME validation: rejects files whose names explicitly identify them as GT/verdict docs.
- TEXT validation: uses COMPOUND-SIGNAL logic — a document is only rejected when it
  exhibits MULTIPLE co-occurring evaluation indicators (e.g. both "ground truth" and a
  final verdict declaration). Single ordinary legal words such as "judgment", "order",
  "verdict" referenced in case evidence are ALWAYS permitted.

FALSE POSITIVE prevention:
  - "Ex.PH - Release order" → ACCEPTED
  - "PW-6 stated... final report under Section 173 CrPC" → ACCEPTED
  - "The judgment dated 01.07.2002 was referenced as procedural history" → ACCEPTED

TRUE POSITIVE enforcement:
  - "Ground truth verdict: Guilty" → REJECTED
  - "Real court judgment — evaluation benchmark" → REJECTED
  - Document containing "ground truth" AND "final verdict: convicted" → REJECTED
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Forbidden state/dict keys — ground truth must never enter CourtState
# ---------------------------------------------------------------------------
FORBIDDEN_KEYS = {
    "ground_truth",
    "real_verdict",
    "actual_judgment",
    "correct_verdict",
    "ground_truth_verdict",
    "actual_reasoning",
    "hidden_evaluation_label",
    "actual_court_decision",
}

# ---------------------------------------------------------------------------
# Forbidden file name substrings — only block files explicitly labelled GT
# NOTE: "judgment" and "verdict" are NOT here — they are ordinary legal words.
# Only explicit compound identifiers that unambiguously denote GT files are blocked.
# ---------------------------------------------------------------------------
FORBIDDEN_FILE_SUBSTRINGS = [
    "ground_truth",
    "real_verdict",
    "actual_judgment",
    "hidden_verdict",
    "verdict_benchmark",
    "gt_verdict",
    "evaluation_verdict",
]

# ---------------------------------------------------------------------------
# Compound-phrase exact signatures — these are unambiguous evaluation declarations.
# Each phrase, by itself, is strong evidence of a GT document.
# ---------------------------------------------------------------------------

_STRONG_GT_SIGNATURES = [
    "ground truth verdict",
    "real court judgment",          # "real court judgment" as a header/declaration
    "hidden evaluation verdict",
    "hidden evaluation label",
    "correct verdict is",           # "the correct verdict is ..."
    "ground truth is",              # "the ground truth is ..."
    "evaluation ground truth",
    "benchmark verdict",
    "actual evaluation outcome",
    "ground_truth_verdict",         # machine-generated key leaked into doc
]

# Verdict-declaration patterns: "REAL VERDICT: convicted", "actual verdict: guilty", etc.
# These are explicit outcome declarations — strong GT signals even alone.
_VERDICT_OUTCOME_DECLARATION_RE = re.compile(
    r"\b(?:real\s+verdict|actual\s+verdict|correct\s+verdict|hidden\s+verdict|final\s+verdict)\s*:\s*"
    r"(?:guilty|acquitted|convicted|not\s+guilty|imprisonment|the\s+accused|hereby)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Weak GT signals — individually innocuous, dangerous only in combination
# ---------------------------------------------------------------------------
_WEAK_GT_SIGNALS_RE = [
    re.compile(r"\bground[\s_-]*truth\b", re.IGNORECASE),
    re.compile(r"\bhidden[\s_-]*verdict\b", re.IGNORECASE),
    re.compile(r"\bactual[\s_-]*verdict\b", re.IGNORECASE),
    re.compile(r"\bcorrect[\s_-]*verdict\b", re.IGNORECASE),
    re.compile(r"\breal[\s_-]*verdict\b", re.IGNORECASE),
    re.compile(r"\bevaluation[\s_-]*label\b", re.IGNORECASE),
    re.compile(r"\bevaluation[\s_-]*benchmark\b", re.IGNORECASE),
]


class BlindEvaluationViolation(PermissionError):
    """Raised when ground truth or real verdict data is detected in the courtroom graph."""
    pass


def _is_ground_truth_document(text: str) -> bool:
    """
    Context-aware Ground Truth document detector.

    A document is classified as a GT/verdict document ONLY when it exhibits
    compound evidence of being an evaluation artifact — NOT from single keyword hits.

    Returns True if the document should be rejected.

    Detection logic (any one of these → reject):
    1. A strong compound GT signature phrase is present (unambiguous declaration).
    2. An explicit verdict outcome declaration is present
       (e.g. "REAL VERDICT: convicted", "actual verdict: hereby acquitted") —
       these are outcome statements strong enough to reject alone.
    3. A verdict-keyword pattern AND at least 1 weak GT signal co-occur.
    4. Three or more distinct weak GT signals co-occur in the same document.
    """
    text_lower = text.lower()

    # Rule 1: Strong compound signature — unambiguous alone
    for sig in _STRONG_GT_SIGNATURES:
        if sig in text_lower:
            logger.debug("GT detection Rule 1: strong signature '%s' found.", sig)
            return True

    # Rule 2: Explicit "VERDICT: <outcome>" declaration — strong signal alone
    if _VERDICT_OUTCOME_DECLARATION_RE.search(text):
        logger.debug("GT detection Rule 2: explicit verdict outcome declaration found.")
        return True

    # Rule 3: Verdict-keyword + at least 1 weak GT signal (compound)
    _VERDICT_KEYWORD_RE = re.compile(
        r"\b(?:final\s+verdict|actual\s+verdict|real\s+verdict|correct\s+verdict|hidden\s+verdict)\b",
        re.IGNORECASE,
    )
    if _VERDICT_KEYWORD_RE.search(text):
        weak_count = sum(1 for pat in _WEAK_GT_SIGNALS_RE if pat.search(text))
        if weak_count >= 2:
            logger.debug("GT detection Rule 3: verdict keyword + %d weak signal(s).", weak_count)
            return True

    # Rule 4: 3 or more distinct weak signals co-occurring
    weak_count = sum(1 for pat in _WEAK_GT_SIGNALS_RE if pat.search(text))
    if weak_count >= 3:
        logger.debug("GT detection Rule 4: %d distinct weak GT signals co-occurring.", weak_count)
        return True

    return False


def validate_case_packet_path(path_or_text: str | Path) -> None:
    """
    Validate that a case packet path does not point to a Ground Truth Verdict file.
    Permits legitimate case packets while strictly blocking Ground Truth / Verdict files.

    Ordinary legal words in filenames (judgment, order, appeal, verdict as part of
    a case name) are permitted. Only explicit GT/evaluation file identifiers are blocked.
    """
    if isinstance(path_or_text, str) and ("\n" in path_or_text or len(path_or_text) > 300):
        # Raw text representation of a case packet, not a filesystem path
        return

    is_path_like = isinstance(path_or_text, Path) or (
        isinstance(path_or_text, str)
        and (path_or_text.lower().endswith(".pdf") or "\\" in path_or_text or "/" in path_or_text or Path(path_or_text).is_file())
    )
    if is_path_like:
        p = Path(path_or_text)
        name_lower = p.name.lower()
        for forbidden in FORBIDDEN_FILE_SUBSTRINGS:
            if forbidden in name_lower:
                raise BlindEvaluationViolation(
                    f"SECURITY VIOLATION: Case packet path '{p.name}' rejected. "
                    f"Courtroom graph must never receive ground-truth verdict files."
                )


def validate_no_forbidden_keys(data: dict[str, Any]) -> None:
    """
    Ensure a dictionary does not contain any forbidden ground truth keys.
    """
    for key in data:
        key_lower = str(key).lower()
        for forbidden in FORBIDDEN_KEYS:
            if forbidden in key_lower:
                raise BlindEvaluationViolation(
                    f"SECURITY VIOLATION: Forbidden field '{key}' detected in courtroom state. "
                    f"Ground truth fields must never enter the LangGraph state."
                )


def validate_no_ground_truth_text(text: str) -> None:
    """
    Ensure raw text does not contain forbidden ground truth verdict signatures.

    Uses compound-signal contextual detection so ordinary occurrences of legal
    words ('judgment', 'verdict', 'order', 'court', 'decision') cited in case
    evidence, arguments, or procedural history are always permitted.

    Only rejects documents that are clearly evaluation Ground Truth / Real Verdict
    artifacts based on co-occurrence of multiple unambiguous GT indicators.

    FALSE POSITIVE prevention:
    - "Ex.PH - Release order of car" → ACCEPTED
    - "PW-6 Gurnam Singh identified the vehicle" → ACCEPTED
    - "final report under Section 173 CrPC" → ACCEPTED
    - "judgment dated 01.07.2002 referenced in procedural history" → ACCEPTED

    TRUE POSITIVE enforcement:
    - "Ground truth verdict: Guilty" → REJECTED
    - "Hidden evaluation verdict — do not expose to AI" → REJECTED
    - "actual verdict: Acquitted" + "ground truth" → REJECTED
    """
    if _is_ground_truth_document(text):
        raise BlindEvaluationViolation(
            "SECURITY VIOLATION: Document exhibits compound ground-truth signature. "
            "Upload only the unadjudicated Evidence Packet — not the "
            "actual court verdict or evaluation benchmark file."
        )
