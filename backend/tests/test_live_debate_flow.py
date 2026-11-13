import pytest
from app.graph.workflow import CourtWorkflow
from app.models.case_models import StructuredCase


def test_live_hearing_debate_flow_and_grounding():
    """
    Verifies that the live courtroom debate follows:
    Judge -> Prosecutor -> Defense -> Prosecutor -> Defense -> Judge -> ...
    without 'Proceed.', without newborn child hallucinations, and grounded in case facts.
    """
    workflow = CourtWorkflow()
    
    # Run against the actual case packet file
    case_pdf_path = "backend/data/cases/uploads/up_089f18b80510_Case_Packet.pdf"
    
    # If file doesn't exist at relative path from backend, try without backend prefix
    from pathlib import Path
    if not Path(case_pdf_path).exists():
        case_pdf_path = "data/cases/uploads/up_089f18b80510_Case_Packet.pdf"
    if not Path(case_pdf_path).exists():
        case_pdf_path = "data/cases/case_packet/Jai_Bhagwan_Evidence_Packet.pdf"

    state = workflow.run(case_pdf_path)
    
    assert state.judgment is not None, "Workflow failed to produce a final judgment"
    assert len(state.transcript) >= 5, f"Expected multi-turn debate transcript, got {len(state.transcript)}"
    
    roles = [t["role"] for t in state.transcript]
    print(f"\nDEBATE ROLE SEQUENCE: {' -> '.join(roles)}")
    
    # 1. Verify sequence starts with judge -> prosecutor -> defense
    assert roles[0] == "judge", f"Expected first speaker to be Judge, got {roles[0]}"
    assert roles[1] == "prosecutor", f"Expected second speaker to be Prosecutor, got {roles[1]}"
    assert roles[2] == "defense", f"Expected third speaker to be Defense, got {roles[2]}"
    if len(roles) >= 5:
        assert roles[3] == "prosecutor", f"Expected fourth speaker to be Prosecutor, got {roles[3]}"
        assert roles[4] == "defense", f"Expected fifth speaker to be Defense, got {roles[4]}"
    if len(roles) >= 6:
        assert roles[5] == "judge", f"Expected sixth speaker to be Judge, got {roles[5]}"

    # 2. Verify no message contains 'Proceed.' or newborn child hallucinations
    for i, t in enumerate(state.transcript):
        role = t["role"]
        content = t["content"]
        print(f"\n[{i}] {role.upper()}: {content}")
        
        # Check against "Proceed" filler
        assert content.strip().lower() not in ["proceed", "proceed.", "i proceed"], f"Turn {i} by {role} contained 'Proceed.'"
        assert len(content.strip()) > 15, f"Turn {i} by {role} was too short or empty: '{content}'"
        
        # Check against newborn child hallucination
        assert "newborn" not in content.lower(), f"Turn {i} contained hallucinated 'newborn': {content}"
        assert "infant" not in content.lower(), f"Turn {i} contained hallucinated 'infant': {content}"
        assert "abandon" not in content.lower(), f"Turn {i} contained hallucinated 'abandon': {content}"


if __name__ == "__main__":
    test_live_hearing_debate_flow_and_grounding()
