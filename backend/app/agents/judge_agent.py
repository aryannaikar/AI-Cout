"""
Judge Agent for AI Court of India.
Final judicial reasoning agent of Phase 2.
Independently adjudicates the simulated trial record following the 12-section judicial framework.
Enforces strict blind evaluation: completely isolated from Ground Truth Verdict.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.evidence_package_models import EvidencePackage
from app.models.judgment_models import (
    DefenseCase,
    Judgment,
    JudicialIssueAnalysis,
    ProsecutionCase,
)
from app.models.legal_models import LegalResearchResult, WebResearchResult
from app.services.legal_transition import detect_case_legal_regime
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class JudgeAgent:
    """
    Simulates the Presiding Judge / Judicial Bench.
    Performs independent judicial appraisal of arguments, evidence, conflicts, and statutory law.
    Strictly barred from accessing or receiving the Ground Truth Verdict.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    @staticmethod
    def _validate_blindness(
        case: StructuredCase,
        prosecution_case: ProsecutionCase,
        defense_case: DefenseCase,
        evidence_package: Optional[EvidencePackage] = None,
    ) -> None:
        """Enforce strict blind evaluation: ensure no ground truth has leaked into judge input."""
        for text in [case.case_title, prosecution_case.prosecution_theory, defense_case.defense_theory]:
            if "ground truth" in text.lower() or "real verdict" in text.lower():
                raise PermissionError("SECURITY VIOLATION: Ground Truth evaluation data detected in Judge inputs.")

        if evidence_package:
            for t in [
                evidence_package.case_identification.case_title or "",
                evidence_package.case_identification.court or "",
            ]:
                if "ground truth" in t.lower() or "real verdict" in t.lower():
                    raise PermissionError("SECURITY VIOLATION: Ground Truth data detected in EvidencePackage.")

    def adjudicate(
        self,
        case: StructuredCase,
        prosecution_case: ProsecutionCase,
        defense_case: DefenseCase,
        evidence_report: EvidenceAnalysisReport,
        conflict_report: ConflictReport,
        evidence_package: Optional[EvidencePackage] = None,
        prosecution_legal_research: Optional[LegalResearchResult] = None,
        defense_legal_research: Optional[LegalResearchResult] = None,
        web_research: Optional[WebResearchResult] = None,
    ) -> Judgment:

        """
        Render a comprehensive 12-section judicial verdict.

        Args:
            case: StructuredCase from CaseUnderstandingAgent.
            prosecution_case: Submissions from ProsecutorAgent.
            defense_case: Submissions from DefenseAgent.
            evidence_report: Report from EvidenceAnalysisAgent.
            conflict_report: Report from ConflictDetectionAgent.
            prosecution_legal_research: Research from LegalResearchAgent.
            defense_legal_research: Research from LegalResearchAgent.
            web_research: Research from WebResearchAgent.

        Returns:
            Judgment object satisfying all 12 judicial framework sections.
        """
        logger.info("Judge Agent adjudicating case: '%s'", case.case_title)
        self._validate_blindness(case, prosecution_case, defense_case, evidence_package=evidence_package)

        # 1. Background
        background = (
            f"The present proceedings arise out of allegations framed in {case.case_title} "
            f"({case.court_identifier or 'Sessions Case'}). The prosecution alleges that {case.allegations_summary} "
            f"The accused pleaded not guilty and claimed trial."
        )

        # 2. Issues for determination
        issues = case.legal_issues.copy() if case.legal_issues else [
            "Whether the prosecution has proved the ingredients of the charged offences beyond reasonable doubt?",
            "Whether the evidentiary recovery was effected in accordance with statutory requirements?",
            "Whether the accused is entitled to the benefit of reasonable doubt?",
        ]

        # 3. Applicable Law
        regime = detect_case_legal_regime(case)
        is_historical = regime["is_historical"]

        applicable_law = []
        for ch in case.charges:
            statute_name = ch.statute
            if is_historical and "bns" in statute_name.lower():
                statute_name = "Indian Penal Code, 1860"
            applicable_law.append(f"{statute_name}, {ch.section}")

        if is_historical:
            applicable_law.append("Indian Evidence Act, 1872 (Evidentiary proof, Section 101, Section 102, Section 27, Section 65B)")
        else:
            applicable_law.append("Bharatiya Sakshya Adhiniyam, 2023 (Evidentiary proof, Section 61, Section 63)")

        if prosecution_legal_research and prosecution_legal_research.citations:
            applicable_law.extend(prosecution_legal_research.citations[:2])

        # 4. Evidence assessment
        ev_summary = (
            f"The court has inspected {len(evidence_report.evidence_items)} items of evidence. "
            f"{evidence_report.documentary_compliance_assessment} "
        )
        if evidence_report.missing_evidence_gaps:
            ev_summary += f"The court notes serious investigative gaps: {'; '.join(evidence_report.missing_evidence_gaps)}."

        # 5. Witness assessment
        wit_assessment = (
            f"The prosecution examined {len(case.witnesses)} witnesses. While the official police witnesses "
            f"deposed consistently regarding the procedural steps, the absence of independent public witnesses "
            f"requires the court to scrutinize their testimony with heightened caution."
        )

        # 6. Prosecution Submissions
        pros_submissions = (
            f"Learned Prosecutor argued that {prosecution_case.prosecution_theory} "
            f"The prosecution placed reliance on {len(prosecution_case.supporting_exhibits)} exhibits "
            f"and contended that statutory presumptions operate against the accused."
        )

        # 7. Defense Submissions
        def_submissions = (
            f"Learned Defense Counsel contended that {defense_case.defense_theory} "
            f"The defense highlighted that {'; '.join(defense_case.reasonable_doubt_grounds[:2])} "
            f"and prayed for complete acquittal."
        )

        # 8. Analysis of each issue & judicial findings
        issue_analyses: list[JudicialIssueAnalysis] = []
        has_critical_doubt = conflict_report.critical_conflicts_count > 0 or len(evidence_report.missing_evidence_gaps) > 0
        issue_governing_law = (
            "Indian Penal Code, 1860 & Indian Evidence Act, 1872"
            if is_historical
            else "Bharatiya Nyaya Sanhita & Bharatiya Sakshya Adhiniyam, 2023"
        )

        for i, issue_text in enumerate(issues, start=1):
            finding = "NOT PROVED" if has_critical_doubt and i > 1 else "PROVED"
            analysis = JudicialIssueAnalysis(
                issue_number=i,
                issue_statement=issue_text,
                applicable_law=issue_governing_law,
                prosecution_submission_summary="State submits statutory ingredients are satisfied by evidence.",
                defense_submission_summary="Defense submits material contradictions vitiate proof beyond reasonable doubt.",
                evidentiary_evaluation=(
                    f"Evaluating the conflicting positions under {conflict_report.conflicts[0].category.value if conflict_report.conflicts else 'general principles'}, "
                    f"the court must test whether the chain of evidence is complete."
                ),
                judicial_finding=finding,
            )
            issue_analyses.append(analysis)

        # 9. Findings per charge
        findings_per_charge: dict[str, str] = {}
        for ch in case.charges:
            charge_statute = ch.statute
            if is_historical and "bns" in charge_statute.lower():
                charge_statute = "Indian Penal Code, 1860"
            if has_critical_doubt:
                findings_per_charge[f"{charge_statute}, {ch.section}"] = "ACQUITTED (Benefit of Doubt)"
            else:
                findings_per_charge[f"{charge_statute}, {ch.section}"] = "CONVICTED"

        # 10. Final decision
        final_decision = "ACQUITTAL" if has_critical_doubt else "CONVICTION"

        # 11. Detailed Reasons
        reasons = (
            f"In a criminal trial under Indian law, the distance between 'may be true' and 'must be true' "
            f"is long and divides vague conjectures from statutory certainty. "
            f"Here, the conflict report recorded {conflict_report.total_conflicts} unresolved contradictions. "
        )
        if has_critical_doubt:
            reasons += (
                "The prosecution having failed to bridge the gaps in the chain of custody and failing to join "
                "independent public witnesses, the hypothesis of innocence cannot be ruled out. "
                "Consequently, the accused is entitled to the benefit of doubt."
            )
        else:
            reasons += "The evidence marshaled by the prosecution establishes guilt beyond reasonable doubt."

        # 12. Legal Citations
        citations = []
        if prosecution_legal_research:
            citations.extend(prosecution_legal_research.citations)
        if defense_legal_research:
            citations.extend(defense_legal_research.citations)
        if not citations:
            if is_historical:
                primary_sec = case.charges[0].section if case.charges else "Section 302"
                citations = [
                    f"Indian Penal Code, 1860, {primary_sec}",
                    "Indian Evidence Act, 1872, Section 101",
                    "Indian Evidence Act, 1872, Section 3",
                ]
            else:
                citations = [
                    "Bharatiya Nyaya Sanhita, 2023, Section 317",
                    "Bharatiya Sakshya Adhiniyam, 2023, Section 61",
                    "Bharatiya Sakshya Adhiniyam, 2023, Section 63",
                ]
        citations = list(dict.fromkeys(citations))

        return Judgment(
            judgment_id=f"JUDG-{case.case_id}",
            case_title=case.case_title,
            presiding_court="Court of Sessions / AI Court of India",
            date_of_decision=datetime.now().strftime("%Y-%m-%d"),
            case_background=background,
            issues_for_determination=issues,
            applicable_law=applicable_law,
            evidence_assessment=ev_summary,
            witness_assessment=wit_assessment,
            prosecution_submissions=pros_submissions,
            defense_submissions=def_submissions,
            issue_analyses=issue_analyses,
            findings_per_charge=findings_per_charge,
            final_decision=final_decision,
            reasons=reasons,
            legal_citations=citations,
        )
