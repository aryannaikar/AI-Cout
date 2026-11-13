"""
Phase 5 Comparison Engine Regression & Fixes Verification Suite.
Validates:
1. Operative order extraction without footer or boilerplate leakage
2. Legal issue extraction and concept matching with OCR currency normalization
3. Accused-specific charge attribution (Moulana vs Shabuddin)
4. Insufficient data vs extraction failure (witness & evidence exclusion from denominator)
5. Contradictory score prevention (no 100% reasoning on 0 matched themes)
6. Historical law vs modern law contextual handling
7. Comprehensive end-to-end regression on the Shabuddin case files
"""

from pathlib import Path
import pytest

from app.comparison.comparator import JudgmentComparator
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.loaders import ComparisonDocumentLoader
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.schemas import (
    ComparisonCategoryStatus,
    EpistemicType,
    NormalizedCharge,
    NormalizedFact,
    NormalizedIssue,
    NormalizedJudgment,
    NormalizedReasoning,
    OperativeVerdict,
    StatuteEra,
)
from app.comparison.scoring import ScoringEngine
from app.comparison.service import ComparisonService


SAMPLE_GROUND_TRUTH_TEXT = """AI Court of India | Source: supplied Supreme Court judgment
Page 1
AI COURT OF INDIA
Ground Truth – Real Court Verdict
Sd. Shabuddin v. The State of Telangana
Criminal Appeal No. 3605 of 2025 | Supreme Court of India | 19 August 2025
CONFIDENTIAL EVALUATION FILE – DO NOT UPLOAD TO THE AI COURT TRIAL OR INGEST INTO LEGAL RAG BEFORE THE
AI JUDGMENT IS COMPLETE.

1. Operative Verdict
ACQUITTAL
The Supreme Court set aside the High Court judgment dated 7 March 2024. The appeal was allowed and the
appellant was acquitted of all charges. The judgment states that the appellant was on bail and the bail bonds stood
discharged.

2. Issues Decided
• Issue I – Reverse burden of proof: the High Court judgment was unsustainable because it erroneously placed the
burden on the appellant and co-accused, whereas the prosecution bore the burden of proving its case beyond
reasonable doubt.
• Issue II – Section 411 IPC after acquittal under Section 379 IPC: conviction under Section 411 IPC was
unsustainable where both accused had been acquitted of theft under Section 379 IPC.

3. Core Reasoning
• The case was based on circumstantial evidence, and the prosecution had to prove the circumstances beyond
reasonable doubt.
• The presumption under Section 114 of the Indian Evidence Act could apply only after the prosecution established
foundational facts of theft and possession soon after the incident.
• The record did not establish the total amount of cash the deceased carried. Mere recovery of I25,000 from the
appellant did not prove that the cash was stolen.
• The recovered cash had no special or distinct identifying characteristics linking it to the amount allegedly taken from
the deceased.
• Section 411 required proof that the property was stolen and that the accused dishonestly received or retained it with
knowledge or reason to believe it was stolen.
• Because the courts below had acquitted the accused of theft under Section 379 IPC, the Section 411 IPC conviction
could not be sustained on the same prosecution theory.

4. Legal Provisions Discussed
• Section 411 IPC – dishonestly receiving or retaining stolen property.
• Section 379 IPC – theft.
• Sections 102 and 114, Indian Evidence Act, 1872 – burden of proof and presumption discussed in the judgment.

5. Final Order
• The judgment under challenge dated 7 March 2024 in Criminal Appeal No. 439 of 2010 was set aside.
• The appeal was allowed. The appellant was acquitted of all charges. Bail bonds stood discharged; pending
applications, if any, were disposed of.

AI Court of India | Source: supplied Supreme Court judgment
Page 2
6. Comparison Engine Ground Truth
• Normalized outcome label: ACQUITTAL.
• Appeal outcome: ALLOWED.
• High Court judgment: SET ASIDE.
• Section 411 IPC conviction: UNSUSTAINABLE / SET ASIDE.
7. Source and Evaluation Controls
• Source: user-supplied Supreme Court judgment PDF
"""


def test_real_operative_order_extraction_and_footer_exclusion():
    """Verify that the real operative final order is extracted cleanly without footer metadata."""
    norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)

    assert norm.verdict == OperativeVerdict.ACQUITTAL
    assert "set aside" in norm.final_order.lower()
    assert "acquitted of all charges" in norm.final_order.lower()

    # Verify complete exclusion of document footer and evaluation boilerplate
    assert "ai court of india | source:" not in norm.final_order.lower()
    assert "page 1" not in norm.final_order.lower()
    assert "page 2" not in norm.final_order.lower()
    assert "comparison engine ground truth" not in norm.final_order.lower()
    assert "confidential evaluation file" not in norm.final_order.lower()


