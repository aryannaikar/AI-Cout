"""
Phase 5 Tests: Deep Substantive Legal Comparison and Error Detection.
Verifies all 10 comparison dimensions, epistemic classifications, historical-law
applicability checks, and the critical scenario where Verdict is identical but
legal reasoning diverges completely.
"""

from __future__ import annotations

import pytest

from app.comparison.comparator import JudgmentComparator
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.schemas import (
    EpistemicType,
    NormalizedCharge,
    NormalizedFact,
    NormalizedIssue,
    NormalizedJudgment,
    NormalizedReasoning,
    OperativeVerdict,
    StatuteEra,
)
from app.models.judgment_models import Judgment


def test_verdict_alignment_exact_match(synthetic_ai_judgment: Judgment, real_court_judgment_text: str):
    """Verify verdict alignment when both courts reach Acquittal."""
    ai_norm = JudgmentNormalizer.normalize_ai_judgment(synthetic_ai_judgment)
    real_norm = JudgmentNormalizer.normalize_real_judgment(real_court_judgment_text)

    comparator = JudgmentComparator()
    verdict_comp, *_ = comparator.compare(ai_norm, real_norm)

    assert verdict_comp.alignment == "aligned"
    assert verdict_comp.score == 100.0
    assert "aligned" in verdict_comp.explanation.lower()


def test_verdict_alignment_discordance():
    """Verify verdict alignment when AI convicts but Real Court acquitted."""
    ai_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.CONVICTION,
        verdict_raw="CONVICTION",
        final_order="Convicted and sentenced to 3 years RI.",
        reasoning=NormalizedReasoning(ratio_decidendi="Guilt established."),
    )
    real_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        verdict_raw="ACQUITTAL",
        final_order="Acquitted of all charges.",
        reasoning=NormalizedReasoning(ratio_decidendi="Reasonable doubt."),
    )

    comparator = JudgmentComparator()
    verdict_comp, *_, errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert verdict_comp.alignment == "not_aligned"
    assert verdict_comp.score == 0.0
    assert any(e.type == "incorrect_final_order" and e.severity == "critical" for e in errors)


def test_critical_test_case_identical_verdict_divergent_reasoning(
    synthetic_ai_judgment: Judgment, real_court_judgment_text: str
):
    """
    CRITICAL TEST CASE from Specifications:
    Real Court: Acquittal because dock identification was unreliable, no Test Identification
    Parade (TIP) was conducted, vehicle identity was insufficiently proved, and independent
    corroboration was missing.
    AI Court: Acquittal because electronic evidence was inadmissible under Section 63 BSA.

    Expected Result:
    - Verdict Alignment: High / 100%
    - Reasoning Alignment: Low (< 40%)
    - Issue Alignment: Low (< 60%)
    - Errors: Flags unrelated issue (BSA 63), historical law mismatch (IPC vs BNS), and invented evidence (call records).
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

    # 1. Verdict matches
    assert verdict_comp.score == 100.0
    assert verdict_comp.alignment == "aligned"

    # 2. Reasoning is LOW
    assert reasoning_comp.score < 40.0
    assert not reasoning_comp.applied_correct_law

    # 3. Issue alignment penalizes extraneous electronic record issue
    assert issue_comp.score < 60.0
    assert any("electronic" in u.lower() or "bsa" in u.lower() for u in issue_comp.ai_unrelated_issues)

    # 4. Error detection flags spurious ground and historical mismatch
    err_types = [e.type for e in major_errors]
    assert "unrelated_issue" in err_types
    assert "historical_law_mismatch" in err_types
    assert "invented_evidence" in err_types
    assert "unsupported_conclusion" in err_types

    # 5. Check error structure guarantees
    for err in major_errors:
        assert err.severity in ["low", "medium", "high", "critical"]
        assert len(err.ai_claim) > 0
        assert len(err.real_court_position) > 0
        assert len(err.explanation) > 0


def test_factual_accuracy_and_epistemic_inference():
    """
    Verify factual accuracy detects invented facts while correctly distinguishing
    valid judicial inferences.
    """
    ai_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        material_facts=[
            NormalizedFact(
                statement="Accused was found driving scooter at police barricade.",
                epistemic_type=EpistemicType.FACT,
            ),
            NormalizedFact(
                statement="Absence of independent panch witnesses implies possibility of recovery being planted.",
                epistemic_type=EpistemicType.INFERENCE,  # Valid inference, not a hallucinated fact
            ),
            NormalizedFact(
                statement="Accused admitted guilt to the police commissioner in a written letter.",
                epistemic_type=EpistemicType.FACT,  # Invented fact
            ),
        ],
        reasoning=NormalizedReasoning(ratio_decidendi="Reasonable doubt."),
    )
    real_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        raw_text="The accused was driving a scooter when intercepted. No independent public witnesses joined.",
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )

    comparator = JudgmentComparator()
    _, _, fact_comp, *_, major_errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert len(fact_comp.invented_facts) >= 1
    assert any("commissioner" in f.lower() for f in fact_comp.invented_facts)
    # The valid inference is NOT flagged as an invented fact
    assert not any("implies possibility" in f.lower() for f in fact_comp.invented_facts)
    assert any(e.type == "hallucinated_fact" for e in major_errors)


def test_charge_alignment_and_historical_applicability():
    """
    Verify charge comparison flags substitution of modern BNS for historical IPC.
    """
    ai_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        charges=[
            NormalizedCharge(statute="Section 317 BNS", era=StatuteEra.MODERN_BNS_BNSS_BSA, offence="Stolen property"),
            NormalizedCharge(statute="Section 66 IT Act", era=StatuteEra.SPECIAL_ACT, offence="Hacking"),  # Unrelated charge
        ],
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )
    real_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        charges=[
            NormalizedCharge(statute="Section 411 IPC", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Stolen property"),
        ],
        raw_text="Prosecuted under Section 411 IPC (Indian Penal Code).",
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )

    comparator = JudgmentComparator()
    _, _, _, charge_comp, *_, major_errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert len(charge_comp.historical_law_mismatches) >= 1
    assert any("historical" in hm.lower() for hm in charge_comp.historical_law_mismatches)
    assert len(charge_comp.incorrectly_introduced_charges) >= 1
    assert any("66" in ic for ic in charge_comp.incorrectly_introduced_charges)


def test_witness_misattribution_detection():
    """Verify detection when substantive testimony is misattributed to another witness."""
    ai_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        prosecution_witnesses=[
            JudgmentNormalizer._extract_witnesses_from_text("PW-1 stated he examined the ballistic weapon and test fired bullets.")[0],
        ],
        reasoning=NormalizedReasoning(ratio_decidendi="Weapon test."),
    )
    real_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted",
        prosecution_witnesses=[
            JudgmentNormalizer._extract_witnesses_from_text("PW-1 Head Constable Ram Singh deposed he was on barricade checking duty.")[0],
        ],
        reasoning=NormalizedReasoning(ratio_decidendi="Barricade duty."),
    )

    comparator = JudgmentComparator()
    _, _, _, _, witness_comp, *_, major_errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert len(witness_comp.misattributed_testimony) >= 1
    assert any(e.type == "incorrect_witness_statement" for e in major_errors)
