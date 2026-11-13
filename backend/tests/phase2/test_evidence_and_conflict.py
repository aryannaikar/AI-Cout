"""
Phase 2 Tests: Evidence Analysis Agent and Conflict Detection Agent.
"""

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.conflict_agent import ConflictDetectionAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.models.conflict_models import ConflictReport, ConflictSeverity
from app.models.evidence_models import EvidenceAnalysisReport, EvidenceType
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_evidence_analysis_agent():
    case_agent = CaseUnderstandingAgent()
    case = case_agent.parse_case_text(SAMPLE_CASE_PACKET_TEXT)

    ev_agent = EvidenceAnalysisAgent()
    report = ev_agent.analyze_evidence(case)

    assert isinstance(report, EvidenceAnalysisReport)
    assert report.case_id == case.case_id
    assert len(report.evidence_items) >= 2

    # Verify classification includes electronic/documentary
    types = [item.type for item in report.evidence_items]
    assert any(t in [EvidenceType.DOCUMENTARY, EvidenceType.ELECTRONIC, EvidenceType.REAL] for t in types)

    # Missing evidence gaps identified
    assert len(report.missing_evidence_gaps) > 0

    # Evidence report must be objective and NOT pronounce verdict
    summary_lower = report.summary.lower()
    assert "convict" not in summary_lower
    assert "sentence the accused" not in summary_lower


def test_conflict_detection_agent():
    case_agent = CaseUnderstandingAgent()
    case = case_agent.parse_case_text(SAMPLE_CASE_PACKET_TEXT)

    ev_agent = EvidenceAnalysisAgent()
    ev_report = ev_agent.analyze_evidence(case)

    conflict_agent = ConflictDetectionAgent()
    conflict_report = conflict_agent.detect_conflicts(case, ev_report)

    assert isinstance(conflict_report, ConflictReport)
    assert conflict_report.total_conflicts > 0
    assert len(conflict_report.conflicts) > 0

    # Ensure conflicts are NOT silently resolved
    for conf in conflict_report.conflicts:
        assert conf.resolution_required is True, "Conflict was silently suppressed!"
        assert conf.statement_a
        assert conf.statement_b
        assert conf.explanation

    # Must contain critical conflicts between prosecution facts and defense plea
    assert conflict_report.critical_conflicts_count > 0
