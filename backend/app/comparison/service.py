"""
Comparison Service for Phase 5 — AI Court Judgment Comparison Engine.
Orchestrates Mode A (Post-Trial Comparison) and Mode B (Manual Comparison).
Strictly enforces Ground Truth isolation from the courtroom pipeline.
All results are returned in-memory only — no outputs are written to disk.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from app.comparison.comparator import JudgmentComparator
from app.comparison.errors import (
    AIJudgmentNotFoundError,
    RealJudgmentNotFoundError,
)
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.loaders import ComparisonDocumentLoader
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.schemas import ComparisonReport
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

        assess_map = {
            "verdict_alignment": verdict_comp.is_assessable,
            "reasoning_alignment": reasoning_comp.is_assessable,
            "factual_accuracy": fact_comp.is_assessable,
            "issue_alignment": issue_comp.is_assessable,
            "evidence_alignment": evidence_comp.is_assessable,
            "finding_alignment": finding_comp.is_assessable,
            "charge_alignment": charge_comp.is_assessable,
            "witness_alignment": witness_comp.is_assessable,
            "legal_alignment": legal_comp.is_assessable,
            "final_order_alignment": order_comp.is_assessable,
        }
        scores = self.scoring_engine.calculate_scores(
            verdict_alignment=verdict_comp.score,
            issue_alignment=issue_comp.score,
            factual_accuracy=fact_comp.score,
            charge_alignment=charge_comp.score,
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
