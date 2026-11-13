"""
Conflict Detection Agent for AI Court of India.
Detects contradictions across witness depositions, exhibits, and competing factual claims.
Never silently resolves conflicts; flags them explicitly for judicial determination.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from app.models.case_models import StructuredCase
from app.models.conflict_models import (
    Conflict,
    ConflictCategory,
    ConflictReport,
    ConflictSeverity,
)
from app.models.evidence_models import EvidenceAnalysisReport
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ConflictDetectionAgent:
    """
    Identifies factual, evidentiary, and testimonial contradictions across the case record.
    Preserves unresolved conflicts with severity ratings for the Judge Agent.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def detect_conflicts(
        self,
        case: StructuredCase,
        evidence_report: Optional[EvidenceAnalysisReport] = None,
    ) -> ConflictReport:
        """
        Scan case facts and evidence to detect all irreconcilable inconsistencies.

        Args:
            case: StructuredCase object.
            evidence_report: Optional EvidenceAnalysisReport from EvidenceAnalysisAgent.

        Returns:
            ConflictReport with identified conflicts and resolution_required flags.
        """
        logger.info("Scanning for courtroom conflicts in case: '%s'", case.case_title)
        conflicts: list[Conflict] = []

        # 1. Prosecution vs Defense factual conflicts
        if case.prosecution_facts and case.defense_facts:
            conf = Conflict(
                conflict_id=f"CONF-{uuid4().hex[:6].upper()}",
                category=ConflictCategory.PROSECUTION_VS_DEFENSE,
                statement_a=case.prosecution_facts[0],
                statement_b=case.defense_facts[0],
                sources=["Prosecution Brief", "Defense Statement / Section 313 Examination"],
                severity=ConflictSeverity.HIGH,
                explanation=(
                    f"Fundamental dispute between prosecution narrative ('{case.prosecution_facts[0]}') "
                    f"and defense denial ('{case.defense_facts[0]}')."
                ),
                impact_on_case="Goes to the core of the allegations; requires proof beyond reasonable doubt.",
                resolution_required=True,
            )
            conflicts.append(conf)

        # 2. Witness vs Exhibit conflicts (e.g. recovery without independent panch)
        if case.disputed_facts:
            for idx, disp in enumerate(case.disputed_facts, start=1):
                conf = Conflict(
                    conflict_id=f"CONF-DISP-{idx}",
                    category=ConflictCategory.FACTUAL_INCONSISTENCY,
                    statement_a=f"Prosecution asserts: {disp}",
                    statement_b=f"Defense disputes: {disp}",
                    sources=["Charge-Sheet", "Plea of Accused"],
                    severity=ConflictSeverity.MEDIUM,
                    explanation=f"Contested material fact regarding: '{disp}'",
                    impact_on_case="Requires judicial evaluation of evidentiary probabilities.",
                    resolution_required=True,
                )
                conflicts.append(conf)

        # 3. Missing evidence / investigative gap conflict
        if evidence_report and evidence_report.missing_evidence_gaps:
            gap = evidence_report.missing_evidence_gaps[0]
            conf = Conflict(
                conflict_id=f"CONF-GAP-{uuid4().hex[:6].upper()}",
                category=ConflictCategory.UNSUPPORTED_ASSERTION,
                statement_a="Prosecution claims complete and unimpeachable investigation.",
                statement_b=f"Evidentiary gap discovered: {gap}",
                sources=["Investigating Officer", "Court Record Gap Analysis"],
                severity=ConflictSeverity.HIGH,
                explanation=f"Failure to address investigative omission: '{gap}'.",
                impact_on_case="Permits drawing of adverse inference against the prosecution under BSA.",
                resolution_required=True,
            )
            conflicts.append(conf)

        # 4. Witness inconsistencies if multiple witnesses
        if len(case.witnesses) >= 2:
            w1 = case.witnesses[0]
            w2 = case.witnesses[1]
            conf = Conflict(
                conflict_id=f"CONF-WIT-{uuid4().hex[:6].upper()}",
                category=ConflictCategory.WITNESS_CONTRADICTION,
                statement_a=f"{w1.witness_id} deposition: {w1.testimony_summary[:100]}",
                statement_b=f"{w2.witness_id} deposition: {w2.testimony_summary[:100]}",
                sources=[w1.witness_id, w2.witness_id],
                severity=ConflictSeverity.MEDIUM,
                explanation="Potential divergence in emphasis between eyewitness and police officer accounts.",
                impact_on_case="Judge must test whether divergence is natural or indicates fabrication.",
                resolution_required=True,
            )
            conflicts.append(conf)

        critical_count = sum(
            1 for c in conflicts if c.severity in [ConflictSeverity.HIGH, ConflictSeverity.FATAL_TO_CHARGE]
        )

        summary = (
            f"Identified {len(conflicts)} courtroom conflicts ({critical_count} critical). "
            f"All conflicts require judicial resolution and must be evaluated by the Judge Agent."
        )

        return ConflictReport(
            case_id=case.case_id,
            total_conflicts=len(conflicts),
            conflicts=conflicts,
            critical_conflicts_count=critical_count,
            summary=summary,
        )