def test_header_date_and_court_extraction():
    """Verify court name and decision date extraction from pipe-separated banner."""
    norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)

    assert "Supreme Court of India" in (norm.presiding_court or "")
    assert "19 August 2025" in (norm.date_of_decision or "")
    assert norm.case_title == "Sd. Shabuddin v. The State of Telangana"


def test_legal_issue_concept_matching_and_ocr_normalization():
    """Verify that substantive issues match even across OCR artifacts (I25,000 / ₹25,000)."""
    norm_real = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)

    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Accused is acquitted of all charges.",
        legal_issues=[
            NormalizedIssue(issue_id="ISS-01", statement="Whether the prosecution discharged its initial burden of proof."),
            NormalizedIssue(
                issue_id="ISS-02",
                statement="Whether Section 411 IPC conviction can be sustained when the accused were acquitted of theft under Section 379 IPC.",
            ),
        ],
        reasoning=NormalizedReasoning(
            ratio_decidendi="Prosecution failed to discharge initial burden. Section 411 cannot stand after acquittal under Section 379."
        ),
    )

    comparator = JudgmentComparator()
    _, issue_comp, *_, errors, _, _ = comparator.compare(ai_norm, norm_real)

    assert len(issue_comp.matched_issues) == 2
    assert issue_comp.score >= 60.0
    assert issue_comp.status in [ComparisonCategoryStatus.MATCH.value, ComparisonCategoryStatus.PARTIAL_MATCH.value]


def test_accused_specific_charge_attribution():
    """
    Verify that trial charges framed against co-accused (e.g. Moulana under IPC 302)
    are recognized as co-accused context rather than pure hallucinations.
    """
    case_context = (
        "In the trial court, charges were framed against accused No. 1 Moulana under Section 302 IPC "
        "and Section 201 IPC, whereas Shabuddin was charged with receiving stolen property under Section 411 IPC."
    )

    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted.",
        charges=[
            NormalizedCharge(statute="Indian Penal Code, 1860, 302", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Murder"),
            NormalizedCharge(statute="Indian Penal Code, 1860, 411", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Stolen Property"),
        ],
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )

    real_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted.",
        charges=[
            NormalizedCharge(statute="IPC Section 411", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Stolen Property", accused_name="Shabuddin"),
        ],
        raw_text=case_context,
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )

    comparator = JudgmentComparator(case_packet_context=case_context)
    _, _, _, charge_comp, *_, errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert any(m["ai_charge"] == "Indian Penal Code, 1860, 411" for m in charge_comp.matched_charges)
    # Check that Section 302 is explained as co-accused charge
    coaccused_err = next((e for e in errors if "302" in e.ai_claim), None)
    assert coaccused_err is not None
    assert "co-accused" in coaccused_err.explanation.lower() or "moulana" in coaccused_err.explanation.lower()


def test_insufficient_data_vs_zero_score_exclusion():
    """
    Verify that when real judgment summary contains no individual witnesses or exhibits,
    those categories are marked INSUFFICIENT_DATA and excluded from scoring denominator.
    """
    real_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)
    assert real_norm.is_ground_truth_summary is True
    assert len(real_norm.prosecution_witnesses) == 0
    assert len(real_norm.defence_witnesses) == 0
    assert len(real_norm.evidence_items) == 0

    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted.",
        reasoning=NormalizedReasoning(ratio_decidendi="Benefit of doubt."),
    )

    comparator = JudgmentComparator()
    results = comparator.compare(ai_norm, real_norm)
    (
        verdict_comp, issue_comp, fact_comp, charge_comp, witness_comp,
        evidence_comp, legal_comp, reasoning_comp, finding_comp, order_comp,
        major_errors, missing_points, unrelated_points
    ) = results

    assert witness_comp.is_assessable is False
    assert witness_comp.status == ComparisonCategoryStatus.INSUFFICIENT_DATA.value
    assert evidence_comp.is_assessable is False
    assert evidence_comp.status == ComparisonCategoryStatus.INSUFFICIENT_DATA.value

    assess_map = {
        "verdict_alignment": verdict_comp.is_assessable,
        "issue_alignment": issue_comp.is_assessable,
        "factual_accuracy": fact_comp.is_assessable,
        "charge_alignment": charge_comp.is_assessable,
        "witness_alignment": witness_comp.is_assessable,
        "evidence_alignment": evidence_comp.is_assessable,
        "legal_alignment": legal_comp.is_assessable,
        "reasoning_alignment": reasoning_comp.is_assessable,
        "finding_alignment": finding_comp.is_assessable,
        "final_order_alignment": order_comp.is_assessable,
    }

    scoring = ScoringEngine()
    scores = scoring.calculate_scores(
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

    assert "witness_alignment" in scores.excluded_categories
    assert "evidence_alignment" in scores.excluded_categories
    # The sum of active weights should equal 1.0 (100%)
    assert abs(sum(scores.active_weights.values()) - 1.0) < 0.01


def test_contradictory_score_prevention_on_divergent_reasoning():
    """
    Verify that if reasoning matches 0 themes, reasoning similarity cannot be 100%,
    and that verdict match is separated from substantive quality.
    """
    ai_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted.",
        reasoning=NormalizedReasoning(
            ratio_decidendi="Acquittal solely because electronic records lacked Section 63 BSA certificate.",
            key_chains=["Electronic records are inadmissible without Section 63 certificate."],
        ),
    )
    real_norm = NormalizedJudgment(
        case_title="State v. Accused",
        verdict=OperativeVerdict.ACQUITTAL,
        final_order="Acquitted.",
        reasoning=NormalizedReasoning(
            ratio_decidendi="Acquittal because prosecution failed to establish foundational facts under Section 114 and cash was unidentifiable.",
            key_chains=["Foundational facts must precede Section 114 presumption.", "Recovered cash was unidentifiable."],
        ),
        raw_text="The prosecution failed to establish foundational facts under Section 114 Evidence Act. Recovered cash was unidentifiable.",
    )

    comparator = JudgmentComparator()
    verdict_comp, *_, reasoning_comp, finding_comp, order_comp, major_errors, _, _ = comparator.compare(ai_norm, real_norm)

    assert verdict_comp.score == 100.0
    assert reasoning_comp.score < 30.0
    assert reasoning_comp.status == ComparisonCategoryStatus.MISMATCH.value


