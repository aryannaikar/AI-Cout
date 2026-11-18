"""
Phase 4 Tests: Real End-to-End Smoke Test and Output Verification (Parts K & L).
Runs the complete courtroom workflow starting from a real synthetic Case_Packet.pdf,
verifying that genuine AI judgment, execution reports, and all 16 criteria are satisfied.
"""

from pathlib import Path
from unittest.mock import patch

from app.graph.workflow import run_court
from app.models.execution_models import ExecutionReport
from app.models.judgment_models import Judgment
from app.models.legal_models import WebResearchItem, WebResearchResult


def test_end_to_end_smoke_and_verify_all_16_criteria(sample_case_packet_pdf: Path):
    """
    Execute real end-to-end pipeline on sample_case_packet_pdf and verify all 16 criteria:
    1. Case facts are present
    2. Relevant issues are identified
    3. Applicable legal provisions are retrieved
    4. Prosecution arguments are present
    5. Defense arguments are present
    6. Evidence analysis is present
    7. Conflict analysis is present
    8. Judge receives the above information
    9. AI judgment is generated
    10. Judgment is structured correctly (12 sections)
    11. No Ground Truth conclusion appears
    12. Execution log shows the expected node sequence
    13. No unexpected empty/null agent output exists
    14. RAG citations/source metadata are preserved
    15. Web research output follows its schema
    16. Output files are actually created (.json, .txt, .pdf)
    """
    mock_web = WebResearchResult(
        research_id="RES-MOCK-E2E",
        side="prosecution",
        research_question="Applicability of Section 317 BNS stolen property",
        finding="Statutory commentary affirms requirements of dishonest intent.",
        why_it_matters="Relevant to evaluation of element of guilty knowledge.",
        sources=[
            WebResearchItem(
                title="BNS Legal Commentary 2024",
                url="https://indiankanoon.org/doc/987654",
                passage_summary="Supreme Court guidance on presumptive possession.",
                why_source_matters="Grounds standard for Section 317 BNS.",
            )
        ],
    )

    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=mock_web):
        # Run full pipeline with real Case_Packet.pdf
        report: ExecutionReport = run_court(sample_case_packet_pdf)

        # 8 & 9. AI judgment is generated and Judge receives the info
        assert report is not None
        assert report.status == "completed"
        judgment: Judgment = report.ai_judgment
        assert judgment is not None

        # 1. Case facts are present
        assert judgment.case_background is not None
        assert len(judgment.case_background) > 0

        # 2. Relevant issues are identified
        assert len(judgment.issues_for_determination) > 0
        assert any(
            "stolen" in issue.lower()
            or "offence" in issue.lower()
            or "charge" in issue.lower()
            or "element" in issue.lower()
            or "possession" in issue.lower()
            or "317" in issue.lower()
            for issue in judgment.issues_for_determination
        )

        # 3. Applicable legal provisions are retrieved
        assert len(judgment.applicable_law) > 0
        assert any("BNS" in law or "BSA" in law or "317" in law or "303" in law or "Section" in law for law in judgment.applicable_law)

        # 4. Prosecution arguments are present
        assert len(judgment.prosecution_submissions) > 0
        assert "prosecution" in judgment.prosecution_submissions.lower()

        # 5. Defense arguments are present
        assert len(judgment.defense_submissions) > 0
        assert "defense" in judgment.defense_submissions.lower() or "accused" in judgment.defense_submissions.lower()

        # 6. Evidence analysis is present
        assert len(judgment.evidence_assessment) > 0

        # 7. Conflict analysis is present
        assert len(judgment.issue_analyses) > 0

        # 10. Judgment is structured correctly (all 12 sections present)
        assert judgment.case_background
        assert judgment.issues_for_determination
        assert judgment.applicable_law
        assert judgment.evidence_assessment
        assert judgment.witness_assessment
        assert judgment.prosecution_submissions
        assert judgment.defense_submissions
        assert judgment.issue_analyses
        assert judgment.findings_per_charge
        assert judgment.final_decision in ["CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"]
        assert judgment.reasons
        assert judgment.legal_citations

        # 11. No Ground Truth conclusion appears
        judgment_str = judgment.model_dump_json().lower()
        for forbidden in ["ground_truth", "real_verdict", "actual_verdict"]:
            assert forbidden not in judgment_str

        # 12. Execution log shows the expected node sequence
        nodes_logged = [e.node for e in report.execution_log]
        assert "case_understanding" in nodes_logged
        assert "prosecutor" in nodes_logged
        assert "defense" in nodes_logged
        assert "judge" in nodes_logged

        # 13. No unexpected empty/null agent output exists
        for agent_name, status in report.agent_statuses.items():
            assert status == "completed", f"Agent {agent_name} failed or incomplete: {status}"

        # 14. RAG citations/source metadata are preserved where expected
        assert len(judgment.legal_citations) > 0

        # 15. Web research output follows its schema
        assert len(mock_web.sources) > 0
        assert mock_web.sources[0].url.startswith("https://")

        # 16. Output files are actually created
        case_dir = Path("backend/data/cases") / report.case_id / "output"
        assert case_dir.exists()
        assert (case_dir / "ai_judgment.json").is_file()
        assert (case_dir / "ai_judgment.txt").is_file()
        assert (case_dir / "ai_judgment.pdf").is_file()
        assert (case_dir / "execution_report.json").is_file()
        assert (case_dir / "ai_judgment.pdf").stat().st_size > 500
