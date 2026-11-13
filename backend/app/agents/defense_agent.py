"""
Defense Agent for AI Court of India.
Constructs adversarial defense theory, raises reasonable doubt, challenges evidentiary
chain-of-custody, and rigorously categorizes arguments into
FACT, EVIDENCE, LEGAL_RULE, INFERENCE, and ARGUMENT.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.evidence_models import EvidenceAnalysisReport, EvidenceType
from app.models.judgment_models import (
    ArgumentComponent,
    DefenseCase,
    ProsecutionCase,
    StatementType,
)
from app.models.legal_models import LegalResearchResult, WebResearchResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class DefenseAgent:
    """
    Simulates the Defense Counsel for the accused.
    Demands strict proof beyond reasonable doubt, challenges procedure, and highlights investigative gaps.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def build_defense(
        self,
        case: StructuredCase,
        prosecution: Optional[ProsecutionCase] = None,
        evidence_report: Optional[EvidenceAnalysisReport] = None,
        legal_research: Optional[LegalResearchResult] = None,
        web_research: Optional[WebResearchResult] = None,
    ) -> DefenseCase:
        """
        Synthesize the complete adversarial defense submission.

        Args:
            case: StructuredCase instance.
            evidence_report: Optional EvidenceAnalysisReport instance.
            legal_research: Optional grounded defense research from LegalResearchAgent.
            web_research: Optional external precedents from WebResearchAgent.

        Returns:
            DefenseCase object with epistemically-classified arguments.
        """
        logger.info("Defense building defense for: '%s'", case.case_title)

        # Handle flexible argument positions for backward compatibility with positional test calls
        if isinstance(prosecution, EvidenceAnalysisReport):
            actual_evidence = prosecution
            actual_legal = evidence_report if isinstance(evidence_report, LegalResearchResult) else legal_research
            prosecution = None
            evidence_report = actual_evidence
            legal_research = actual_legal

        accused_names = ", ".join(case.accused) if case.accused else "the accused"
        theory = (
            f"The defence submits that {accused_names} has been falsely implicated based on nothing more than "
            f"suspicion. The prosecution case has serious contradictions, procedural failures, "
            f"and investigative gaps, which mean the charge has not been proved beyond reasonable doubt."
        )

        components: list[ArgumentComponent] = []

        # FACT
        if case.defense_facts:
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.FACT,
                    content=f"Defense fact: {case.defense_facts[0]}",
                    source_reference="Plea of Accused & Cross-Examination Record",
                )
            )

        # EVIDENCE
        # Point out evidentiary infirmity
        if evidence_report:
            for item in evidence_report.evidence_items:
                if item.limitations:
                    components.append(
                        ArgumentComponent(
                            statement_type=StatementType.EVIDENCE,
                            content=f"Infirmity in {item.id} ({item.description}): {item.limitations[0]}",
                            source_reference=f"Evidence Item {item.id} limitations",
                        )
                    )
                    break
        if not any(c.statement_type == StatementType.EVIDENCE for c in components):
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.EVIDENCE,
                    content="The seizure memo does not have any independent civilian witness to verify the recovery — it was prepared only by police personnel.",
                    source_reference="Trial Record & Seizure Memo",
                )
            )

        # LEGAL_RULE
        if legal_research and legal_research.citations:
            top_cit = legal_research.citations[0]
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.LEGAL_RULE,
                    content=(
                        f"Under {top_cit}: The burden of proving guilt lies entirely on the prosecution. "
                        f"The accused does not have to prove innocence — guilt must be established beyond all reasonable doubt, not just on probability."
                    ),
                    source_reference=top_cit,
                )
            )
        else:
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.LEGAL_RULE,
                    content=(
                        "Under Article 21 of the Constitution of India and Section 104 BSA: The burden of proving guilt lies entirely on the prosecution. "
                        "The accused does not have to prove innocence — guilt must be established beyond all reasonable doubt, not just on probability."
                    ),
                    source_reference="Constitution of India Art. 21 & BSA",
                )
            )

        # INFERENCE
        components.append(
            ArgumentComponent(
                statement_type=StatementType.INFERENCE,
                content=(
                    "Because no independent civilian witnesses were brought in during the recovery, even though they were available nearby, "
                    "the Court should treat the alleged recovery as doubtful and suspect."
                ),
                source_reference="Adverse inference under Section 119 BSA",
            )
        )

        # ARGUMENT
        components.append(
            ArgumentComponent(
                statement_type=StatementType.ARGUMENT,
                content=(
                    "When the evidence on record can reasonably support two views — one pointing to guilt and one pointing to innocence — "
                    "the law requires the Court to adopt the view that favours the accused."
                ),
                source_reference="Fundamental Principle of Indian Criminal Jurisprudence",
            )
        )

        # REBUTTAL to prosecution (Contextual interaction)
        if prosecution and prosecution.argument_components:
            first_pros_arg = prosecution.argument_components[0].content
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.ARGUMENT,
                    content=f"The prosecution claims that '{first_pros_arg}'. However, this assertion rests on an unverified assumption and is not supported by any independent evidence.",
                    source_reference="Rebuttal to Prosecution",
                )
            )

        # Reasonable doubt grounds
        reasonable_doubt_grounds = [
            "The prosecution has not ruled out the possibility that the recovery was planted.",
            "No independent civilian witnesses were present during the alleged seizure.",
        ]
        if evidence_report and any(e.type == EvidenceType.ELECTRONIC for e in evidence_report.evidence_items):
            reasonable_doubt_grounds.append(
                "Electronic records relied upon by prosecution lack mandatory certification under Section 63 BSA."
            )

        # Missing evidence highlighted
        missing_evidence = evidence_report.missing_evidence_gaps.copy() if evidence_report else []
        if not missing_evidence:
            missing_evidence.append("Failure to record statements of independent eye-witnesses at the scene.")

        # Alternative interpretation
        alt_narrative = (
            f"The accused was merely present in the area, or was innocently in possession of goods without knowing "
            f"anything about their prior illegal history. The prosecution never proved the dishonest knowledge required by law."
        )

        citations = legal_research.citations.copy() if legal_research else [
            "Constitution of India Art. 21",
            "Bharatiya Sakshya Adhiniyam, 2023 Section 104",
        ]
        if web_research and web_research.sources:
            citations.append(f"Precedent: {web_research.sources[0].title} ({web_research.sources[0].url})")

        return DefenseCase(
            case_id=case.case_id,
            defense_theory=theory,
            argument_components=components,
            reasonable_doubt_grounds=reasonable_doubt_grounds,
            witness_inconsistencies_highlighted=["Discrepancies in the timeline of arrest and recovery."],
            missing_evidence_highlighted=missing_evidence,
            alternative_interpretation=alt_narrative,
            legal_citations=citations,
            final_prayer=(
                "It is respectfully prayed that this Hon'ble Court extend the benefit of doubt to the accused "
                "and pass an order of honourable acquittal."
            ),
        )
