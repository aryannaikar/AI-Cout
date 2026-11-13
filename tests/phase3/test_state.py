"""
Phase 3 Tests: CourtState and Blindness Validation.
Verifies strongly-typed state schema, reducers, and defensive exclusion of ground-truth data.
"""

from pathlib import Path
import pytest

from app.graph.state import CourtError, CourtState, ExecutionLogEntry, JudgeInput
from app.graph.validation import BlindEvaluationViolation
from app.models.case_models import StructuredCase
from app.models.judgment_models import DefenseCase, ProsecutionCase
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.conflict_models import ConflictReport


def test_court_state_initialization():
    state = CourtState(case_packet="Case_Packet.pdf")
    assert state.case_packet == "Case_Packet.pdf"
    assert state.case_analysis is None
    assert state.prosecution is None
    assert state.defense is None
    assert state.judgment is None
    assert state.errors == []
    assert state.execution_log == []


def test_court_state_forbids_extra_fields():
    with pytest.raises(Exception):
        CourtState(case_packet="Case_Packet.pdf", unauthorized_extra_field="malicious_payload")


def test_court_state_rejects_ground_truth_file():
    with pytest.raises(BlindEvaluationViolation, match="rejected"):
        CourtState(case_packet="Ground_Truth_Verdict.pdf")

    with pytest.raises(BlindEvaluationViolation, match="rejected"):
        CourtState(case_packet=Path("data/sample/Ground_Truth_Verdict.pdf"))


def test_court_state_rejects_forbidden_keys():
    for forbidden_key in ["ground_truth", "real_verdict", "actual_judgment", "correct_verdict", "ground_truth_verdict"]:
        with pytest.raises(BlindEvaluationViolation, match="Forbidden field"):
            CourtState(**{"case_packet": "Case_Packet.pdf", forbidden_key: "guilty"})


def test_court_state_reducers_aggregate_entries():
    err1 = CourtError(agent="agent_a", error="error 1", recoverable=True)
    err2 = CourtError(agent="agent_b", error="error 2", recoverable=True)

    log1 = ExecutionLogEntry(node="node_a", status="completed")
    log2 = ExecutionLogEntry(node="node_b", status="completed")

    state = CourtState(case_packet="Case_Packet.pdf", errors=[err1], execution_log=[log1])
    assert len(state.errors) == 1
    assert len(state.execution_log) == 1


def test_judge_input_validation():
    # Valid minimal judge input construction
    case = StructuredCase(case_id="C-1", case_title="State v. Kumar", allegations_summary="Alleged receipt of stolen electronic goods.")
    pros = ProsecutionCase(case_id="C-1", prosecution_theory="Theory", final_prayer="Conviction")
    defs = DefenseCase(case_id="C-1", defense_theory="Defense", alternative_interpretation="Innocent", final_prayer="Acquittal")
    ev = EvidenceAnalysisReport(
        case_id="C-1",
        documentary_compliance_assessment="Compliance noted",
        summary="Evidence summary",
    )
    conf = ConflictReport(case_id="C-1", total_conflicts=0, summary="No fatal conflicts")

    judge_in = JudgeInput(
        case_analysis=case,
        prosecution=pros,
        defense=defs,
        evidence_analysis=ev,
        conflicts=conf,
    )
    assert judge_in.case_analysis.case_id == "C-1"

    # Forbids ground truth fields
    with pytest.raises(BlindEvaluationViolation):
        JudgeInput(
            case_analysis=case,
            prosecution=pros,
            defense=defs,
            evidence_analysis=ev,
            conflicts=conf,
            ground_truth="convicted",
        )
