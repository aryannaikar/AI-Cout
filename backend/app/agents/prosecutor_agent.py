"""
Prosecutor Agent for AI Court of India.
Constructs adversarial prosecution arguments, maps evidence to statutory elements,
addresses weaknesses proactively, and rigorously categorizes propositions into
FACT, EVIDENCE, LEGAL_RULE, INFERENCE, and ARGUMENT.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import (
    ArgumentComponent,
    ProsecutionCase,
    StatementType,
)
from app.models.legal_models import LegalResearchResult, WebResearchResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ProsecutorAgent:
    """
    Simulates the State / Prosecution counsel.
    Formulates prosecution theory and marshals oral and documentary evidence.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def build_case(
        self,
        case: StructuredCase,
        evidence_report: Optional[EvidenceAnalysisReport] = None,
        legal_research: Optional[LegalResearchResult] = None,
        web_research: Optional[WebResearchResult] = None,
    ) -> ProsecutionCase:
        """
        Synthesize the complete adversarial prosecution submission.

        Args:
            case: StructuredCase instance.
            evidence_report: Optional EvidenceAnalysisReport instance.
            legal_research: Optional grounded research from LegalResearchAgent.
            web_research: Optional external precedent from WebResearchAgent.

        Returns:
            ProsecutionCase object with epistemically-classified arguments.
        """
        logger.info("Prosecutor building case for: '%s'", case.case_title)

        # 1. Prosecution Theory
        accused_names = ", ".join(case.accused) if case.accused else "the accused"
        theory = (
            f"The prosecution submits that on the date of the incident, {accused_names} acted with "
            f"dishonest intent in violation of the law. The physical evidence and witness testimony together "
            f"establish guilt beyond reasonable doubt."
        )

        # 2. Statutory Elements that must be proven
        statutory_elements = []
        for ch in case.charges:
            statutory_elements.append(f"Proof of the acts and guilty intention required under {ch.section} ({ch.statute}).")
        statutory_elements.append("Proof that the accused knowingly possessed the property without lawful justification (conscious possession).")

        # 3. Categorized Argument Components (FACT, EVIDENCE, LEGAL_RULE, INFERENCE, ARGUMENT)
        components: list[ArgumentComponent] = []

        # FACT
        if case.prosecution_facts:
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.FACT,
                    content=f"Primary fact: {case.prosecution_facts[0]}",
                    source_reference="FIR & Charge-Sheet Narrative",
                )
            )

        # EVIDENCE
        if case.witnesses:
            w0 = case.witnesses[0]
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.EVIDENCE,
                    content=f"{w0.witness_id} testified: {w0.testimony_summary}",
                    source_reference=f"Deposition of {w0.witness_name} ({w0.witness_id})",
                )
            )
        if case.exhibits:
            ex0 = case.exhibits[0]
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.EVIDENCE,
                    content=f"Physical proof: {ex0.title} was formally recovered and marked in trial.",
                    source_reference=f"Exhibit {ex0.exhibit_id}",
                )
            )

        # LEGAL_RULE
        if legal_research and legal_research.citations:
            top_cit = legal_research.citations[0]
            top_prov = legal_research.applicable_provisions[0] if legal_research.applicable_provisions else None
            prov_text = top_prov.text[:150] if top_prov else "Statutory definition"
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.LEGAL_RULE,
                    content=f"Under {top_cit}: {prov_text}...",
                    source_reference=top_cit,
                )
            )
        elif case.charges:
            ch0 = case.charges[0]
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.LEGAL_RULE,
                    content=f"Under {ch0.statute} Section {ch0.section}: The prosecution must establish all statutory elements beyond reasonable doubt.",
                    source_reference=f"{ch0.statute} Section {ch0.section}",
                )
            )
        else:
            components.append(
                ArgumentComponent(
                    statement_type=StatementType.LEGAL_RULE,
                    content="Under Indian penal law: The prosecution bears the burden of establishing the statutory ingredients of the alleged offenses.",
                    source_reference="Governing Penal Provisions",
                )
            )

        # INFERENCE
        components.append(
            ArgumentComponent(
                statement_type=StatementType.INFERENCE,
                content=(
                    "Given that the stolen property was recovered directly and immediately from the accused, "
                    "the Court must infer that the accused knowingly held the property with dishonest intent, as presumed under the law."
                ),
                source_reference="Evidentiary presumption under BSA / Section 119",
            )
        )

        # ARGUMENT
        components.append(
            ArgumentComponent(
                statement_type=StatementType.ARGUMENT,
                content=(
                    "The defence's blanket denial is a mere afterthought, unsupported by any credible material. "
                    "The police witnesses had no reason or motive to falsely implicate the accused."
                ),
                source_reference="Prosecution Final Submissions",
            )
        )

        # 4. Proactive mitigation of weaknesses
        addressed_weaknesses = []
        if evidence_report and evidence_report.missing_evidence_gaps:
            for gap in evidence_report.missing_evidence_gaps:
                addressed_weaknesses.append(
                    f"On the point of '{gap}': It is settled law that not examining public witnesses does not "
                    f"automatically discredit a police recovery, so long as the police testimony is reliable and credible."
                )
        else:
            addressed_weaknesses.append(
                "The recovery memos and procedural steps were completed at the time of seizure, in line with standard procedure."
            )

        citations = legal_research.citations.copy() if legal_research else []
        if not citations and case.charges:
            citations = [f"{ch.statute} Section {ch.section}" for ch in case.charges]
        if web_research and web_research.sources:
            citations.append(f"Precedent: {web_research.sources[0].title} ({web_research.sources[0].url})")

        return ProsecutionCase(
            case_id=case.case_id,
            prosecution_theory=theory,
            statutory_elements=statutory_elements,
            argument_components=components,
            supporting_witnesses=[w.witness_id for w in case.witnesses],
            supporting_exhibits=[e.exhibit_id for e in case.exhibits],
            addressed_weaknesses=addressed_weaknesses,
            legal_citations=citations,
            final_prayer=(
                "It is respectfully prayed that this Hon'ble Court find the accused guilty as charged "
                "and pass an appropriate sentence in accordance with law."
            ),
        )
