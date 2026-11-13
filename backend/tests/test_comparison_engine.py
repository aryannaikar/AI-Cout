"""
Tests for Phase 5 — AI Court Judgment vs Real Court Judgment Comparison Engine.
Validates Post-Trial comparison, upload_id resolution, seven-dimensional scoring,
report generation, and ground truth isolation.
"""

from pathlib import Path
import pytest
from app.comparison.service import ComparisonService
from app.comparison.errors import CaseIdentityMismatchError
from app.comparison.schemas import (
    ComparisonReport, ComparisonScores, NormalizedCharge, NormalizedFact,
    NormalizedJudgment, NormalizedEvidenceItem, NormalizedReasoning,
    OperativeVerdict, StatuteEra,
)
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.comparator import JudgmentComparator
from app.comparison.scoring import ScoringEngine
from app.comparison.report_generator import ComparisonReportGenerator


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
    assert scores.overall_score > 0.0
    assert scores.verdict_alignment == 100.0
    assert scores.weights == {
        "verdict_alignment": 0.20,
        "reasoning_alignment": 0.25,
        "factual_accuracy": 0.15,
        "issue_alignment": 0.10,
        "evidence_alignment": 0.15,
        "charge_alignment": 0.10,
        "final_order_alignment": 0.05,
    }
    assert set(scores.active_weights) == set(scores.weights)
    assert sum(scores.weights.values()) == pytest.approx(1.0)


def test_scoring_engine_uses_fixed_weights_and_excludes_diagnostics():
    engine = ScoringEngine(custom_weights={"verdict_alignment": 1.0})
    scores = engine.calculate_scores(
        verdict_alignment=100, issue_alignment=80, factual_accuracy=60,
        charge_alignment=40, witness_alignment=0, evidence_alignment=80,
        legal_alignment=0, reasoning_alignment=80, finding_alignment=20,
        final_order_alignment=100,
    )
    expected = 100 * .20 + 80 * .25 + 60 * .15 + 80 * .10 + 80 * .15 + 40 * .10 + 100 * .05
    assert scores.overall_score == pytest.approx(expected)
    assert "witness_alignment" not in scores.weights
    assert "legal_alignment" not in scores.weights
    assert "finding_alignment" not in scores.weights


def test_scoring_engine_renormalizes_only_unassessable_core_categories():
    scores = ScoringEngine().calculate_scores(
        verdict_alignment=100, issue_alignment=0, factual_accuracy=100,
        charge_alignment=100, witness_alignment=0, evidence_alignment=100,
        legal_alignment=0, reasoning_alignment=100, finding_alignment=0,
        final_order_alignment=100,
        assessability={"issue_alignment": False},
    )
    assert "issue_alignment" in scores.excluded_categories
    assert "issue_alignment" not in scores.active_weights
    assert sum(scores.active_weights.values()) == pytest.approx(1.0)
    assert scores.active_weight_denominator == pytest.approx(0.90)


def test_dashboard_example_seven_dimension_arithmetic():
    scores = ScoringEngine().calculate_scores(
        verdict_alignment=100, reasoning_alignment=40, factual_accuracy=100,
        issue_alignment=40, evidence_alignment=70, charge_alignment=25,
        final_order_alignment=100, witness_alignment=0, legal_alignment=0,
        finding_alignment=0,
    )
    assert scores.overall_score == 67.0
    assert scores.substantive_score == 58.75


def _judgment(**updates):
    base = dict(
        case_title="Synthetic v. Test", verdict=OperativeVerdict.ACQUITTAL,
        findings={}, material_facts=[], evidence_items=[], reasoning=NormalizedReasoning(),
        raw_text="",
    )
    base.update(updates)
    return NormalizedJudgment(**base)


def test_charge_outcome_normalization_keeps_ingredient_findings_distinct():
    normalize = JudgmentComparator._charge_outcome
    assert normalize("NOT PROVED") == "acquittal"
    assert normalize("Acquittal") == "acquittal"
    assert normalize("Conviction set aside on appeal") == "acquittal"
    assert normalize("Conviction upheld") == "conviction"
    assert normalize("Ingredient of dishonest receipt not proved") is None

    comparator = JudgmentComparator()
    ai = _judgment(findings={"IPC Section 411": "NOT PROVED"})
    real = _judgment(findings={"IPC Section 411": "ACQUITTAL"})
    result = comparator._compare_findings(ai, real, [])
    assert result.score == 100
    assert result.issue_findings[0]["ai_charge_outcome"] == "acquittal"


