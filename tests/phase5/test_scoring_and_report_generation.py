"""
Phase 5 Tests: Scoring Methodology and Report Generation.
Verifies configurable weights, non-verdict dominance in overall scoring,
and complete 17-section report rendering across JSON, TXT, and PDF.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pymupdf

from app.comparison.comparator import JudgmentComparator
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.schemas import ComparisonReport, ComparisonScores
from app.comparison.scoring import ComparisonScoringConfig, ScoringEngine
from app.models.judgment_models import Judgment


def test_scoring_weights_configuration():
    """Verify default and overridden scoring weights."""
    default_weights = ComparisonScoringConfig.get_weights()
    assert sum(default_weights.values()) == pytest.approx(1.0, 0.01)
    assert default_weights["verdict_alignment"] == 0.20
    assert default_weights["reasoning_alignment"] == 0.20

    # Custom weights
    custom = ComparisonScoringConfig.get_weights({"verdict_alignment": 0.50, "reasoning_alignment": 0.50})
    assert custom["verdict_alignment"] > 0.30


def test_overall_score_not_dominated_only_by_verdict():
    """
    CRITICAL REQUIREMENT: The overall score MUST NOT be determined only by the verdict.
    Even if verdict_alignment is 100%, if reasoning and issues are low, overall score is moderate/low.
    """
    engine = ScoringEngine()
    scores: ComparisonScores = engine.calculate_scores(
        verdict_alignment=100.0,
        issue_alignment=30.0,
        factual_accuracy=50.0,
        charge_alignment=60.0,
        witness_alignment=40.0,
        evidence_alignment=30.0,
        legal_alignment=20.0,
        reasoning_alignment=25.0,
        finding_alignment=70.0,
        final_order_alignment=100.0,
    )

    assert scores.verdict_alignment == 100.0
    # Overall score must reflect weighted average, not just 100%
    assert scores.overall_score < 60.0
    assert scores.overall_score > 35.0


def test_comparison_report_all_17_sections_present(
    synthetic_ai_judgment: Judgment, real_court_judgment_text: str, tmp_path: Path
):
    """
    Verify complete 17-section report construction, text formatting, and PDF rendering.
    """
    ai_norm = JudgmentNormalizer.normalize_ai_judgment(synthetic_ai_judgment)
    real_norm = JudgmentNormalizer.normalize_real_judgment(real_court_judgment_text)

    comparator = JudgmentComparator()
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

    scoring_engine = ScoringEngine()
    scores = scoring_engine.calculate_scores(
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
    )

    report: ComparisonReport = ComparisonReportGenerator.build_report(
        comparison_id="CMP-TEST-001",
        case_id="CASE-2024-001",
        case_title="State v. Jai Bhagwan",
        mode="post_trial",
        timestamp="2026-10-06T12:00:00",
        case_information={"case_id": "CASE-2024-001", "court": "Delhi High Court"},
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

    # 1. JSON serializability & Schema completeness
    dumped = report.model_dump()
    assert dumped["comparison_id"] == "CMP-TEST-001"
    assert "verdict_comparison" in dumped
    assert "reasoning_comparison" in dumped
    assert "scores" in dumped
    assert len(dumped["scores"]) > 5

    # 2. Text rendering verification
    report_text = ComparisonReportGenerator.format_report_text(report)
    for section_header in [
        "1. CASE INFORMATION",
        "2. OVERALL ASSESSMENT",
        "3. VERDICT COMPARISON",
        "4. ISSUE COMPARISON",
        "5. FACTUAL COMPARISON",
        "6. CHARGE COMPARISON",
        "7. WITNESS COMPARISON",
        "8. EVIDENCE COMPARISON",
        "9. LEGAL PROVISION COMPARISON",
        "10. LEGAL REASONING COMPARISON",
        "11. FINDING COMPARISON",
        "12. FINAL ORDER COMPARISON",
        "13. MAJOR ERRORS",
        "14. MISSING IMPORTANT POINTS",
        "15. UNRELATED / HALLUCINATED POINTS",
        "16. COMPREHENSIVE BENCHMARK SCORES",
        "17. OVERALL CONCLUSION",
    ]:
        assert section_header in report_text, f"Missing section: {section_header}"

    # 3. PDF rendering verification
    pdf_out = tmp_path / "comparison.pdf"
    ComparisonReportGenerator.write_report_pdf(report_text, pdf_out)
    assert pdf_out.exists()
    assert pdf_out.stat().st_size > 1000

    doc = pymupdf.open(str(pdf_out))
    assert len(doc) >= 1
    pdf_text = doc[0].get_text()
    assert "COMPARISON REPORT" in pdf_text
    doc.close()
