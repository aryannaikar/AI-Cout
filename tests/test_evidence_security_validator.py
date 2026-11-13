"""
Tests for Evidence PDF Security Validator — False Positive Prevention & True Positive Enforcement.

Covers the 10 specified test areas:
 1. Clean Evidence PDF is accepted.
 2. Evidence containing normal legal words (judgment, verdict, order, court, decision, appeal) is accepted.
 3. Evidence PDF with exhibit "Release order" (Ex.PH) is accepted.
 4. Evidence PDF with witness reference to a judgment is accepted (procedural context).
 5. Actual Ground Truth PDF is rejected.
 6. Actual Real Verdict is rejected.
 7. Actual hidden final judgment (evaluation benchmark) is rejected.
 8. Ground Truth content cannot enter CourtState (validate_no_forbidden_keys).
 9. Ground Truth cannot reach Judge (via validate_no_forbidden_keys on JudgeInput-like dicts).
10. Existing security tests remain passing (filename blocking still works for explicit GT names).

False Positive Protection Principle:
  - A single legal word ("verdict", "judgment", "order") must NOT cause rejection.
  - Only compound/co-occurring GT evaluation signals should trigger rejection.

True Positive Enforcement Principle:
  - A document declaring itself a GT evaluation artifact MUST be rejected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graph.validation import (
    BlindEvaluationViolation,
    validate_case_packet_path,
    validate_no_forbidden_keys,
    validate_no_ground_truth_text,
)
from app.ingestion.evidence_loader import (
    EvidencePDFLoader,
    GroundTruthLeakageError,
)
from rag.loader import PDFPage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_loader_pages(text: str) -> list[PDFPage]:
    """Wrap plain text into a single PDFPage for testing loader-level validation."""
    return [PDFPage(page_number=1, text=text, source_file="Evidence_Packet.pdf")]


# ---------------------------------------------------------------------------
# 1. Clean Evidence PDF is accepted
# ---------------------------------------------------------------------------

def test_1_clean_evidence_pdf_is_accepted():
    """A properly formatted Evidence PDF with only evidentiary content must be accepted."""
    clean_evidence = """
    IN THE HIGH COURT OF PUNJAB & HARYANA AT CHANDIGARH
    CRA-S-174-SB-2005
    Jai Bhagwan & Ors. ..... Appellants
    VERSUS
    State of Haryana ..... Respondent

    FIR No.50 dated 01.07.2002, Police Station Mohana.
    Offences under Section 412, 420, 468, 471 IPC and Section 25 Arms Act.

    PW-1 - Om Parkash
    PW-6 - Gurnam Singh
    PW-7 - Inspector Lachman Singh

    Ex.PA - Affidavit of Om Parkash
    Ex.PH - Release order of car in question
    Ex.PG - Memo of Identification of the car by PW-6 Gurnam Singh
    Ex.P3 - Pistol recovered from appellant Jai Bhagwan

    In their defence evidence, no evidence was adduced by the appellants.
    """
    # Must not raise
    validate_no_ground_truth_text(clean_evidence)

    loader = EvidencePDFLoader()
    pages = loader.load_text(clean_evidence, source_filename="Evidence_Packet.pdf")
    assert len(pages) == 1


# ---------------------------------------------------------------------------
# 2. Evidence containing normal legal words is accepted
# ---------------------------------------------------------------------------

def test_2_normal_legal_words_are_accepted():
    """
    Words such as 'judgment', 'verdict', 'order', 'court', 'appeal', 'decision'
    appearing naturally in case evidence must NOT trigger rejection.
    """
    legal_word_evidence = """
    State v. Accused — Criminal Appeal No. 174/2005

    The prosecution relied upon documentary evidence and oral depositions.
    The court heard arguments from both parties on the question of possession.
    The appeal arises from the conviction order passed by the Sessions Court.
    The decision of the Sessions Judge was challenged on grounds of appreciation of evidence.
    A judgment dated 01.07.2002 was referenced as part of the procedural history.
    The accused challenged the verdict of the lower court through this appeal.
    The order of Sessions Court was appealed in the High Court.

    PW-6 stated that he reported the matter to the police after he became aware of it.
    The final report under Section 173 CrPC was filed after investigation.
    """
    # None of these single legal words should trigger rejection
    validate_no_ground_truth_text(legal_word_evidence)


# ---------------------------------------------------------------------------
# 3. Evidence PDF with exhibit "Release order" is accepted
# ---------------------------------------------------------------------------

def test_3_release_order_exhibit_is_accepted():
    """
    'Ex.PH - Release order of car in question' contains the word 'order'
    and should be accepted without any rejection.
    """
    text_with_release_order = """
    Documentary Evidence proved by the prosecution:

    Ex.PA  - Affidavit of Om Parkash
    Ex.PB  - Seizure memo of Indica car and countrymade pistol
    Ex.PH  - Release order of car in question
    Ex.PC/1 - Copy of First Information Report
    Ex.PK  - Photocopy of FIR No.149 dated 16.05.2002, Police Station Sadar Rohtak
    """
    # Must not raise — "Release order" is an exhibit label, not a GT signal
    validate_no_ground_truth_text(text_with_release_order)

    loader = EvidencePDFLoader()
    pages = loader.load_text(text_with_release_order, source_filename="Evidence_Packet.pdf")
    assert any("Ex.PH" in p.text for p in pages)


# ---------------------------------------------------------------------------
# 4. Evidence PDF with witness reference to a judgment is accepted
# ---------------------------------------------------------------------------

def test_4_witness_reference_to_judgment_in_evidence_is_accepted():
    """
    A witness deposing about a judgment referenced in procedural history
    must not trigger rejection. Context matters — this is evidence, not GT.
    """
    procedural_judgment_reference = """
    PW-5 Silak Ram, Reader to District Magistrate Sonepat, deposed that
    the judgment of conviction in the lower court was based on examination
    of the documentary exhibits. He referred to the order of the Magistrate
    as part of his official capacity.

    PW-7 Inspector Lachman Singh deposed that after the final report under
    Section 173 CrPC was filed, the court took cognizance.
    The accused challenged the order of the Sessions Judge through an appeal.

    The defense argued that the Sessions Court decision was based on
    insufficient appreciation of recovery evidence.
    """
    # Procedural/contextual judgment references must be accepted
    validate_no_ground_truth_text(procedural_judgment_reference)

    loader = EvidencePDFLoader()
    pages = loader.load_text(procedural_judgment_reference, source_filename="Evidence_Packet.pdf")
    assert len(pages) == 1


# ---------------------------------------------------------------------------
# 5. Actual Ground Truth PDF is rejected
# ---------------------------------------------------------------------------

def test_5_actual_ground_truth_pdf_is_rejected():
    """A document explicitly declaring itself the Ground Truth verdict must be rejected."""
    ground_truth_text = """
    GROUND TRUTH VERDICT — EVALUATION DOCUMENT
    =============================================
    This document contains the actual court decision for evaluation benchmarking.
    Ground truth verdict: The accused are guilty as charged.
    Final verdict: Convicted under Section 412 IPC.
    This file must never be uploaded to the AI Court system.
    """
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_ground_truth_text(ground_truth_text)


# ---------------------------------------------------------------------------
# 6. Actual Real Verdict is rejected
# ---------------------------------------------------------------------------

def test_6_actual_real_verdict_is_rejected():
    """A document containing a real verdict declaration must be rejected."""
    real_verdict_text = """
    REAL COURT JUDGMENT — DO NOT UPLOAD TO AI SYSTEM

    The High Court of Punjab & Haryana, having heard the parties, arrived at
    the following conclusion as ground truth is:

    The appeal is dismissed. The conviction is upheld.
    Real court judgment: Conviction confirmed.
    """
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_ground_truth_text(real_verdict_text)


# ---------------------------------------------------------------------------
# 7. Actual hidden final judgment (evaluation benchmark) is rejected
# ---------------------------------------------------------------------------

def test_7_hidden_final_judgment_evaluation_is_rejected():
    """
    A document serving as a hidden evaluation benchmark — describing the
    actual final outcome — must be rejected.
    """
    hidden_benchmark_text = """
    EVALUATION BENCHMARK — HIDDEN EVALUATION VERDICT
    ==================================================
    Case: CRA-S-174-SB-2005
    Hidden evaluation label: ACQUITTAL
    Evaluation ground truth: The appellants were acquitted by the High Court.
    Actual verdict: Not guilty.
    This document contains the hidden evaluation verdict for model scoring.
    """
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_ground_truth_text(hidden_benchmark_text)


# ---------------------------------------------------------------------------
# 8. Ground Truth content cannot enter CourtState
# ---------------------------------------------------------------------------

def test_8_ground_truth_content_cannot_enter_court_state():
    """
    Dictionaries carrying ground truth keys must be rejected before
    they can enter the CourtState graph.
    """
    # Explicit ground_truth key
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys({"ground_truth": "guilty", "case_id": "CASE-001"})

    # Nested/variant keys
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys({"real_verdict": "acquitted"})

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys({"actual_judgment": "convicted"})

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys({"correct_verdict": "guilty", "case_id": "X"})

    # Clean dict must be accepted
    validate_no_forbidden_keys({"case_id": "CASE-001", "status": "pending", "judgment": None})


# ---------------------------------------------------------------------------
# 9. Ground Truth cannot reach Judge
# ---------------------------------------------------------------------------

def test_9_ground_truth_cannot_reach_judge():
    """
    Any data structure carrying GT evaluation fields must be blocked
    before reaching the Judge agent. The forbidden keys check acts as
    the last line of defense.
    """
    # Simulate a Judge input dict that somehow acquired a GT field
    judge_input_tainted = {
        "case_id": "CASE-001",
        "prosecution_theory": "...",
        "defense_theory": "...",
        "ground_truth_verdict": "convicted",   # ← must be caught
    }
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys(judge_input_tainted)

    # A tainted variant: hidden evaluation label
    judge_input_tainted_2 = {
        "case_id": "CASE-001",
        "hidden_evaluation_label": "acquitted",
    }
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_no_forbidden_keys(judge_input_tainted_2)

    # Clean Judge input must pass
    clean_judge_input = {
        "case_id": "CASE-001",
        "prosecution_theory": "Accused possessed stolen vehicle.",
        "defense_theory": "Recovery was planted.",
        "judgment": None,   # "judgment" as a field name for AI output is fine
    }
    validate_no_forbidden_keys(clean_judge_input)


# ---------------------------------------------------------------------------
# 10. Existing security — filename blocking still works for explicit GT names
# ---------------------------------------------------------------------------

def test_10_explicit_gt_filenames_still_blocked():
    """
    Regression: validate_case_packet_path must still reject files whose names
    unambiguously identify them as Ground Truth / evaluation verdict documents.
    Ordinary filenames with 'judgment' or 'verdict' as legal context must pass.
    """
    # These must be blocked
    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_case_packet_path("Ground_Truth_Verdict.pdf")

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_case_packet_path("ground_truth_case_outcome.pdf")

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_case_packet_path("real_verdict_appeal.pdf")

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_case_packet_path("actual_judgment_jai_bhagwan.pdf")

    with pytest.raises(BlindEvaluationViolation, match="SECURITY VIOLATION"):
        validate_case_packet_path("hidden_verdict_2005.pdf")

    # These must be ACCEPTED — ordinary legal case filenames
    validate_case_packet_path("Jai_Bhagwan_Evidence_Packet.pdf")
    validate_case_packet_path("Case_Packet.pdf")
    validate_case_packet_path("Evidence_CRA_174_2005.pdf")
    validate_case_packet_path("State_v_Accused_CrA_174.pdf")
