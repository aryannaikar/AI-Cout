"""
Phase 5 Tests: Comparison Service Workflow and Ground Truth Isolation Security.
Verifies Mode A (Post-Trial), Mode B (Manual Standalone), error handling,
and guarantees Ground Truth never leaks into the courtroom graph.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.comparison.errors import (
    AIJudgmentNotFoundError,
    RealJudgmentNotFoundError,
)
from app.comparison.schemas import ComparisonReport
from app.comparison.service import ComparisonService
from app.graph.state import CourtState
from app.graph.validation import BlindEvaluationViolation, validate_no_ground_truth_text
from app.graph.workflow import CourtWorkflow


def test_post_trial_comparison_workflow(
    tmp_path: Path, synthetic_ai_judgment_json: str, real_court_judgment_text: str
):
    """
    Verify Mode A: Post-Trial Comparison execution and artifact output.
    Ensures comparison.json, comparison.txt, and comparison.pdf are saved in comparison/
    without modifying the original output/ directory.
    """
    case_id = "CASE-TEST-PT-001"
    cases_dir = tmp_path / "cases"
    case_out_dir = cases_dir / case_id / "output"
    case_out_dir.mkdir(parents=True)

    # Save original AI Judgment in output/
    ai_json_file = case_out_dir / "ai_judgment.json"
    ai_json_file.write_text(synthetic_ai_judgment_json, encoding="utf-8")
    original_mtime = ai_json_file.stat().st_mtime

    service = ComparisonService(base_cases_dir=cases_dir)
    report = service.compare_post_trial(
        case_id=case_id,
        real_judgment_source=real_court_judgment_text,
    )

    assert isinstance(report, ComparisonReport)
    assert report.case_id == case_id
    assert report.mode == "post_trial"

    # Verify comparison directory was created
    comp_dir = cases_dir / case_id / "comparison"
    assert comp_dir.exists()
    assert (comp_dir / "comparison.json").exists()
    assert (comp_dir / "comparison.txt").exists()
    assert (comp_dir / "comparison.pdf").exists()

    # CRITICAL: Verify output/ directory was NOT modified
    assert ai_json_file.stat().st_mtime == original_mtime


def test_post_trial_comparison_missing_ai_judgment_raises_error(tmp_path: Path, real_court_judgment_text: str):
    """Verify Post-Trial comparison fails cleanly if AI judgment does not exist."""
    cases_dir = tmp_path / "cases"
    service = ComparisonService(base_cases_dir=cases_dir)

    with pytest.raises(AIJudgmentNotFoundError):
        service.compare_post_trial(
            case_id="NON_EXISTENT_CASE",
            real_judgment_source=real_court_judgment_text,
        )


def test_post_trial_comparison_missing_real_judgment_raises_error(tmp_path: Path, synthetic_ai_judgment_json: str):
    """Verify Post-Trial comparison fails if real judgment is None."""
    case_id = "CASE-TEST-PT-002"
    cases_dir = tmp_path / "cases"
    case_out_dir = cases_dir / case_id / "output"
    case_out_dir.mkdir(parents=True)
    (case_out_dir / "ai_judgment.json").write_text(synthetic_ai_judgment_json, encoding="utf-8")

    service = ComparisonService(base_cases_dir=cases_dir)
    with pytest.raises(RealJudgmentNotFoundError):
        service.compare_post_trial(
            case_id=case_id,
            real_judgment_source=None,
        )


def test_manual_standalone_comparison_mode(
    synthetic_ai_judgment_json: str, real_court_judgment_text: str, sample_case_packet_txt: str
):
    """
    Verify Mode B: Manual comparison works directly with user-supplied documents
    without invoking the courtroom graph.
    """
    service = ComparisonService()
    report = service.compare_manual(
        ai_judgment_source=synthetic_ai_judgment_json,
        real_judgment_source=real_court_judgment_text,
        case_packet_source=sample_case_packet_txt,
    )

    assert isinstance(report, ComparisonReport)
    assert report.mode == "manual"
    assert report.scores.verdict_alignment == 100.0


def test_ground_truth_security_isolation_enforcement(real_court_judgment_text: str):
    """
    CRITICAL SECURITY TEST:
    Verifies that Real Court Judgment / Ground Truth CANNOT enter CourtState
    or CourtWorkflow, but is exclusively isolated to the Comparison Engine.
    """
    gt_header_text = (
        "Ground Truth Verdict: Guilty\n"
        "Real court judgment — evaluation benchmark\n"
        f"{real_court_judgment_text}"
    )

    # 1. BlindEvaluation check strictly catches GT in text
    with pytest.raises(BlindEvaluationViolation):
        validate_no_ground_truth_text(gt_header_text)

    # 2. CourtState strictly rejects GT
    with pytest.raises(BlindEvaluationViolation):
        CourtState(case_packet=gt_header_text)

    # 3. CourtWorkflow strictly rejects GT
    workflow = CourtWorkflow()
    with pytest.raises(BlindEvaluationViolation):
        workflow.run(gt_header_text)
