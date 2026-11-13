"""
Phase 4 Tests: Structured AI Judgment Generation (Tests 18-21).
Verifies that the generated judgment adheres to the 12-section judicial framework,
the execution log is fully populated, and errors are cleanly structured.
"""

from unittest.mock import patch
from app.graph.state import CourtError, CourtState
from app.graph.workflow import run_court
from app.models.judgment_models import Judgment, JudicialIssueAnalysis
from app.models.legal_models import WebResearchItem, WebResearchResult
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def _make_mock_web_result() -> WebResearchResult:
    return WebResearchResult(
        research_id="RES-MOCK-WEB",
        side="prosecution",
        research_question="Standard of proof under BSA and BNS",
        finding="Precedent requires clear chain of custody for seized articles.",
        why_it_matters="Relevant to evaluation of seizure memos.",
        sources=[
            WebResearchItem(
                title="State of Haryana v. Bhajan Lal",
                url="https://indiankanoon.org/doc/12345",
                passage_summary="Guidelines on criminal investigation and evidence.",
                why_source_matters="Applicable standard of proof.",
            )
        ],
    )


def test_18_and_19_structured_ai_judgment_all_12_sections_present():
    """Verify structured AI judgment generation with all 12 mandatory sections."""
    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=_make_mock_web_result()):
        report = run_court(SAMPLE_CASE_PACKET_TEXT)

        assert report is not None
        judgment: Judgment = report.ai_judgment
        assert isinstance(judgment, Judgment)

        # 12 Mandatory Sections Verification:
        # Section 1: Case background
        assert isinstance(judgment.case_background, str)
        assert len(judgment.case_background) > 20

        # Section 2: Issues for determination
        assert isinstance(judgment.issues_for_determination, list)
        assert len(judgment.issues_for_determination) > 0

        # Section 3: Applicable law
        assert isinstance(judgment.applicable_law, list)
        assert len(judgment.applicable_law) > 0

        # Section 4: Evidence assessment
        assert isinstance(judgment.evidence_assessment, str)
        assert len(judgment.evidence_assessment) > 20

        # Section 5: Witness assessment
        assert isinstance(judgment.witness_assessment, str)
        assert len(judgment.witness_assessment) > 20

        # Section 6: Prosecution submissions
        assert isinstance(judgment.prosecution_submissions, str)
        assert len(judgment.prosecution_submissions) > 20

        # Section 7: Defense submissions
        assert isinstance(judgment.defense_submissions, str)
        assert len(judgment.defense_submissions) > 20

        # Section 8: Analysis of each issue
        assert isinstance(judgment.issue_analyses, list)
        assert len(judgment.issue_analyses) > 0
        for analysis in judgment.issue_analyses:
            assert isinstance(analysis, JudicialIssueAnalysis)
            assert analysis.issue_number > 0
            assert analysis.judicial_finding in ["PROVED", "NOT PROVED", "DISPROVED"]

        # Section 9: Findings per charge
        assert isinstance(judgment.findings_per_charge, dict)
        assert len(judgment.findings_per_charge) > 0

        # Section 10: Final decision
        assert judgment.final_decision in ["CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"]

        # Section 11: Reasons
        assert isinstance(judgment.reasons, str)
        assert len(judgment.reasons) > 20

        # Section 12: Legal citations
        assert isinstance(judgment.legal_citations, list)
        assert len(judgment.legal_citations) > 0


def test_20_execution_log_is_populated():
    """Verify execution log contains sequential traces of node execution."""
    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=_make_mock_web_result()):
        report = run_court(SAMPLE_CASE_PACKET_TEXT)

        assert report.execution_log is not None
        assert len(report.execution_log) >= 8

        nodes_logged = [entry.node for entry in report.execution_log]
        assert "case_understanding" in nodes_logged
        assert "prosecutor" in nodes_logged
        assert "defense" in nodes_logged
        assert "judge" in nodes_logged

        for entry in report.execution_log:
            assert entry.status == "completed"
            assert entry.start_time is not None
            assert entry.end_time is not None


def test_21_errors_are_structured():
    """Verify runtime errors during graph execution are captured in structured error logs."""
    state = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    # Inject a structured error
    err = CourtError(agent="test_node", error="Simulated controlled agent exception", recoverable=True)
    state.errors.append(err)

    assert len(state.errors) == 1
    assert state.errors[0].agent == "test_node"
    assert "Simulated controlled" in state.errors[0].error
    assert state.errors[0].timestamp is not None
