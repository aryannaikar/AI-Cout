"""
Phase 4 Tests: Context-Aware Case Packet Input Validation (Tests 1-5).
Verifies acceptance of valid Case Packets, rejection of Ground Truth / Real Verdicts,
and context-aware tolerance of legal references citing judgments.
"""

from pathlib import Path
import pytest

from app.graph.state import CourtState
from app.graph.validation import BlindEvaluationViolation, validate_case_packet_path, validate_no_ground_truth_text
from app.graph.workflow import run_court
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_1_case_packet_accepted(sample_case_packet_pdf: Path):
    """Verify both valid Case_Packet.pdf and raw text are accepted."""
    state_pdf = CourtState(case_packet=str(sample_case_packet_pdf))
    assert state_pdf.case_packet == str(sample_case_packet_pdf)

    state_text = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    assert len(state_text.case_packet) > 50


def test_2_invalid_case_packet_rejected():
    """Verify empty or non-existent file path handling."""
    with pytest.raises(Exception):
        run_court("non_existent_case_file_path_12345.pdf")


def test_3_ground_truth_rejected(tmp_path: Path):
    """Verify files containing ground_truth in name are rejected."""
    fake_gt = tmp_path / "Ground_Truth_Verdict.pdf"
    fake_gt.write_bytes(b"%PDF-1.4 Fake GT")

    with pytest.raises(BlindEvaluationViolation, match="rejected"):
        validate_case_packet_path(fake_gt)

    with pytest.raises(BlindEvaluationViolation, match="rejected"):
        run_court(fake_gt)


def test_4_real_verdict_rejected(tmp_path: Path):
    """Verify files containing verdict in name or evaluation signatures in text are rejected."""
    fake_verdict = tmp_path / "real_verdict.pdf"
    fake_verdict.write_bytes(b"%PDF-1.4 Fake Real Verdict")

    with pytest.raises(BlindEvaluationViolation, match="rejected"):
        validate_case_packet_path(fake_verdict)

    tainted_text = (
        SAMPLE_CASE_PACKET_TEXT
        + "\nREAL VERDICT: The accused is hereby convicted under BNS Section 317."
    )
    with pytest.raises(BlindEvaluationViolation, match="ground-truth signature"):
        validate_no_ground_truth_text(tainted_text)


def test_5_ground_truth_cannot_enter_initial_state():
    """Verify CourtState strictly rejects forbidden ground truth fields."""
    with pytest.raises(BlindEvaluationViolation):
        CourtState(case_packet="Case_Packet.pdf", ground_truth="conviction")

    with pytest.raises(BlindEvaluationViolation):
        CourtState(case_packet="Case_Packet.pdf", real_verdict="acquittal")


def test_contextual_judgment_citation_accepted():
    """Verify ordinary legal occurrences of 'judgment' (e.g., citing a precedent) are accepted."""
    legal_packet_with_citation = (
        SAMPLE_CASE_PACKET_TEXT
        + "\nDEFENSE ARGUMENT: As held in the judgment of the Supreme Court in State v. Kumar, "
        + "reasonable doubt must accrue to the benefit of the accused."
    )
    # Must NOT raise BlindEvaluationViolation
    validate_no_ground_truth_text(legal_packet_with_citation)
    state = CourtState(case_packet=legal_packet_with_citation)
    assert "judgment of the Supreme Court" in state.case_packet