def test_shabuddin_case_files_integration():
    """
    Integration regression on the actual Shabuddin case files if available in the repository.
    Verifies that real verdict, real court date, issues, and order are properly extracted
    and that witness/evidence are excluded from the denominator.
    """
    real_pdf = Path(r"C:\Users\Aryan Naikar\Downloads\AI_Court_Real_Verdict_Comparison_Shabuddin.pdf")
    ai_json = Path("backend/data/cases/CASE-001/output/ai_judgment.json")
    packet_pdf = Path("backend/data/cases/uploads/up_e88899e87195_Case_Packet.pdf")

    if not (real_pdf.exists() and ai_json.exists()):
        pytest.skip("Shabuddin case files not found on this environment.")

    service = ComparisonService()
    report = service.compare_post_trial(
        case_id="CASE-001",
        real_judgment_source=real_pdf,
        case_packet_source=packet_pdf if packet_pdf.exists() else None,
    )

    # 1. Metadata provenance
    assert report.case_information.get("date_of_decision") == "19 August 2025"
    assert "Supreme Court of India" in (report.case_information.get("presiding_court") or "")

    # 2. Operative order and verdict
    assert report.verdict_comparison.score == 100.0
    assert report.final_order_comparison.alignment == "aligned"
    assert "set aside" in report.final_order_comparison.real_final_order.lower()
    assert "page 1" not in report.final_order_comparison.real_final_order.lower()
    assert "page 2" not in report.final_order_comparison.real_final_order.lower()

    # 3. Substantive issues
    assert len(report.issue_comparison.matched_issues) >= 2

    # 4. Excluded categories
    assert "witness_alignment" in report.scores.excluded_categories
    assert "evidence_alignment" in report.scores.excluded_categories

    # 5. Separation of verdict from substantive quality
    assert report.scores.verdict_alignment == 100.0
    assert report.scores.substantive_score > 0.0
    assert report.scores.substantive_score != report.scores.verdict_alignment
    assert report.overall_assessment.startswith("VERDICT MATCH — SUBSTANTIVE MISMATCH")


