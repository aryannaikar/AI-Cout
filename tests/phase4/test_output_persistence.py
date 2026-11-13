"""
Phase 4 Tests: Output Persistence and Storage Integrity (Tests 22-24).
Verifies that:
- ai_judgment.json, ai_judgment.txt, ai_judgment.pdf, and execution_report.json are valid
- output files contain NO Ground Truth leaks or verdict copies
- repeated executions do not corrupt files or directories
"""

import json
from pathlib import Path
from unittest.mock import patch

from app.graph.workflow import run_court
from app.models.execution_models import ExecutionReport
from app.models.judgment_models import Judgment
from app.models.legal_models import WebResearchItem, WebResearchResult
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def _make_mock_web_result() -> WebResearchResult:
    return WebResearchResult(
        research_id="RES-MOCK-WEB",
        side="prosecution",
        research_question="Legal precedents on electronic evidence admissibility",
        finding="Precedents mandate compliance with Section 63 BSA.",
        why_it_matters="Relevant to admissibility of call records.",
        sources=[
            WebResearchItem(
                title="Arjun Panditrao v. Kailash Kushanrao",
                url="https://indiankanoon.org/doc/56789",
                passage_summary="Certificate requirement for secondary electronic evidence.",
                why_source_matters="Governs Exhibit P-2 admissibility.",
            )
        ],
    )


def test_22_output_files_exist_and_json_is_valid(tmp_path: Path):
    """Verify generated output files exist and match Pydantic schemas."""
    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=_make_mock_web_result()):
        report = run_court(SAMPLE_CASE_PACKET_TEXT)
        assert report is not None
        assert report.case_id is not None
        assert report.status == "completed"

        case_out_dir = Path("backend/data/cases") / report.case_id / "output"
        assert case_out_dir.exists(), f"Directory {case_out_dir} was not created"

        json_file = case_out_dir / "ai_judgment.json"
        txt_file = case_out_dir / "ai_judgment.txt"
        pdf_file = case_out_dir / "ai_judgment.pdf"
        report_file = case_out_dir / "execution_report.json"

        assert json_file.exists(), "ai_judgment.json missing"
        assert txt_file.exists(), "ai_judgment.txt missing"
        assert pdf_file.exists(), "ai_judgment.pdf missing"
        assert report_file.exists(), "execution_report.json missing"

        # Validate ai_judgment.json
        raw_judgment = json.loads(json_file.read_text(encoding="utf-8"))
        validated_judgment = Judgment(**raw_judgment)
        assert validated_judgment.judgment_id == report.ai_judgment.judgment_id

        # Validate execution_report.json
        raw_report = json.loads(report_file.read_text(encoding="utf-8"))
        validated_report = ExecutionReport(**raw_report)
        assert validated_report.case_id == report.case_id

        # Validate PDF content size
        assert pdf_file.stat().st_size > 500


def test_23_output_does_not_contain_ground_truth():
    """Verify output directory contains NO ground truth files and no leak terms."""
    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=_make_mock_web_result()):
        report = run_court(SAMPLE_CASE_PACKET_TEXT)
        case_out_dir = Path("backend/data/cases") / report.case_id / "output"

        # 1. Check file names
        for item in case_out_dir.iterdir():
            name_lower = item.name.lower()
            assert "ground_truth" not in name_lower
            assert "real_verdict" not in name_lower

        # 2. Check JSON and TXT text contents
        txt_content = (case_out_dir / "ai_judgment.txt").read_text(encoding="utf-8").lower()
        json_content = (case_out_dir / "ai_judgment.json").read_text(encoding="utf-8").lower()

        for forbidden in ["ground_truth", "real_verdict", "actual_verdict", "hidden_verdict"]:
            assert forbidden not in txt_content
            assert forbidden not in json_content


def test_24_repeated_executions_do_not_corrupt_outputs(tmp_path: Path):
    """Verify multiple executions handle persistence cleanly and idempotently."""
    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=_make_mock_web_result()):
        report_1 = run_court(SAMPLE_CASE_PACKET_TEXT)
        report_2 = run_court(SAMPLE_CASE_PACKET_TEXT)

        assert report_1.status == "completed"
        assert report_2.status == "completed"

        case_out_dir = Path("backend/data/cases") / report_2.case_id / "output"
        assert (case_out_dir / "ai_judgment.json").exists()
        assert (case_out_dir / "ai_judgment.txt").exists()
        assert (case_out_dir / "ai_judgment.pdf").exists()

        # Check that JSON is still valid after rewrite
        data = json.loads((case_out_dir / "ai_judgment.json").read_text(encoding="utf-8"))
        Judgment(**data)
