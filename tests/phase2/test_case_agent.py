"""
Phase 2 Tests: Case Understanding Agent and Blind Evaluation Guards.
"""

from pathlib import Path
import pytest
from app.agents.case_agent import CaseUnderstandingAgent
from app.models.case_models import StructuredCase


SAMPLE_CASE_PACKET_TEXT = """
IN THE COURT OF SESSIONS AT NEW DELHI
Sessions Case No. 45/2024
State of NCT of Delhi v. Ramesh Kumar

CHARGES:
The accused Ramesh Kumar is charged under Section 317 of Bharatiya Nyaya Sanhita, 2023
for dishonestly receiving stolen electronic devices.

PROSECUTION FACTS:
1. On 12th January 2024, complainant reported theft of 10 laptops from his warehouse.
2. On 14th January 2024, Sub-Inspector Sharma intercepted accused with 4 stolen laptops.
3. Seizure panchnama Ex. P-1 was prepared at the spot.

DEFENSE PLEA:
1. The accused pleads complete innocence and asserts he purchased the devices with valid receipts.
2. The recovery was planted by police without independent witnesses.

WITNESSES:
PW-1: Complainant Vikas Verma (Warehouse owner)
PW-2: Sub-Inspector R. Sharma (Investigating Officer)

EXHIBITS:
Ex. P-1: Seizure Memo of 4 laptops
Ex. P-2: CCTV Footage of warehouse exit
"""


def test_case_agent_parses_packet_text():
    agent = CaseUnderstandingAgent()
    case = agent.parse_case_text(SAMPLE_CASE_PACKET_TEXT, source_filename="Case_Packet.pdf")

    assert isinstance(case, StructuredCase)
    assert "Ramesh Kumar" in case.case_title or "State" in case.case_title
    assert len(case.charges) > 0
    assert "317" in case.charges[0].section or "BNS" in case.charges[0].statute
    assert len(case.witnesses) >= 2
    assert len(case.exhibits) >= 2
    assert len(case.disputed_facts) > 0
    assert len(case.missing_or_uncertain_info) > 0


def test_case_agent_ground_truth_file_rejection(tmp_path: Path):
    agent = CaseUnderstandingAgent()

    # Attempting to load Ground_Truth_Verdict.pdf MUST be rejected immediately
    fake_gt = tmp_path / "Ground_Truth_Verdict.pdf"
    fake_gt.write_text("Conviction order and final court reasoning.")

    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        agent.process_case_packet(fake_gt)


def test_case_agent_judgment_file_rejection(tmp_path: Path):
    agent = CaseUnderstandingAgent()

    fake_judgment = tmp_path / "high_court_judgment.pdf"
    fake_judgment.write_text("Final judgment of the court.")

    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        agent.process_case_packet(fake_judgment)


def test_case_agent_detects_ground_truth_inside_text():
    agent = CaseUnderstandingAgent()
    tainted_text = "Here is the case packet. Final verdict of the court: Ground truth is guilty."

    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        agent.parse_case_text(tainted_text)


def test_case_schema_validation():
    agent = CaseUnderstandingAgent()
    case = agent.parse_case_text(SAMPLE_CASE_PACKET_TEXT)

    # Validate Pydantic schema constraints
    case_dict = case.model_dump()
    assert "case_title" in case_dict
    assert "charges" in case_dict
    assert "witnesses" in case_dict
    assert "exhibits" in case_dict
    assert "legal_issues" in case_dict
    assert isinstance(case_dict["charges"], list)