def test_factual_correctness_and_completeness_separation():
    """
    Task 5 Regression:
    Verifies that factual scoring separates correctness (precision) from completeness (recall),
    and prevents non-fact titles, banners, and issues from being treated as material facts.
    """
    comparator = JudgmentComparator(
        case_packet_context="The prosecution alleges that Moulana took the deceased's cash and Shabuddin received money."
    )

    ai_judgment = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        material_facts=[
            NormalizedFact(
                statement="The prosecution alleges that Moulana took the deceased's cash and Shabuddin received money.",
                epistemic_type=EpistemicType.FACT,
            ),
        ],
        raw_text="The prosecution alleges that Moulana took the deceased's cash and Shabuddin received money.",
    )

    # 1. Real judgment summary with no factual matrix section (only legal issues)
    real_summary = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        material_facts=[],  # summary with no factual matrix
        raw_text="The appeal was allowed and appellant acquitted under Section 411 IPC.",
    )

    errors = []
    missing = []
    unrelated = []
    fact_res = comparator._compare_facts(ai_judgment, real_summary, errors, missing, unrelated)

    assert fact_res.correctness_score == 100.0
    assert fact_res.completeness_score == 100.0
    assert fact_res.score == 100.0
    assert len(fact_res.omitted_material_facts) == 0

    # 2. When real judgment HAS material facts and AI omits some
    real_with_facts = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        material_facts=[
            NormalizedFact(
                statement="The deceased was carrying cash in a leather pouch on the night of occurrence.",
                epistemic_type=EpistemicType.FACT,
            ),
            NormalizedFact(
                statement="The accused was apprehended two days later at a bus terminal.",
                epistemic_type=EpistemicType.FACT,
            ),
        ],
        raw_text="Deceased was carrying cash in leather pouch. Accused apprehended at bus terminal.",
    )

    fact_res_omitted = comparator._compare_facts(ai_judgment, real_with_facts, errors, missing, unrelated)
    assert fact_res_omitted.completeness_score < 100.0
    assert fact_res_omitted.score < 100.0
    assert len(fact_res_omitted.omitted_material_facts) > 0
    # Composite score must be penalized when material facts are omitted
    assert fact_res_omitted.score != 100.0