def test_factual_score_uses_precision_recall_f1_and_counts():
    comparator = JudgmentComparator()
    source_facts = [
        NormalizedFact(statement="Two witnesses identified the accused at the scene."),
        NormalizedFact(statement="The recovered property was identified by its serial number."),
    ]
    ai_facts = [NormalizedFact(statement="Two witnesses identified the accused at the scene.")]
    result = comparator._compare_facts(
        _judgment(material_facts=ai_facts, raw_text="Two witnesses identified the accused at the scene."),
        _judgment(material_facts=source_facts, raw_text="Two witnesses identified the accused at the scene. The recovered property was identified by its serial number."),
        [], [], [],
    )
    assert result.precision == 100
    assert result.recall == 50
    assert result.score == pytest.approx(66.67, abs=0.01)
    assert result.assessed_ai_facts == 1
    assert result.assessed_real_facts == 2


def test_factual_and_evidence_scores_are_unassessable_without_source_inventories():
    comparator = JudgmentComparator()
    ai = _judgment(
        material_facts=[NormalizedFact(statement="A material event occurred at the location.")],
        evidence_items=[NormalizedEvidenceItem(exhibit_id="Ex P-1", description="Document")],
    )
    real = _judgment(raw_text="A judgment without extracted fact or exhibit inventories.")
    fact = comparator._compare_facts(ai, real, [], [], [])
    evidence = comparator._compare_evidence(ai, real, [], [], [])
    assert fact.is_assessable is False and fact.score == 0
    assert fact.precision is None and fact.recall is None
    assert evidence.is_assessable is False and evidence.score == 0


def test_charge_matching_does_not_transfer_another_accuseds_charge():
    comparator = JudgmentComparator()
    ai = _judgment(charges=[NormalizedCharge(
        statute="IPC Section 302", era=StatuteEra.HISTORICAL_IPC_CRPC, accused_name="Accused A"
    )])
    real = _judgment(charges=[NormalizedCharge(
        statute="IPC Section 302", era=StatuteEra.HISTORICAL_IPC_CRPC, accused_name="Accused B"
    )])
    result = comparator._compare_charges(ai, real, [], [], [])
    assert result.matched_charges == []
    assert result.score == 0


def test_reasoning_comparison_uses_source_derived_propositions():
    comparator = JudgmentComparator()
    proposition = "The prosecution did not establish possession because the recovery evidence was inconsistent."
    ai = _judgment(reasoning=NormalizedReasoning(ratio_decidendi=proposition, key_chains=[proposition]))
    real = _judgment(reasoning=NormalizedReasoning(ratio_decidendi=proposition, key_chains=[proposition]))
    result = comparator._compare_reasoning(ai, real, [], [])
    assert result.is_assessable is True
    assert result.score == 100
    assert result.theme_evaluations[0].source_evidence == proposition


def test_case_identity_validation_reports_conflicting_case_numbers_without_blocking():
    service = ComparisonService()
    ai = _judgment(
        case_title="State v. Ramesh Kumar", case_number="Criminal Appeal No. 11/2020",
        presiding_court="High Court of Delhi",
    )
    real = _judgment(
        case_title="State v. Ramesh Kumar", case_number="Criminal Appeal No. 12/2020",
        presiding_court="High Court of Delhi",
    )
    result = service._validate_case_identity(ai, real)
    assert result["status"] == "limited_metadata"
    assert "case_number" in result["note"]


def test_case_identity_validation_does_not_reject_title_only_difference():
    service = ComparisonService()
    ai = _judgment(case_title="State v. Ramesh Kumar")
    real = _judgment(case_title="State v. Ram Kumar")
    result = service._validate_case_identity(ai, real)
    assert result["status"] in {"limited_metadata", "verified"}


def test_case_identity_validation_does_not_reject_weak_metadata_conflicts():
    """Caption/court extraction differences must not block a valid upload."""
    service = ComparisonService()
    ai = _judgment(
        case_title="Sd. Shabuddin v. State of Telangana",
        presiding_court="Supreme Court of India",
    )
    real = _judgment(
        case_title="State of Telangana v. Sk. Shabuddin",
        presiding_court="High Court for the State of Telangana",
    )
    result = service._validate_case_identity(ai, real)
    assert result["status"] == "limited_metadata"
    assert "court" in result["note"]


def test_compare_post_trial_with_case_id():
    service = ComparisonService()
    report = service.compare_post_trial(
        case_id="up_2bcbfb0b616b",
        ai_judgment_source=SAMPLE_REAL_JUDGMENT,
        real_judgment_source=SAMPLE_REAL_JUDGMENT,
    )
    assert isinstance(report, ComparisonReport)
    assert report.scores.overall_score > 0
    assert report.case_id == "up_2bcbfb0b616b"
    txt = ComparisonReportGenerator.format_report_text(report)
    json_report = report.model_dump_json()
    expected_score = f"{report.scores.overall_score:6.2f}%"
    assert expected_score in txt
    assert f'"overall_score":{report.scores.overall_score}' in json_report
    assert "ACTIVE WEIGHT DENOMINATOR" in txt
