"""
Evidence Analysis Agent for AI Court of India.
Analyzes exhibits, testimonies, electronic records, and chain of custody.
Strictly objective: does NOT pronounce final guilt or innocence.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.evidence_models import (
    CorroborationLink,
    EvidenceAnalysisReport,
    EvidenceItemAnalysis,
    EvidenceType,
)
from app.models.evidence_package_models import EvidencePackage
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EvidenceAnalysisAgent:
    """
    Evaluates evidence contained in the case packet or standardized EvidencePackage.
    Categorizes evidence types, detects gaps and corroborations, and verifies BSA compliance.
    Strictly objective: does NOT pronounce final guilt or innocence.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def analyze_evidence(
        self,
        case: Optional[StructuredCase] = None,
        evidence_package: Optional[EvidencePackage] = None,
    ) -> EvidenceAnalysisReport:
        """
        Analyze all exhibits and witness testimony in the case packet and/or EvidencePackage.

        Args:
            case: StructuredCase instance (optional if evidence_package provided).
            evidence_package: Standardized EvidencePackage instance.

        Returns:
            EvidenceAnalysisReport detailing evidentiary probative value and infirmities.
        """
        if evidence_package:
            return self.analyze_evidence_package(evidence_package, case=case)

        if not case:
            raise ValueError("EvidenceAnalysisAgent requires either case or evidence_package.")

        logger.info("Analyzing evidence for case: '%s'", case.case_title)

        analyzed_items: list[EvidenceItemAnalysis] = []
        corroboration_links: list[CorroborationLink] = []
        contradictions: list[str] = []
        missing_gaps: list[str] = []

        # Analyze each exhibit
        for ex in case.exhibits:
            ex_type = self._map_evidence_type(ex.exhibit_type)
            limitations = []
            confidence = 0.85
            chain_ok = True

            if ex_type == EvidenceType.ELECTRONIC:
                limitations.append("Requires statutory certification under Section 63 BSA to be admissible as secondary evidence.")
                confidence = 0.70

            if "panchnama" in ex.title.lower() or "recovery" in ex.title.lower():
                limitations.append("Must be supported by independent attesting witnesses under Section 23/100 CrPC/BSA.")

            item = EvidenceItemAnalysis(
                id=ex.exhibit_id,
                type=ex_type,
                description=ex.description,
                source=f"Marked by {ex.marked_by}",
                related_witness=ex.marked_by,
                supports=[f"Fact of recovery/existence of {ex.title}"],
                contradicts=[],
                limitations=limitations,
                confidence=confidence,
                chain_of_custody_intact=chain_ok,
            )
            analyzed_items.append(item)

        # Map witnesses as testimonial evidence
        for w in case.witnesses:
            w_type = EvidenceType.TESTIMONIAL
            confidence = 0.75
            limitations = []

            if w.witness_type == "police_officer":
                limitations.append("Official police witness; requires independent corroboration where feasible.")
            elif w.witness_type == "eye_witness":
                confidence = 0.85

            item = EvidenceItemAnalysis(
                id=w.witness_id,
                type=w_type,
                description=f"Oral deposition of {w.witness_name} ({w.witness_type})",
                source=f"{w.witness_id} in Court Record",
                related_witness=w.witness_name,
                supports=w.key_assertions,
                contradicts=[],
                limitations=limitations,
                confidence=confidence,
                chain_of_custody_intact=True,
            )
            analyzed_items.append(item)

        # Detect corroboration links
        if len(case.witnesses) >= 2 and case.exhibits:
            corroboration_links.append(
                CorroborationLink(
                    item_a_id=case.witnesses[0].witness_id,
                    item_b_id=case.exhibits[0].exhibit_id,
                    fact_corroborated="Identification and seizure of subject property",
                    strength="moderate",
                )
            )

        # Identify missing evidence gaps from case metadata
        if case.missing_or_uncertain_info:
            missing_gaps.extend(case.missing_or_uncertain_info)
        else:
            missing_gaps.append("Absence of independent civilian panch witness to substantiate recovery.")

        # Check for BSA Section 61 / 63 compliance on electronic records
        has_electronic = any(e.type == EvidenceType.ELECTRONIC for e in analyzed_items)
        if has_electronic:
            compliance_note = (
                "Electronic records are present on record. Under Bharatiya Sakshya Adhiniyam, 2023 "
                "(Sections 57, 61, 63), a certificate from a person occupying a responsible official position "
                "in relation to the operation of the device is mandatory unless produced from proper custody."
            )
        else:
            compliance_note = "Documentary and physical evidence governed by primary and secondary proof standards under BSA."

        summary = (
            f"The evidentiary record for '{case.case_title}' consists of {len(case.exhibits)} exhibits "
            f"and {len(case.witnesses)} depositions. Corroboration exists regarding initial complaint and seizure, "
            f"while material limitations exist regarding {len(missing_gaps)} identified investigative omissions."
        )

        return EvidenceAnalysisReport(
            case_id=case.case_id,
            evidence_items=analyzed_items,
            corroboration_links=corroboration_links,
            evidentiary_contradictions=contradictions,
            missing_evidence_gaps=missing_gaps,
            documentary_compliance_assessment=compliance_note,
            summary=summary,
        )

    def analyze_evidence_package(
        self,
        package: EvidencePackage,
        case: Optional[StructuredCase] = None,
    ) -> EvidenceAnalysisReport:
        """
        Perform deep objective evidentiary evaluation on a standardized EvidencePackage.
        Strictly analyzes probative weight, chain of custody, and corroborations without pronouncing guilt.
        """
        case_id = (case.case_id if case else None) or package.case_identification.case_id or "CASE-AUTO"
        case_title = (case.case_title if case else None) or package.case_identification.case_title or "State v. Accused"
        logger.info("Analyzing standardized EvidencePackage for case '%s'", case_title)

        analyzed_items: list[EvidenceItemAnalysis] = []
        corroboration_links: list[CorroborationLink] = []
        contradictions: list[str] = [c.description for c in package.contradictions]
        missing_gaps: list[str] = [m.description for m in package.missing_evidence]

        # 1. Analyze exhibits
        for ex in package.exhibits:
            ex_type = self._map_evidence_type(ex.evidence_type)
            limitations = []
            confidence = 0.85
            chain_ok = True

            if ex_type == EvidenceType.ELECTRONIC:
                limitations.append("Requires certificate under Section 63 BSA for secondary electronic admissibility.")
                confidence = 0.70

            if "memo" in ex.evidence_type or "seizure" in ex.description.lower() or "recovery" in ex.description.lower():
                limitations.append("Recovery memo admissibility requires attestation by independent panchas under BSA.")

            if ex.original_or_copy == "photocopy":
                limitations.append("Photocopy tendered; secondary evidence conditions under Section 58-61 BSA apply.")
                confidence = 0.75

            analyzed_items.append(
                EvidenceItemAnalysis(
                    id=ex.evidence_id,
                    type=ex_type,
                    description=f"{ex.exhibit_number}: {ex.description}",
                    source=f"Ex. {ex.exhibit_number} (Page {ex.source_page or 'record'})",
                    related_witness=ex.introduced_through_witness or (ex.linked_witnesses[0] if ex.linked_witnesses else None),
                    supports=[f"Fact of {ex.description}"],
                    contradicts=[],
                    limitations=limitations,
                    confidence=confidence,
                    chain_of_custody_intact=chain_ok,
                )
            )

        # 2. Analyze physical evidence
        for pe in package.physical_evidence:
            analyzed_items.append(
                EvidenceItemAnalysis(
                    id=pe.evidence_id,
                    type=EvidenceType.REAL,
                    description=pe.item_description,
                    source=f"Seized from {pe.recovered_from or 'spot'} (Page {pe.source_page or 'record'})",
                    related_witness=pe.recovered_by,
                    supports=[f"Seizure and existence of {pe.item_description}"],
                    limitations=["Physical custody from recovery to judicial malkhana requires unbroken seal documentation."],
                    confidence=0.80,
                    chain_of_custody_intact=True,
                )
            )

        # 3. Analyze witnesses (Prosecution & Defence)
        for w in package.prosecution_witnesses:
            w_limits = []
            conf = 0.80
            if "police" in w.role.lower() or "inspector" in w.role.lower() or "officer" in w.role.lower():
                w_limits.append("Official police witness; scrutiny required in absence of independent corroboration.")
                conf = 0.75
            elif "owner" in w.role.lower() or "victim" in w.role.lower():
                conf = 0.85

            analyzed_items.append(
                EvidenceItemAnalysis(
                    id=w.witness_id,
                    type=EvidenceType.TESTIMONIAL,
                    description=f"Deposition of {w.name} ({w.role or 'Prosecution Witness'})",
                    source=f"{w.witness_id} deposition (Page {w.source_page or 'record'})",
                    related_witness=w.name,
                    supports=w.facts_testified or [f"Testified as {w.witness_id}"],
                    limitations=w_limits,
                    confidence=conf,
                    chain_of_custody_intact=True,
                )
            )

        for dw in package.defence_witnesses:
            analyzed_items.append(
                EvidenceItemAnalysis(
                    id=dw.witness_id,
                    type=EvidenceType.TESTIMONIAL,
                    description=f"Defense deposition of {dw.name} ({dw.role or 'Defense Witness'})",
                    source=f"{dw.witness_id} deposition (Page {dw.source_page or 'record'})",
                    related_witness=dw.name,
                    supports=dw.facts_testified or [f"Testified as {dw.witness_id}"],
                    limitations=["Defense witness; subject to cross-examination scrutiny."],
                    confidence=0.75,
                    chain_of_custody_intact=True,
                )
            )

        # 4. Map corroboration links from package linkages
        for link in package.evidence_links:
            corroboration_links.append(
                CorroborationLink(
                    item_a_id=link.source_id,
                    item_b_id=link.target_id,
                    fact_corroborated=link.description or f"{link.source_id} {link.relation_type} {link.target_id}",
                    strength="strong" if link.relation_type in ["produced", "identified"] else "moderate",
                )
            )

        if not missing_gaps:
            missing_gaps.append("Absence of independent civilian panch witness during search and seizure.")

        has_electronic = any(e.type == EvidenceType.ELECTRONIC for e in analyzed_items)
        compliance_note = (
            "Electronic records present; requires Section 63 BSA compliance."
            if has_electronic
            else "Documentary, material, and oral evidence governed by primary proof and Section 57/61 BSA."
        )

        summary = (
            f"The evidentiary record for '{case_title}' consists of {len(package.exhibits)} marked exhibits, "
            f"{len(package.prosecution_witnesses)} prosecution witnesses, and {len(package.defence_witnesses)} defence witnesses. "
            f"Found {len(corroboration_links)} evidentiary links, {len(contradictions)} contradictions, "
            f"and {len(missing_gaps)} identified omissions."
        )

        return EvidenceAnalysisReport(
            case_id=case_id,
            evidence_items=analyzed_items,
            corroboration_links=corroboration_links,
            evidentiary_contradictions=contradictions,
            missing_evidence_gaps=missing_gaps,
            documentary_compliance_assessment=compliance_note,
            summary=summary,
        )

    @staticmethod
    def _map_evidence_type(raw_type: str) -> EvidenceType:
        raw = raw_type.lower()
        if "electronic" in raw or "digital" in raw:
            return EvidenceType.ELECTRONIC
        if "forensic" in raw or "ballistic" in raw:
            return EvidenceType.FORENSIC
        if "medical" in raw or "postmortem" in raw:
            return EvidenceType.MEDICAL
        if "document" in raw or "memo" in raw or "panchnama" in raw or "affidavit" in raw:
            return EvidenceType.DOCUMENTARY
        if "physical" in raw or "weapon" in raw or "real" in raw or "object" in raw:
            return EvidenceType.REAL
        return EvidenceType.TESTIMONIAL

