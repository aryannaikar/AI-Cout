"""
Tests for Phase 5 — AI Court Judgment vs Real Court Judgment Comparison Engine.
Validates Post-Trial comparison, upload_id resolution, 10-dimensional scoring,
report generation, and ground truth isolation.
"""

from pathlib import Path
import pytest
from app.comparison.service import ComparisonService
from app.comparison.schemas import ComparisonReport, ComparisonScores
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.comparator import JudgmentComparator
from app.comparison.scoring import ScoringEngine


SAMPLE_REAL_JUDGMENT = """
IN THE HIGH COURT OF DELHI AT NEW DELHI
CRIMINAL APPEAL NO. 452/2023

State (NCT of Delhi) v. Ramesh Kumar

JUDGMENT
1. The accused was charged under Section 317 of Bharatiya Nyaya Sanhita, 2023.
2. The key issue is whether the prosecution proved possession of stolen property beyond reasonable doubt.
3. The prosecution witnesses PW1 and PW2 gave contradictory statements regarding recovery.
4. Independent witnesses were not joined during seizure.
5. In view of material inconsistencies, the benefit of doubt is extended to the accused.
VERDICT: ACQUITTAL.
The accused is hereby acquitted of all framed charges.
"""


def test_comparison_service_initialization():
    service = ComparisonService()
    assert service.base_cases_dir.exists()
    assert isinstance(service.scoring_engine, ScoringEngine)


def test_judgment_normalizer():
    norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_REAL_JUDGMENT)
    assert norm.case_title is not None
    assert norm.verdict is not None
    assert "ACQUITTAL" in norm.verdict.upper() or "ACQUIT" in norm.verdict.upper()


def test_judgment_comparator():
    comparator = JudgmentComparator()
    ai_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_REAL_JUDGMENT)
    real_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_REAL_JUDGMENT)
    
    (
        v_comp, i_comp, f_comp, c_comp, w_comp,
        e_comp, l_comp, r_comp, fnd_comp, ord_comp,
        major_errors, missing_points, unrelated_points
    ) = comparator.compare(ai_norm, real_norm)

    assert v_comp.alignment == "aligned"
    assert v_comp.score == 100.0


def test_scoring_engine():
    engine = ScoringEngine()
    ai_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_REAL_JUDGMENT)
    real_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_REAL_JUDGMENT)
    comparator = JudgmentComparator()
    (
        v_comp, i_comp, f_comp, c_comp, w_comp,
        e_comp, l_comp, r_comp, fnd_comp, ord_comp,
        *rest
    ) = comparator.compare(ai_norm, real_norm)
    
    scores = engine.calculate_scores(
        verdict_alignment=v_comp.score,
        issue_alignment=i_comp.score,
        factual_accuracy=f_comp.score,
        charge_alignment=c_comp.score,
        witness_alignment=w_comp.score,
        evidence_alignment=e_comp.score,
        legal_alignment=l_comp.score,
        reasoning_alignment=r_comp.score,
        finding_alignment=fnd_comp.score,
        final_order_alignment=ord_comp.score,
    )
    assert isinstance(scores, ComparisonScores)
    assert scores.overall_score >= 70.0
    assert scores.verdict_alignment == 100.0


def test_compare_post_trial_with_case_id():
    service = ComparisonService()
    report = service.compare_post_trial(
        case_id="up_2bcbfb0b616b",
        real_judgment_source=SAMPLE_REAL_JUDGMENT,
    )
    assert isinstance(report, ComparisonReport)
    assert report.scores.overall_score > 0
    assert report.case_id == "up_2bcbfb0b616b"
