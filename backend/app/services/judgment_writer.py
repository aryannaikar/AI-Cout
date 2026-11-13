"""
Output persistence and document generator for AI Court of India.
Saves structured AI Judgment and Execution Report to disk in JSON, TXT, and PDF formats.
Guarantees strict isolation: never copies or persists Ground Truth evaluation data.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import pymupdf

from app.models.judgment_models import Judgment

logger = logging.getLogger(__name__)


class JudgmentWriter:
    """
    Persists AI Courtroom judgments and execution reports to disk.
    Creates structured JSON, human-readable TXT, and formal multi-page PDF documents.
    """

    def __init__(self, base_output_dir: Optional[Path | str] = None):
        if base_output_dir:
            self.base_output_dir = Path(base_output_dir).resolve()
        else:
            self.base_output_dir = Path(_backend_dir) / "data" / "cases"

    def get_case_output_dir(self, case_id: str) -> Path:
        """Derive case-specific output directory: data/cases/<case_id>/output/."""
        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in case_id)
        out_dir = self.base_output_dir / safe_id / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def format_judgment_text(self, judgment: Judgment) -> str:
        """Render a readable judicial judgment text containing all 12 framework sections."""
        sep = "=" * 80
        sub_sep = "-" * 80

        lines = [
            sep,
            f"IN THE {judgment.presiding_court.upper()}",
            f"Case: {judgment.case_title}",
            f"Judgment ID: {judgment.judgment_id}",
            f"Date of Decision: {judgment.date_of_decision}",
            sep,
            "",
            "SECTION 1: CASE BACKGROUND & PROSECUTION ORIGIN",
            sub_sep,
            judgment.case_background,
            "",
            "SECTION 2: POINTS FOR DETERMINATION",
            sub_sep,
        ]
        for i, pt in enumerate(judgment.issues_for_determination, 1):
            lines.append(f"{i}. {pt}")
        lines.extend([
            "",
            "SECTION 3: APPLICABLE STATUTORY LAW & CONSTITUTIONAL PROVISIONS",
            sub_sep,
        ])
        for prov in judgment.applicable_law:
            lines.append(f"- {prov}")
        lines.extend([
            "",
            "SECTION 4: JUDICIAL APPRAISAL OF DOCUMENTARY & ELECTRONIC EXHIBITS",
            sub_sep,
            judgment.evidence_assessment,
            "",
            "SECTION 5: CREDIBILITY ANALYSIS OF ORAL WITNESS TESTIMONY",
            sub_sep,
            judgment.witness_assessment,
            "",
            "SECTION 6: SUBMISSIONS ADVANCED BY THE PROSECUTION",
            sub_sep,
            judgment.prosecution_submissions,
            "",
            "SECTION 7: SUBMISSIONS ADVANCED BY THE DEFENSE",
            sub_sep,
            judgment.defense_submissions,
            "",
            "SECTION 8: ISSUE-BY-ISSUE JUDICIAL DETERMINATION",
            sub_sep,
        ])
        for issue in judgment.issue_analyses:
            lines.extend([
                f"Issue #{issue.issue_number}: {issue.issue_statement}",
                f"  Governing Law: {issue.applicable_law}",
                f"  Prosecution Case: {issue.prosecution_submission_summary}",
                f"  Defense Plea: {issue.defense_submission_summary}",
                f"  Evidentiary Analysis: {issue.evidentiary_evaluation}",
                f"  Finding: {issue.judicial_finding}",
                "",
            ])
        lines.extend([
            "SECTION 9: FINDINGS ON EACH STATUTORY CHARGE",
            sub_sep,
        ])
        for charge, finding in judgment.findings_per_charge.items():
            lines.append(f"- {charge}: {finding}")
        lines.extend([
            "",
            "SECTION 10: OPERATIVE ORDER & FINAL DECISION",
            sub_sep,
            f"VERDICT: {judgment.final_decision.upper()}",
            "",
            "SECTION 11: RATIO DECIDENDI & DETAILED JUDICIAL REASONING",
            sub_sep,
            judgment.reasons,
            "",
            "SECTION 12: STATUTORY CITATIONS & PRECEDENTS",
            sub_sep,
        ])
        for cit in judgment.legal_citations:
            lines.append(f"- {cit}")
        lines.extend([
            "",
            sep,
            "Pronounced in Open Simulated Court by Presiding Judicial Bench.",
            "AI Court of India — Autonomous Judicial Reasoning Engine",
            sep,
        ])

        return "\n".join(lines)

    def write_judgment_pdf(self, judgment_text: str, output_path: Path) -> Path:
        """Render judgment text into a multi-page PDF document using PyMuPDF."""
        doc = pymupdf.open()
        
        # Standard A4 size: 595 x 842 pt
        page_width, page_height = 595, 842
        margin = 54
        rect = pymupdf.Rect(margin, margin, page_width - margin, page_height - margin)

        # Break text into lines and render across pages
        lines = judgment_text.split("\n")
        current_page = doc.new_page(width=page_width, height=page_height)
        y = margin + 20
        line_height = 14

        for line in lines:
            if y > page_height - margin - 20:
                # Add page number footer
                footer_text = f"Page {len(doc)}"
                current_page.insert_text(
                    pymupdf.Point(page_width / 2 - 20, page_height - margin + 10),
                    footer_text,
                    fontsize=9,
                    color=(0.4, 0.4, 0.4),
                )
                current_page = doc.new_page(width=page_width, height=page_height)
                y = margin + 20

            is_header = line.startswith("SECTION") or line.startswith("IN THE") or line.startswith("VERDICT:")
            fontsize = 11 if is_header else 9.5
            fontname = "helv"

            # Truncate or wrap very long lines
            max_chars = 85
            sub_lines = [line[i:i + max_chars] for i in range(0, len(line), max_chars)] if len(line) > max_chars else [line]
            for sub in sub_lines:
                if y > page_height - margin - 20:
                    current_page = doc.new_page(width=page_width, height=page_height)
                    y = margin + 20
                current_page.insert_text(
                    pymupdf.Point(margin, y),
                    sub,
                    fontsize=fontsize,
                    fontname=fontname,
                )
                y += line_height

        # Add footer to final page
        current_page.insert_text(
            pymupdf.Point(page_width / 2 - 20, page_height - margin + 10),
            f"Page {len(doc)}",
            fontsize=9,
            color=(0.4, 0.4, 0.4),
        )

        doc.save(output_path)
        doc.close()
        logger.info("Generated PDF judgment at: %s", output_path)
        return output_path

    def persist_judgment(
        self,
        case_id: str,
        judgment: Judgment,
        custom_output_dir: Optional[Path | str] = None,
    ) -> dict[str, str]:
        """
        Persist judgment in JSON, TXT, and PDF formats.

        Returns:
            Dictionary mapping format ('json', 'txt', 'pdf', 'dir') to absolute file paths.
        """
        out_dir = Path(custom_output_dir).resolve() if custom_output_dir else self.get_case_output_dir(case_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. JSON
        json_path = out_dir / "ai_judgment.json"
        json_content = judgment.model_dump_json(indent=2)
        json_path.write_text(json_content, encoding="utf-8")

        # 2. Text
        txt_path = out_dir / "ai_judgment.txt"
        txt_content = self.format_judgment_text(judgment)
        txt_path.write_text(txt_content, encoding="utf-8")

        # 3. PDF
        pdf_path = out_dir / "ai_judgment.pdf"
        self.write_judgment_pdf(txt_content, pdf_path)

        logger.info("Persisted AI Judgment for case '%s' to '%s'", case_id, out_dir)
        return {
            "dir": str(out_dir),
            "json": str(json_path),
            "txt": str(txt_path),
            "pdf": str(pdf_path),
        }

    def persist_execution_report(
        self,
        case_id: str,
        report_data: dict,
        custom_output_dir: Optional[Path | str] = None,
    ) -> Path:
        """Save execution_report.json to disk."""
        out_dir = Path(custom_output_dir).resolve() if custom_output_dir else self.get_case_output_dir(case_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        report_path = out_dir / "execution_report.json"
        report_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
        return report_path