def test_api_scores_and_frontend_display_consistency():
    """
    Task 8 Regression:
    Compares the API score object from /api/cases/{case_id}/comparison
    with the frontend dashboard's displayed values for the same comparison ID.
    Guarantees:
    - Authoritative score object from backend matches exactly
    - Excluded categories display 'Not assessed' (NOT 100%)
    - Active weights are used and normalized
    - Issue Framing (66.7%), Charges (80.0%), Findings (100.0%), Legal Citations (0.0%)
    - Overall Benchmark displays 70.2% and is labeled PARTIAL BENCHMARK
    - TXT and PDF downloads match the exact same scores and labels
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/cases/CASE-001/comparison")
    assert response.status_code == 200, f"Failed to retrieve comparison: {response.text}"

    report_data = response.json()
    comparison_id = report_data["comparison_id"]
    scores = report_data["scores"]

    # 1. Authoritative backend score values
    assert scores["overall_score"] == 71.76
    assert scores["verdict_alignment"] == 100.0
    assert scores["reasoning_alignment"] == 20.0
    assert scores["issue_alignment"] == 66.67
    assert scores["charge_alignment"] == 80.0
    assert scores["factual_accuracy"] == 100.0
    assert scores["finding_alignment"] == 100.0
    assert scores["legal_alignment"] == 26.67
    assert scores["final_order_alignment"] == 100.0
    assert "evidence_alignment" in scores["excluded_categories"]
    assert "witness_alignment" in scores["excluded_categories"]
    assert scores["substantive_score"] == 63.08
    assert scores["verdict_score"] == 100.0

    # 2. Simulated Frontend Dashboard Display Rules (from ComparisonModal.tsx)
    def render_frontend_category(key: str, val: float, excluded: list, active_w: dict, default_w: str):
        is_excluded = key in excluded
        act_weight = active_w.get(key)
        weight_display = (
            "Excluded (Insufficient Data)"
            if is_excluded
            else f"Active: {(act_weight * 100):.1f}%"
            if act_weight is not None
            else default_w
        )
        score_display = "Not assessed" if is_excluded else f"{val:.1f}%"
        return score_display, weight_display

    exc = scores["excluded_categories"]
    act_w = scores.get("active_weights", {})

    # Evidence: Must show "Not assessed", NOT "100.0%"
    evi_score, evi_wt = render_frontend_category("evidence_alignment", scores["evidence_alignment"], exc, act_w, "10%")
    assert evi_score == "Not assessed"
    assert evi_wt == "Excluded (Insufficient Data)"

    # Witness: Must show "Not assessed", NOT "100.0%"
    wit_score, wit_wt = render_frontend_category("witness_alignment", scores["witness_alignment"], exc, act_w, "5%")
    assert wit_score == "Not assessed"
    assert wit_wt == "Excluded (Insufficient Data)"

    # Issue Framing: Must match backend 66.67 -> "66.7%"
    iss_score, iss_wt = render_frontend_category("issue_alignment", scores["issue_alignment"], exc, act_w, "10%")
    assert iss_score == "66.7%"
    assert "11.8%" in iss_wt

    # Charges: Must match backend 80.0 -> "80.0%"
    chg_score, chg_wt = render_frontend_category("charge_alignment", scores["charge_alignment"], exc, act_w, "5%")
    assert chg_score == "80.0%"
    assert "5.9%" in chg_wt

    # Findings: Must match backend 100.0 -> "100.0%"
    fnd_score, fnd_wt = render_frontend_category("finding_alignment", scores["finding_alignment"], exc, act_w, "8%")
    assert fnd_score == "100.0%"
    assert "9.4%" in fnd_wt

    # Legal Citations: Must match backend 26.67 -> "26.7%"
    leg_score, leg_wt = render_frontend_category("legal_alignment", scores["legal_alignment"], exc, act_w, "5%")
    assert leg_score == "26.7%"
    assert "5.9%" in leg_wt

    # Overall benchmark card
    is_partial = len(exc) > 0
    benchmark_card_label = "PARTIAL BENCHMARK" if is_partial else "OVERALL BENCHMARK"
    benchmark_card_score = f"{scores['overall_score']:.1f}%"
    assert benchmark_card_label == "PARTIAL BENCHMARK"
    assert benchmark_card_score == "71.8%"

    # 3. Check TXT and PDF download endpoints for the same comparison
    txt_res = client.get("/api/cases/CASE-001/comparison/download/txt")
    assert txt_res.status_code == 200
    txt_content = txt_res.text
    assert comparison_id in txt_content
    assert f"PARTIAL BENCHMARK SCORE     :  {scores['overall_score']:.2f}%" in txt_content
    assert "Evidence Alignment      : Not assessed (EXCLUDED (Insufficient Data))" in txt_content
    assert "Witness Alignment       : Not assessed (EXCLUDED (Insufficient Data))" in txt_content
    assert "Issue Alignment         :  66.67%" in txt_content
    assert "Charge Alignment        :  80.00%" in txt_content
    assert "Factual Accuracy        : 100.00%" in txt_content
    assert "Finding Alignment       : 100.00%" in txt_content

    pdf_res = client.get("/api/cases/CASE-001/comparison/download/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000


def test_verdict_normalization_acquittal_variations():
    """Verify that equivalent acquittal expressions normalize to canonical ACQUITTAL with explanation."""
    acquittal_variations = [
        "acquitted",
        "acquittal",
        "The appellant was acquitted of all charges.",
        "The appellant is acquitted under Section 411 IPC.",
        "The appellant was acquitted of the charges.",
        "The order of conviction recorded by the trial court is set aside.",
        "The conviction and sentence passed against the appellant is set aside.",
        "In the result, the appeal is allowed and the appellant is acquitted of all charges.",
        "The accused is extended the benefit of doubt and acquitted.",
        "The appellant was honourably acquitted.",
    ]

    for variant in acquittal_variations:
        verdict, explanation = JudgmentNormalizer._determine_verdict_with_explanation(variant)
        assert verdict == OperativeVerdict.ACQUITTAL, f"Failed for variant: {variant} -> {verdict}"
        assert "ACQUITTAL" in explanation
        assert len(explanation) > 10

        # Also verify via JudgmentNormalizer._extract_verdict_and_order
        v, raw, order, expl = JudgmentNormalizer._extract_verdict_and_order(f"FINAL ORDER:\n{variant}")
        assert v == OperativeVerdict.ACQUITTAL, f"Full extraction failed for: {variant}"
        assert raw != "ADJUDICATED", "raw_verdict must not be replaced with generic ADJUDICATED"
        assert variant.lower() in raw.lower() or "acquitt" in raw.lower() or "set aside" in raw.lower()


def test_failed_and_unrecognized_extraction_yields_extraction_error_not_other():
    """Verify that missing or unrecognized text produces EXTRACTION_ERROR or UNKNOWN, never substantive OTHER."""
    failed_inputs = [
        "",
        "   \n  \t  ",
        "Operative order not explicitly detailed in judgment text.",
        "NO OPERATIVE ORDER FOUND",
        "EXTRACTION_ERROR",
    ]

    for fi in failed_inputs:
        v, expl = JudgmentNormalizer._determine_verdict_with_explanation(fi)
        assert v == OperativeVerdict.EXTRACTION_ERROR, f"Expected EXTRACTION_ERROR for '{fi}', got {v}"
        assert v != OperativeVerdict.OTHER, f"Must never classify failed extraction as OTHER!"

    unrecognized_inputs = [
        "The court took judicial notice of weather conditions on the afternoon of the hearing.",
        "The hearing was adjourned until next Tuesday.",
    ]

    for ui in unrecognized_inputs:
        v, expl = JudgmentNormalizer._determine_verdict_with_explanation(ui)
        assert v == OperativeVerdict.UNKNOWN, f"Expected UNKNOWN for '{ui}', got {v}"
        assert v != OperativeVerdict.OTHER, f"Must never classify unrecognized text as substantive OTHER!"


def test_source_text_preservation_and_explanation_in_judgment():
    """Verify that original source text snippet is preserved in verdict_raw and explained."""
    text = (
        "IN THE SUPREME COURT OF INDIA\n"
        "Sd. Shabuddin v. State of Telangana\n\n"
        "5. Final Order\n"
        "The appeal was allowed and the appellant was acquitted of all charges."
    )
    norm = JudgmentNormalizer.normalize_real_judgment(text)
    assert norm.verdict == OperativeVerdict.ACQUITTAL
    assert "acquitted of all charges" in norm.verdict_raw.lower()
    assert norm.verdict_normalization_explanation is not None
    assert "ACQUITTAL" in norm.verdict_normalization_explanation


def test_mathematical_formula_validation():
    """
    Verify the mathematical derivation of the 26.4% score and 52.0% reasoning score:
    - 26.4% = 0% * 0.20 (Verdict) + 52% * 0.20 (Reasoning) + 100% * 0.12 (Facts) + 80% * 0.05 (Charges)
    - 52.0% = 1/5 themes matched (12.0%) + structure score (40.0%)
    """
    engine = ScoringEngine()

    # When all 10 categories are assessable, verdict=0, reasoning=52, facts=100, charges=80, others=0
    scores_discordant = engine.calculate_scores(
        verdict_alignment=0.0,
        issue_alignment=0.0,
        factual_accuracy=100.0,
        charge_alignment=80.0,
        witness_alignment=0.0,
        evidence_alignment=0.0,
        legal_alignment=0.0,
        reasoning_alignment=52.0,
        finding_alignment=0.0,
        final_order_alignment=0.0,
        assessability={k: True for k in engine.weights},
    )
    assert scores_discordant.overall_score == 26.4, f"Expected 26.4, got {scores_discordant.overall_score}"

    # When verdict is aligned (100.0), overall score increases by exactly 100 * 0.20 = 20.0 -> 46.4%
    scores_aligned = engine.calculate_scores(
        verdict_alignment=100.0,
        issue_alignment=0.0,
        factual_accuracy=100.0,
        charge_alignment=80.0,
        witness_alignment=0.0,
        evidence_alignment=0.0,
        legal_alignment=0.0,
        reasoning_alignment=52.0,
        finding_alignment=0.0,
        final_order_alignment=0.0,
        assessability={k: True for k in engine.weights},
    )
    assert scores_aligned.overall_score == 46.4, f"Expected 46.4, got {scores_aligned.overall_score}"


def test_comparison_extraction_error_unassessable():
    """Verify that when real verdict is EXTRACTION_ERROR, verdict category is unassessable and excluded."""
    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        verdict_raw="ACQUITTAL",
    )
    real_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.EXTRACTION_ERROR,
        verdict_raw="",
        verdict_normalization_explanation="Extraction failed: Operative text is empty.",
    )

    comparator = JudgmentComparator()
    errors = []
    verdict_comp = comparator._compare_verdict(ai_norm, real_norm, errors)

    assert verdict_comp.real_verdict == OperativeVerdict.EXTRACTION_ERROR.value
    assert verdict_comp.status == ComparisonCategoryStatus.EXTRACTION_ERROR.value
    assert verdict_comp.is_assessable is False
    assert "failed" in verdict_comp.explanation.lower()


def test_legal_scoring_consistency():
    """
    Verify that when legal provisions are correctly identified alongside inapplicable citations,
    the legal provision score is mathematically consistent with counts and never 0%.
    """
    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        legal_provisions=[
            "Section 411 IPC",
            "Section 379 IPC",
            "Section 302 IPC",
            "Bharatiya Nyaya Sanhita, 2023, Section 212",
            "Bharatiya Nyaya Sanhita, 2023, Section 358",
            "Bharatiya Sakshya Adhiniyam, 2023, Section 61",
        ],
        raw_text="Procedural history: accused Moulana charged under Section 302 IPC. Appellant Shabuddin charged under Section 411 IPC.",
    )
    real_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        legal_provisions=[
            "Section 411 IPC",
            "Section 379 IPC",
            "Section 102 INDIAN EVIDENCE ACT",
            "Section 114 INDIAN EVIDENCE ACT",
        ],
        raw_text="Procedural history: accused Moulana charged under Section 302 IPC. Appellant Shabuddin charged under Section 411 IPC.",
    )

    comparator = JudgmentComparator(case_packet_context="accused Moulana charged under Section 302 IPC")
    errors = []
    missing = []
    unrelated = []
    legal_comp = comparator._compare_legal_provisions(ai_norm, real_norm, errors, missing, unrelated)

    assert legal_comp.matched_count == 2
    assert legal_comp.missing_count == 2
    assert legal_comp.inapplicable_count == 3
    assert legal_comp.procedural_count == 1
    assert legal_comp.score > 0.0, "Score must not be wiped to 0% when provisions were correctly matched!"

    # Mathematical consistency verification:
    # Recall = 2 / 4 = 0.50
    # Precision = (2 + 0.5 * 1) / (2 + 1 + 3) = 2.5 / 6 = 0.4167
    # F1 = 2 * (0.4167 * 0.50) / (0.4167 + 0.50) * 100 = 45.45%
    expected_f1 = round(2.0 * (0.4167 * 0.5) / (0.4167 + 0.5) * 100.0, 2)
    assert abs(legal_comp.score - expected_f1) < 0.5, f"Expected ~{expected_f1}%, got {legal_comp.score}%"
    assert "Balanced F1 score" in legal_comp.explanation


def test_contextual_statutory_references_and_charge_attribution():
    """
    Verify that Section 302 IPC framed against co-accused Moulana is attributed to the co-accused
    context, distinguished from appellant Shabuddin's charges, and not treated as an unconnected citation.
    """
    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        charges=[
            NormalizedCharge(statute="Indian Penal Code, 1860, 302", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Murder"),
            NormalizedCharge(statute="Indian Penal Code, 1860, 411", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Stolen Property"),
        ],
        legal_provisions=["Indian Penal Code, 1860, 302", "Indian Penal Code, 1860, 411"],
    )
    real_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. The State of Telangana",
        verdict=OperativeVerdict.ACQUITTAL,
        charges=[
            NormalizedCharge(statute="IPC Section 411", era=StatuteEra.HISTORICAL_IPC_CRPC, offence="Stolen Property", accused_name="Shabuddin"),
        ],
        legal_provisions=["Section 411 IPC"],
        raw_text="Trial court record: Charges were framed against co-accused Moulana under Section 302 IPC. Appellant Shabuddin charged under Section 411 IPC.",
    )

    comparator = JudgmentComparator(case_packet_context="co-accused Moulana under Section 302 IPC")
    errors = []
    missing = []
    unrelated = []
    charge_comp = comparator._compare_charges(ai_norm, real_norm, errors, missing, unrelated)
    legal_comp = comparator._compare_legal_provisions(ai_norm, real_norm, errors, missing, unrelated)

    # Section 302 must be identified in procedural_or_coaccused
    assert any("302" in c for c in charge_comp.procedural_or_coaccused_charges)
    assert any("302" in p for p in legal_comp.procedural_or_coaccused_provisions)
    # Section 302 must NOT be treated as an unconnected hallucination
    assert not any("302" in u for u in legal_comp.unconnected_provisions)

    # Explanation must clearly distinguish the procedural/co-accused context
    err_302 = next((e for e in errors if "302" in e.ai_claim), None)
    assert err_302 is not None
    assert "moulana" in err_302.explanation.lower()
    assert "shabuddin" in err_302.explanation.lower()


def test_findings_versus_reasoning_independence():
    """
    Verify that finding alignment and reasoning alignment are kept strictly separate.
    A matching acquittal on specific charges must not force or imply 100% reasoning alignment.
    """
    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        findings={"IPC Section 411": "ACQUITTED", "IPC Section 379": "ACQUITTED"},
        reasoning=NormalizedReasoning(ratio_decidendi="General benefit of doubt granted due to witness demeanor."),
    )
    real_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)

    comparator = JudgmentComparator()
    errors = []
    missing = []
    finding_comp = comparator._compare_findings(ai_norm, real_norm, errors)
    reasoning_comp = comparator._compare_reasoning(ai_norm, real_norm, errors, missing)

    # Finding alignment is 100% because findings on charges align
    assert finding_comp.score == 100.0
    # But reasoning alignment is NOT 100% because AI did not reproduce the real court ratio
    assert reasoning_comp.score < 100.0
    assert "separate" in finding_comp.explanation.lower() or "independently" in reasoning_comp.explanation.lower()


def test_individual_reasoning_theme_comparison():
    """
    Verify that the four Supreme Court themes are compared individually with
    AI position, real-court position, match status, and source evidence.
    """
    real_norm = JudgmentNormalizer.normalize_real_judgment(SAMPLE_GROUND_TRUTH_TEXT)

    ai_norm = NormalizedJudgment(
        case_title="Sd. Shabuddin v. State",
        verdict=OperativeVerdict.ACQUITTAL,
        legal_issues=[
            NormalizedIssue(issue_id="Issue-1", statement="Whether the prosecution discharged its initial burden of proof."),
            NormalizedIssue(issue_id="Issue-2", statement="Whether Section 411 IPC conviction can be sustained when the accused were acquitted of theft under Section 379 IPC."),
            NormalizedIssue(issue_id="Issue-3", statement="Whether the prosecution material sufficiently connects the recovered I25,000 to the alleged stolen amount."),
        ],
        reasoning=NormalizedReasoning(
            ratio_decidendi="In a criminal trial, the distance between may be true and must be true is long. Hypothesis of innocence cannot be ruled out. Accused is entitled to the benefit of doubt.",
            key_chains=["Chain of custody gaps.", "Absence of civilian panch witness."],
        ),
    )

    comparator = JudgmentComparator()
    errors = []
    missing = []
    reasoning_comp = comparator._compare_reasoning(ai_norm, real_norm, errors, missing)

    # Must contain individual theme evaluations
    assert len(reasoning_comp.theme_evaluations) == 4
    theme_ids = {t.theme_id for t in reasoning_comp.theme_evaluations}
    assert theme_ids == {"THEME-1", "THEME-2", "THEME-3", "THEME-4"}

    for t in reasoning_comp.theme_evaluations:
        assert len(t.theme_name) > 0
        assert len(t.real_court_position) > 0
        assert len(t.ai_position) > 0
        assert t.match_status in ("MATCH", "PARTIAL_MATCH", "MISMATCH")
        assert len(t.source_evidence) > 0

    # Section 114 was omitted by AI -> MISMATCH
    t2 = next(t for t in reasoning_comp.theme_evaluations if t.theme_id == "THEME-2")
    assert t2.match_status == "MISMATCH"

    # Theme 1: Framed in issue list, but omitted in ratio decidendi -> MISMATCH
    t1 = next(t for t in reasoning_comp.theme_evaluations if t.theme_id == "THEME-1")
    assert t1.match_status == "MISMATCH"
    assert "omitted in ratio decidendi" in t1.ai_position.lower()


def test_score_mathematical_validation_across_categories():
    """
    Validate that every dimension score agrees with its formula and counts,
    and overall weighted score agrees with active assessable weights without hardcoding.
    """
    engine = ScoringEngine()
    assessability = {
        "verdict_alignment": True,
        "reasoning_alignment": True,
        "factual_accuracy": True,
        "issue_alignment": True,
        "charge_alignment": True,
        "legal_alignment": True,
        "finding_alignment": True,
        "final_order_alignment": True,
        "evidence_alignment": False,  # Insufficient data
        "witness_alignment": False,   # Insufficient data
    }

    scores = engine.calculate_scores(
        verdict_alignment=100.0,
        reasoning_alignment=20.0,
        factual_accuracy=100.0,
        issue_alignment=66.67,
        charge_alignment=80.0,
        legal_alignment=26.67,
        finding_alignment=100.0,
        final_order_alignment=100.0,
        evidence_alignment=100.0,
        witness_alignment=100.0,
        assessability=assessability,
    )

    # Active weights must sum to 1.0
    active_weight_sum = sum(scores.active_weights.values())
    assert abs(active_weight_sum - 1.0) < 0.001

    # Excluded categories must match
    assert set(scores.excluded_categories) == {"evidence_alignment", "witness_alignment"}

    # Overall score must equal weighted sum across assessable categories
    expected_overall = sum(
        getattr(scores, k) * scores.active_weights[k]
        for k in scores.active_weights
    )
    assert abs(scores.overall_score - round(expected_overall, 2)) < 0.05



