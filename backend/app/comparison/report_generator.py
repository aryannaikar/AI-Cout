"""
Comparison Report Generator for Phase 5 — AI Court Judgment Comparison Engine.
Compiles the comprehensive 17-section structured report in JSON, human-readable TXT,
and formal archival PDF formats.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf

from app.comparison.schemas import (
    ChargeComparisonResult,
    ComparisonErrorDetail,
    ComparisonReport,
    ComparisonScores,
    EvidenceComparisonResult,
    FactualComparisonResult,
    FinalOrderComparisonResult,
    FindingComparisonResult,
    IssueComparisonResult,
    LegalProvisionComparisonResult,
    LegalReasoningComparisonResult,
    VerdictComparisonResult,
    WitnessComparisonResult,
)

logger = logging.getLogger(__name__)


class ComparisonReportGenerator:
    """
    Renders structured comparison reports across JSON, TXT, and PDF formats.
    Fully implements the 17 required report sections.
    """

    @classmethod
    def build_report(
        cls,
        comparison_id: str,
        case_id: Optional[str],
        case_title: str,
        mode: str,
        timestamp: str,
        case_information: Dict[str, Any],
        verdict_comp: VerdictComparisonResult,
        issue_comp: IssueComparisonResult,
        fact_comp: FactualComparisonResult,
        charge_comp: ChargeComparisonResult,
        witness_comp: WitnessComparisonResult,
        evidence_comp: EvidenceComparisonResult,
        legal_comp: LegalProvisionComparisonResult,
        reasoning_comp: LegalReasoningComparisonResult,
        finding_comp: FindingComparisonResult,
        order_comp: FinalOrderComparisonResult,
        scores: ComparisonScores,
        major_errors: List[ComparisonErrorDetail],
        missing_points: List[str],
        unrelated_points: List[str],
    ) -> ComparisonReport:
        """Construct the complete 17-section ComparisonReport instance."""
        # Derive overall assessment
        if scores.overall_score >= 80.0 and scores.verdict_alignment >= 80.0 and scores.reasoning_alignment >= 70.0:
            assessment = "FULL ALIGNMENT — AI Court reproduced both operative outcome and substantive judicial reasoning."
        elif scores.verdict_alignment >= 90.0 and scores.reasoning_alignment < 50.0:
            assessment = "VERDICT MATCH — SUBSTANTIVE MISMATCH: AI Court reached the identical operative outcome but failed to reproduce the material legal reasoning and evidentiary grounds of the Real Court."
        elif scores.verdict_alignment == 0.0:
            assessment = "OPERATIVE DISCORDANCE — AI Court diverged completely from the authoritative judicial determination of the Real Court."
        else:
            assessment = "MODERATE ALIGNMENT — AI Court captured aspects of the controversy with material differences in legal application and evidentiary appreciation."

        # Derive overall conclusion
        has_critical = any(e.severity == "critical" for e in major_errors)
        has_major = any(e.severity == "major" for e in major_errors)
        
        if has_critical:
            error_note = "Critical error: Spurious legal or evidentiary grounds detected."
        elif has_major:
            error_note = "Significant divergence: Substantive judicial reasoning or legal grounds diverged materially from the authoritative benchmark."
        elif scores.verdict_alignment >= 90.0 and scores.reasoning_alignment < 50.0:
            error_note = "Superficial verdict alignment: Operative outcome matched, but ratio decidendi and foundational judicial reasoning failed to reproduce authoritative grounds."
        else:
            error_note = "No critical invalidations detected."

        excluded_str = f" | Excluded Categories (Insufficient Data): {', '.join(scores.excluded_categories)}" if scores.excluded_categories else ""
        benchmark_label = "Partial Benchmark Alignment" if scores.excluded_categories else "Overall Benchmark Alignment"

        conclusion = (
            f"{benchmark_label}: {scores.overall_score}%. "
            f"Substantive Quality Score: {scores.substantive_score}%. "
            f"Verdict Alignment: {scores.verdict_alignment}% | Reasoning Alignment: {scores.reasoning_alignment}% | "
            f"Factual Accuracy: {scores.factual_accuracy}%. "
            f"{error_note}{excluded_str}"
        )

        return ComparisonReport(
            comparison_id=comparison_id,
            case_id=case_id,
            case_title=case_title,
            mode="post_trial" if mode == "post_trial" else "manual",
            timestamp=timestamp,
            case_information=case_information,
            overall_assessment=assessment,
            verdict_comparison=verdict_comp,
            issue_comparison=issue_comp,
            factual_comparison=fact_comp,
            charge_comparison=charge_comp,
            witness_comparison=witness_comp,
            evidence_comparison=evidence_comp,
            legal_provision_comparison=legal_comp,
            reasoning_comparison=reasoning_comp,
            finding_comparison=finding_comp,
            final_order_comparison=order_comp,
            major_errors=major_errors,
            missing_important_points=missing_points,
            unrelated_hallucinated_points=unrelated_points,
            scores=scores,
            overall_conclusion=conclusion,
        )

    @staticmethod
    def _format_status(status: Any) -> str:
        if hasattr(status, "value"):
            return str(status.value)
        return str(status) if status is not None else ""

    @classmethod
    def format_report_text(cls, report: ComparisonReport) -> str:
        """Render the 17-section comparison report into structured plain text."""
        sep = "=" * 80
        sub_sep = "-" * 80

        lines = [
            sep,
            "AI COURT JUDGMENT VS REAL COURT JUDGMENT COMPARISON REPORT",
            f"Comparison ID : {report.comparison_id}",
            f"Case Title    : {report.case_title}",
            f"Case ID       : {report.case_id or 'N/A'}",
            f"Mode          : {report.mode.upper()}",
            f"Timestamp     : {report.timestamp}",
            sep,
            "",
            "1. CASE INFORMATION",
            sub_sep,
        ]
        for k, v in report.case_information.items():
            lines.append(f"  {k}: {v}")

        lines.extend([
            "",
            "2. OVERALL ASSESSMENT",
            sub_sep,
            report.overall_assessment,
            "",
            "3. VERDICT COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.verdict_comparison.status)}",
            f"  AI Verdict    : {report.verdict_comparison.ai_verdict}",
            f"  Real Verdict  : {report.verdict_comparison.real_verdict}",
            f"  Alignment     : {report.verdict_comparison.alignment.upper()} ({report.verdict_comparison.score}%)",
            f"  Explanation   : {report.verdict_comparison.explanation}",
            "",
            "4. ISSUE COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.issue_comparison.status)}",
            f"  Score         : {report.issue_comparison.score}%",
            f"  Explanation   : {report.issue_comparison.explanation}",
            f"  Matched Issues: {len(report.issue_comparison.matched_issues)}",
        ])
        for m in report.issue_comparison.matched_issues:
            lines.append(f"    - Real: '{m.get('real_issue', '')[:80]}...' <=> AI: '{m.get('ai_issue', '')[:80]}...'")
        if report.issue_comparison.ai_missed_issues:
            lines.append("  Omitted by AI:")
            for mi in report.issue_comparison.ai_missed_issues:
                lines.append(f"    - {mi[:100]}")
        if report.issue_comparison.ai_unrelated_issues:
            lines.append("  Unrelated Issues Introduced by AI:")
            for ui in report.issue_comparison.ai_unrelated_issues:
                lines.append(f"    - {ui[:100]}")

        lines.extend([
            "",
            "5. FACTUAL COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.factual_comparison.status)}",
            f"  Score         : {report.factual_comparison.score}% (Correctness: {report.factual_comparison.correctness_score}%, Completeness: {report.factual_comparison.completeness_score}%)",
            f"  Assessed Facts: AI {report.factual_comparison.assessed_ai_facts} | Real {report.factual_comparison.assessed_real_facts}",
            f"  Explanation   : {report.factual_comparison.explanation}",
            f"  Verified Facts: {len(report.factual_comparison.correct_facts)}",
            f"  Invented Facts: {len(report.factual_comparison.invented_facts)}",
        ])
        for iv in report.factual_comparison.invented_facts:
            lines.append(f"    - [INVENTED]: {iv[:100]}")

        lines.extend([
            "",
            "6. CHARGE COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.charge_comparison.status)}",
            f"  Score         : {report.charge_comparison.score}%",
            f"  Explanation   : {report.charge_comparison.explanation}",
        ])
        for hm in report.charge_comparison.historical_law_mismatches:
            lines.append(f"    - [HISTORICAL MISMATCH]: {hm}")
        for pc in report.charge_comparison.procedural_or_coaccused_charges:
            lines.append(f"    - [PROCEDURAL/CO-ACCUSED CONTEXT]: {pc}")

        is_wit_excluded = not report.witness_comparison.is_assessable or "witness_alignment" in report.scores.excluded_categories
        is_evi_excluded = not report.evidence_comparison.is_assessable or "evidence_alignment" in report.scores.excluded_categories

        lines.extend([
            "",
            "7. WITNESS COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.witness_comparison.status)}",
            f"  Assessable    : {report.witness_comparison.is_assessable}",
            f"  Score         : {'Not assessed' if is_wit_excluded else f'{report.witness_comparison.score}%'}",
            f"  AI Witnesses  : {report.witness_comparison.witness_count_ai} | Real: {report.witness_comparison.witness_count_real}",
            f"  Explanation   : {report.witness_comparison.explanation}",
            "",
            "8. EVIDENCE COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.evidence_comparison.status)}",
            f"  Assessable    : {report.evidence_comparison.is_assessable}",
            f"  Score         : {'Not assessed' if is_evi_excluded else f'{report.evidence_comparison.score}%'}",
            f"  Assessed Items: AI {report.evidence_comparison.assessed_ai_evidence} | Real {report.evidence_comparison.assessed_real_evidence}",
            f"  Explanation   : {report.evidence_comparison.explanation}",
        ])
        if report.evidence_comparison.correctly_considered:
            lines.append(f"  Correctly Considered: {', '.join(report.evidence_comparison.correctly_considered)}")
        if report.evidence_comparison.ignored_evidence:
            lines.append(f"  Omitted: {', '.join(report.evidence_comparison.ignored_evidence)}")
        if report.evidence_comparison.misattributed_evidence:
            lines.append(f"  Misinterpreted/Misattributed: {', '.join(report.evidence_comparison.misattributed_evidence)}")
        if report.evidence_comparison.misinterpreted_evidence:
            lines.append(f"  Incorrect Significance: {', '.join(report.evidence_comparison.misinterpreted_evidence)}")
        if report.evidence_comparison.invented_evidence:
            lines.append(f"  Unsupported/Inventions: {', '.join(report.evidence_comparison.invented_evidence)}")
        lines.extend([
            "",
            "9. LEGAL PROVISION COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.legal_provision_comparison.status)}",
            f"  Score         : {report.legal_provision_comparison.score}%",
            f"  Explanation   : {report.legal_provision_comparison.explanation}",
        ])
        if report.legal_provision_comparison.correct_provisions:
            lines.append(f"  Matched Provisions : {', '.join(report.legal_provision_comparison.correct_provisions)}")
        if report.legal_provision_comparison.missing_provisions:
            lines.append(f"  Missing Provisions : {', '.join(report.legal_provision_comparison.missing_provisions)}")
        if report.legal_provision_comparison.procedural_or_coaccused_provisions:
            lines.append(f"  Procedural/Co-accused: {', '.join(report.legal_provision_comparison.procedural_or_coaccused_provisions)}")
        if report.legal_provision_comparison.historically_inapplicable_provisions:
            lines.append(f"  Inapplicable Modern: {len(report.legal_provision_comparison.historically_inapplicable_provisions)} citations (BNS/BSA applied to historical offence)")

        lines.extend([
            "",
            "10. LEGAL REASONING COMPARISON (RATIO DECIDENDI)",
            sub_sep,
            f"  Status        : {cls._format_status(report.reasoning_comparison.status)}",
            f"  Score         : {report.reasoning_comparison.score}%",
            f"  Addressed Real Legal Issue : {report.reasoning_comparison.addressed_actual_legal_issue}",
            f"  Applied Correct Law        : {report.reasoning_comparison.applied_correct_law}",
            f"  Evaluated Missing Evidence : {report.reasoning_comparison.considered_missing_evidence}",
            f"  Explanation                : {report.reasoning_comparison.explanation}",
        ])
        if report.reasoning_comparison.theme_evaluations:
            lines.append("  Substantive Judicial Themes Evaluated:")
            for t in report.reasoning_comparison.theme_evaluations:
                lines.append(f"    • [{t.match_status}] {t.theme_name}")
                lines.append(f"      - Real Court Position : {t.real_court_position}")
                lines.append(f"      - AI Court Position   : {t.ai_position}")
                if t.source_evidence:
                    lines.append(f"      - Source Evidence     : {t.source_evidence}")

        lines.extend([
            "",
            "11. FINDING COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.finding_comparison.status)}",
            f"  Score         : {report.finding_comparison.score}%",
            f"  Explanation   : {report.finding_comparison.explanation}",
            "",
            "12. FINAL ORDER COMPARISON",
            sub_sep,
            f"  Status        : {cls._format_status(report.final_order_comparison.status)}",
            f"  Score         : {report.final_order_comparison.score}%",
            f"  AI Final Order: {report.final_order_comparison.ai_final_order[:120]}...",
            f"  Real Order    : {report.final_order_comparison.real_final_order[:120]}...",
            f"  Alignment     : {report.final_order_comparison.alignment.upper()}",
            "",
            "13. MAJOR ERRORS & DISCREPANCIES",
            sub_sep,
        ])
        if report.major_errors:
            for i, err in enumerate(report.major_errors, 1):
                lines.extend([
                    f"  [{i}] Type: {err.type.upper()} (Severity: {err.severity.upper()})",
                    f"      AI Claim     : {err.ai_claim}",
                    f"      Real Position: {err.real_court_position}",
                    f"      Explanation  : {err.explanation}",
                ])
        else:
            lines.append("  No major errors detected.")

        lines.extend([
            "",
            "14. MISSING IMPORTANT POINTS",
            sub_sep,
        ])
        if report.missing_important_points:
            for pt in report.missing_important_points:
                lines.append(f"  - {pt}")
        else:
            lines.append("  No critical missing points flagged.")

        lines.extend([
            "",
            "15. UNRELATED / HALLUCINATED POINTS",
            sub_sep,
        ])
        if report.unrelated_hallucinated_points:
            for uh in report.unrelated_hallucinated_points:
                lines.append(f"  - {uh}")
        else:
            lines.append("  No extraneous hallucinated points flagged.")

        # Format weights and category scores
        score_lines = []
        cat_map = [
            ("verdict_alignment", "Verdict Alignment", report.scores.verdict_alignment),
            ("reasoning_alignment", "Legal Reasoning", report.scores.reasoning_alignment),
            ("factual_accuracy", "Factual Accuracy", report.scores.factual_accuracy),
            ("issue_alignment", "Issue Alignment", report.scores.issue_alignment),
            ("evidence_alignment", "Evidence Alignment", report.scores.evidence_alignment),
            ("charge_alignment", "Charge Alignment", report.scores.charge_alignment),
            ("final_order_alignment", "Final Order Alignment", report.scores.final_order_alignment),
        ]
        for key, label, val in cat_map:
            if key in report.scores.excluded_categories:
                weight_str = "EXCLUDED (Insufficient Data)"
                score_lines.append(f"  {label:<24}: {'Not assessed':>12} ({weight_str})")
            else:
                act_w = report.scores.active_weights.get(key, report.scores.weights.get(key, 0.0))
                weight_str = f"Active Weight: {act_w:.1%}"
                score_lines.append(f"  {label:<24}: {val:>6.2f}% ({weight_str})")

        is_partial = bool(report.scores.excluded_categories)
        benchmark_name = "PARTIAL BENCHMARK SCORE" if is_partial else "OVERALL BENCHMARK SCORE"
        benchmark_note = "Partial Normalized" if is_partial else "Weighted Multi-Category"

        lines.extend([
            "",
            "16. COMPREHENSIVE BENCHMARK SCORES",
            sub_sep,
            *score_lines,
            sub_sep,
            f"  SUBSTANTIVE BENCHMARK SCORE : {report.scores.substantive_score:>6.2f}% (Reasoning/Substance Only)" if report.scores.substantive_score is not None else "  SUBSTANTIVE BENCHMARK SCORE :    N/A",
            f"  VERDICT BENCHMARK SCORE     : {report.scores.verdict_score:>6.2f}% (Pure Outcome Alignment)" if report.scores.verdict_score is not None else "  VERDICT BENCHMARK SCORE     :    N/A",
            f"  {benchmark_name:<28}: {report.scores.overall_score:>6.2f}% ({benchmark_note})",
            f"  ACTIVE WEIGHT DENOMINATOR   : {report.scores.active_weight_denominator:.1%} of the fixed 100% rubric",
            f"  Scoring Formula             : {report.scores.scoring_formula}",
            "",
            "17. OVERALL CONCLUSION",
            sub_sep,
            report.overall_conclusion,
            sep,
        ])

        return "\n".join(lines)

    @classmethod
    def write_report_pdf(cls, report_text: str, output_path: Path) -> Path:
        """Render comparison report text into a multi-page PDF document using PyMuPDF."""
        doc = pymupdf.open()
        page_width, page_height = 595, 842
        margin = 54

        lines = report_text.split("\n")
        current_page = doc.new_page(width=page_width, height=page_height)
        y = margin + 20
        line_height = 13

        for line in lines:
            if y > page_height - margin - 20:
                # Add footer
                footer_text = f"Page {len(doc)} — AI Court of India Comparison Engine"
                current_page.insert_text(
                    pymupdf.Point(page_width / 2 - 80, page_height - margin + 10),
                    footer_text,
                    fontsize=8,
                    color=(0.4, 0.4, 0.4),
                )
                current_page = doc.new_page(width=page_width, height=page_height)
                y = margin + 20

            is_header = line.startswith("=") or line.startswith("-") or (line and line[0].isdigit() and ". " in line[:4])
            is_title = "COMPARISON REPORT" in line
            fontsize = 11 if is_title else (10 if is_header else 9)
            fontname = "helv"

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

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        doc.close()
        return output_path
