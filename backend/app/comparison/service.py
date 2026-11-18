"""
Comparison Service for Phase 5 — AI Court Judgment Comparison Engine.
Orchestrates Mode A (Post-Trial Comparison) and Mode B (Manual Comparison).
Strictly enforces Ground Truth isolation from the courtroom pipeline.
All results are returned in-memory only — no outputs are written to disk.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from app.comparison.comparator import JudgmentComparator
from app.comparison.errors import AIJudgmentNotFoundError, RealJudgmentNotFoundError
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.loaders import ComparisonDocumentLoader
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.schemas import ComparisonReport, NormalizedJudgment
from app.comparison.scoring import ScoringEngine

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    Central service for evaluating AI Court judgments against authoritative Real Court decisions.
    Supports Mode A (Post-Trial) and Mode B (Manual Standalone).
    Results are returned in-memory and never persisted to disk.
    """

    def __init__(
        self,
        base_cases_dir: Optional[Union[str, Path]] = None,
        scoring_weights: Optional[Dict[str, float]] = None,
    ):
        self.scoring_engine = ScoringEngine(custom_weights=scoring_weights)

    @staticmethod
    def _identity_tokens(value: Optional[str]) -> set[str]:
        """Normalize identifiers while removing generic caption and court words."""
        generic = {
            "state", "union", "india", "court", "high", "supreme", "criminal",
            "appeal", "case", "judgment", "accused", "appellant", "respondent",
        }
        return {
            token for token in re.findall(r"[a-z0-9]+", (value or "").lower())
            if len(token) > 2 and token not in generic
        }

    @classmethod
    def _validate_case_identity(
        cls, ai: NormalizedJudgment, real: NormalizedJudgment
    ) -> Dict[str, Any]:
        """Reject only a conflict in a reliable shared case identifier.

        Court names, captions and party labels are frequently abbreviated or
        inferred differently by the AI judgment and a scanned real judgment.
        They are useful report metadata, but are not safe enough to deny a
        comparison request.  A populated case number is the only identifier
        this generic pipeline can compare deterministically.
        """
        checks: List[Dict[str, Any]] = []
        conflicts: List[str] = []

        def unavailable_placeholder(value: Optional[str]) -> bool:
            normalized = cls._normalise_identifier(value or "")
            return normalized in {"", "state", "accusedappellant", "statevaccused", "courtofsessionshighcourt"}

        def add_check(field: str, ai_value: Optional[str], real_value: Optional[str], exact: bool = False) -> None:
            ai_tokens, real_tokens = cls._identity_tokens(ai_value), cls._identity_tokens(real_value)
            if unavailable_placeholder(ai_value) or unavailable_placeholder(real_value):
                checks.append({"field": field, "status": "unavailable"})
                return
            overlap = len(ai_tokens & real_tokens) / max(1, len(ai_tokens | real_tokens))
            matched = cls._normalise_identifier(ai_value) == cls._normalise_identifier(real_value) if exact else overlap >= 0.5
            checks.append({
                "field": field, "status": "match" if matched else "conflict",
                "ai": ai_value, "ground_truth": real_value,
            })
            if not matched:
                conflicts.append(field)

        add_check("case_number", ai.case_number, real.case_number, exact=True)
        add_check("court", ai.presiding_court, real.presiding_court)
        add_check("accused_or_appellant", ai.parties.appellant_or_accused, real.parties.appellant_or_accused)
        add_check("respondent_or_state", ai.parties.respondent_or_state, real.parties.respondent_or_state)

        # Captions are informative only. A title conflict cannot by itself reject
        # a comparison because formatting and party ordering vary by judgment.
        ai_title, real_title = cls._identity_tokens(ai.case_title), cls._identity_tokens(real.case_title)
        title_overlap = len(ai_title & real_title) / max(1, len(ai_title | real_title))
        title_conflict = bool(ai_title and real_title and title_overlap < 0.25)
        checks.append({"field": "case_title", "status": "conflict" if title_conflict else "match" if ai_title and real_title else "unavailable", "ai": ai.case_title, "ground_truth": real.case_title})

        # Only treat a case number as a reliable identifier when both sides
        # contain a substantive docket number. Normalizer fallbacks often
        # extract years, FIR numbers, or differently formatted references.
        ai_case_number = cls._normalise_identifier(ai.case_number or "")
        real_case_number = cls._normalise_identifier(real.case_number or "")
        has_reliable_case_numbers = bool(ai_case_number and real_case_number)
        matched = [check["field"] for check in checks if check["status"] == "match"]
        metadata_conflicts = [check["field"] for check in checks if check["status"] == "conflict"]
        reliable_match = "case_number" in matched and has_reliable_case_numbers
        return {
            "status": "verified" if reliable_match else "limited_metadata",
            "matched_identifiers": matched,
            "checks": checks,
            "note": (
                "Identity checks are informational and do not block comparison. "
                + (
                    "Other metadata differs ("
                    + ", ".join(metadata_conflicts)
                    + ") and is shown for review; it did not block comparison because it is not a reliable shared case identifier."
                    if metadata_conflicts else
                    "Limited metadata means the comparison proceeded without a reliable shared case identifier."
                )
            ),
        }

    @staticmethod
    def _normalise_identifier(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    def _run_comparison(
        self,
        ai_input: Any,
        real_input: Any,
        packet_text: Optional[str],
        case_id: str,
        mode: str,
        case_title: Optional[str] = None,
        presiding_court: Optional[str] = None,
        date_of_decision: Optional[str] = None,
    ) -> ComparisonReport:
        """Shared comparison logic for both modes — purely in-memory."""
        ai_norm = JudgmentNormalizer.normalize_ai_judgment(ai_input)
        real_norm = JudgmentNormalizer.normalize_real_judgment(real_input)
        identity_validation = self._validate_case_identity(ai_norm, real_norm)

        # Kept in memory only so the read-only "Understand the Difference" explainer can reuse
        # the already-normalised judgments without re-parsing the uploaded files.
        self.last_context = {"ai": ai_norm, "real": real_norm, "packet_text": packet_text}

        comparator = JudgmentComparator(case_packet_context=packet_text)
        (
            verdict_comp,
            issue_comp,
            fact_comp,
            charge_comp,
            witness_comp,
            evidence_comp,
            legal_comp,
            reasoning_comp,
            finding_comp,
            order_comp,
            major_errors,
            missing_points,
            unrelated_points,
        ) = comparator.compare(ai_norm, real_norm)

        # Charge Alignment includes the finding on each charge. Findings remain
        # visible as a diagnostic section, but are not an independently weighted
        # core dimension. Average only assessable charge/finding components.
        charge_components = [
            value for value, assessable in (
                (charge_comp.score, charge_comp.is_assessable),
                (finding_comp.score, finding_comp.is_assessable),
            ) if assessable
        ]
        core_charge_score = sum(charge_components) / len(charge_components) if charge_components else charge_comp.score
        if charge_components:
            charge_comp = charge_comp.model_copy(update={
                "score": round(core_charge_score, 2),
                "explanation": (
                    f"{charge_comp.explanation} Core Charge Alignment combines charge matching "
                    f"({charge_comp.score:.2f}%) and charge-wise findings "
                    f"({finding_comp.score:.2f}%) across assessable components; findings are diagnostic only outside this merged score."
                ),
            })

        assess_map = {
            "verdict_alignment": verdict_comp.is_assessable,
            "reasoning_alignment": reasoning_comp.is_assessable,
            "factual_accuracy": fact_comp.is_assessable,
            "issue_alignment": issue_comp.is_assessable,
            "evidence_alignment": evidence_comp.is_assessable,
            "finding_alignment": finding_comp.is_assessable,
            "charge_alignment": bool(charge_components),
            "witness_alignment": witness_comp.is_assessable,
            "legal_alignment": legal_comp.is_assessable,
            "final_order_alignment": order_comp.is_assessable,
        }
        scores = self.scoring_engine.calculate_scores(
            verdict_alignment=verdict_comp.score,
            issue_alignment=issue_comp.score,
            factual_accuracy=fact_comp.score,
            charge_alignment=core_charge_score,
            witness_alignment=witness_comp.score,
            evidence_alignment=evidence_comp.score,
            legal_alignment=legal_comp.score,
            reasoning_alignment=reasoning_comp.score,
            finding_alignment=finding_comp.score,
            final_order_alignment=order_comp.score,
            assessability=assess_map,
        )

        comparison_id = f"CMP-{case_id}-{uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        case_info = {
            "case_id": case_id,
            "case_title": case_title or real_norm.case_title or ai_norm.case_title,
            "presiding_court": presiding_court or real_norm.presiding_court or "Supreme Court of India",
            "date_of_decision": date_of_decision or real_norm.date_of_decision or ai_norm.date_of_decision,
            "identity_validation": identity_validation,
        }
        if mode == "manual":
            case_info["case_packet_provided"] = packet_text is not None

        return ComparisonReportGenerator.build_report(
            comparison_id=comparison_id,
            case_id=case_id,
            case_title=case_info["case_title"],
            mode=mode,
            timestamp=timestamp,
            case_information=case_info,
            verdict_comp=verdict_comp,
            issue_comp=issue_comp,
            fact_comp=fact_comp,
            charge_comp=charge_comp,
            witness_comp=witness_comp,
            evidence_comp=evidence_comp,
            legal_comp=legal_comp,
            reasoning_comp=reasoning_comp,
            finding_comp=finding_comp,
            order_comp=order_comp,
            scores=scores,
            major_errors=major_errors,
            missing_points=missing_points,
            unrelated_points=unrelated_points,
        )

    # --------------------------------------------------------------------------
    # MODE A: Post-Trial Comparison
    # --------------------------------------------------------------------------

    def compare_post_trial(
        self,
        case_id: str,
        real_judgment_source: Union[str, Path, bytes, dict],
        ai_judgment_source: Optional[Union[str, Path, bytes, dict]] = None,
        case_packet_source: Optional[Union[str, Path, bytes]] = None,
    ) -> ComparisonReport:
        """
        Post-Trial Comparison mode.
        AI judgment must be supplied directly (not read from disk).
        Real Court Judgment is provided by the user.
        """
        logger.info("Initiating Post-Trial comparison for case: '%s'", case_id)

        if ai_judgment_source is None:
            raise AIJudgmentNotFoundError(
                f"AI Judgment for case '{case_id}' must be supplied directly. "
                f"Disk-based fallback has been disabled."
            )

        ai_input = ComparisonDocumentLoader.load_ai_judgment(ai_judgment_source)

        if real_judgment_source is None:
            raise RealJudgmentNotFoundError("Real Court Judgment / Ground Truth must be provided.")
        real_input = ComparisonDocumentLoader.load_real_judgment(real_judgment_source)

        packet_text = ComparisonDocumentLoader.load_case_packet(case_packet_source)

        return self._run_comparison(
            ai_input=ai_input,
            real_input=real_input,
            packet_text=packet_text,
            case_id=case_id,
            mode="post_trial",
        )

    # --------------------------------------------------------------------------
    # MODE B: Manual Standalone Comparison
    # --------------------------------------------------------------------------

    def compare_manual(
        self,
        ai_judgment_source: Union[str, Path, bytes, dict],
        real_judgment_source: Union[str, Path, bytes, dict],
        case_packet_source: Optional[Union[str, Path, bytes]] = None,
        case_id: Optional[str] = None,
    ) -> ComparisonReport:
        """
        Manual/standalone comparison mode.
        Does NOT execute courtroom. Evaluates user-supplied AI Judgment vs Real Court Judgment.
        Optional case packet is supporting context only, never ground truth.
        Results are returned in-memory only.
        """
        logger.info("Initiating Manual comparison mode.")

        ai_input = ComparisonDocumentLoader.load_ai_judgment(ai_judgment_source)
        real_input = ComparisonDocumentLoader.load_real_judgment(real_judgment_source)
        packet_text = ComparisonDocumentLoader.load_case_packet(case_packet_source)

        cid = case_id or f"MANUAL-{uuid4().hex[:8]}"

        return self._run_comparison(
            ai_input=ai_input,
            real_input=real_input,
            packet_text=packet_text,
            case_id=cid,
            mode="manual",
        )
