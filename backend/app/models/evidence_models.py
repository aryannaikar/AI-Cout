"""
Pydantic data models for Evidence Analysis in AI Court of India.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    DIRECT = "direct_oral"
    CIRCUMSTANTIAL = "circumstantial"
    DOCUMENTARY = "documentary"
    ELECTRONIC = "electronic_record"
    FORENSIC = "forensic_ballistic_or_chemical"
    MEDICAL = "medical_or_postmortem"
    TESTIMONIAL = "witness_testimony"
    REAL = "physical_or_material_object"


class EvidenceItemAnalysis(BaseModel):
    """Deep analytical evaluation of an individual piece of evidence."""

    id: str = Field(description="Evidence identifier (e.g. 'EV-01', 'Ex. P-1', 'MO-1').")
    type: EvidenceType = Field(description="Statutory category of evidence under BSA.")
    description: str = Field(description="Description of the item or testimony.")
    source: str = Field(description="Originating source (e.g. 'PW-1 statement', 'Recovery panchnama', 'Server log').")
    related_witness: Optional[str] = Field(default=None, description="Key witness introducing or proving this evidence.")
    supports: list[str] = Field(
        default_factory=list,
        description="Factual propositions or allegations corroborated by this evidence.",
    )
    contradicts: list[str] = Field(
        default_factory=list,
        description="Factual assertions or witness accounts directly contradicted by this evidence.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Evidentiary infirmities (e.g. lack of Section 63 BSA certificate, delay in FIR, hostile attesting witness).",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Analytical confidence in the probative value and authenticity of this evidence (0.0 to 1.0).",
    )
    chain_of_custody_intact: bool = Field(
        default=True,
        description="Whether custody from seizure to laboratory/court was unbroken.",
    )
    document_reference: Optional[str] = Field(default=None, description="Originating document reference.")
    page_reference: Optional[int] = Field(default=None, description="Source page number if available.")
    associated_proceeding: Optional[str] = Field(default=None, description="Proceeding identifier if applicable.")
    associated_accused: list[str] = Field(default_factory=list, description="Specific accused persons linked to this item.")
    associated_charge: Optional[str] = Field(default=None, description="Specific charge linked to this item.")
    proof_nature: Literal["direct", "circumstantial", "uncertain"] = Field(
        default="uncertain", description="Whether evidence is direct, circumstantial, or uncertain."
    )
    record_role: Literal["allegation", "statement", "documentary_record", "physical_exhibit", "expert_opinion"] = Field(
        default="documentary_record", description="Epistemic role in the record."
    )
    verification_status: Literal["verified_on_record", "disputed", "unverified", "missing_link"] = Field(
        default="unverified", description="Verification status in the trial record."
    )


class CorroborationLink(BaseModel):
    """Represents mutual corroboration between two pieces of evidence or testimonies."""

    item_a_id: str = Field(description="Identifier of first evidence item.")
    item_b_id: str = Field(description="Identifier of second evidence item.")
    fact_corroborated: str = Field(description="The specific material fact established by their combination.")
    strength: str = Field(default="moderate", description="'strong', 'moderate', or 'circumstantial'.")


class CanonicalWitnessRecord(BaseModel):
    """Canonical deduplicated witness record preserving distinct identities."""

    witness_id: str
    witness_name: str
    side: Literal["prosecution", "defense", "court", "unknown"] = "unknown"
    role: str = ""
    statement_references: list[str] = Field(default_factory=list)
    related_exhibits: list[str] = Field(default_factory=list)
    accused_involved: list[str] = Field(default_factory=list)
    material_assertions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)


class CanonicalExhibitRecord(BaseModel):
    """Canonical exhibit record distinguishing formally marked exhibits from narrative mentions."""

    exhibit_id: str
    exhibit_marking: str
    is_formally_marked: bool = True
    description: str
    document_type: str
    introducing_witness: Optional[str] = None
    associated_accused: list[str] = Field(default_factory=list)
    associated_proceeding: Optional[str] = None
    source_reference: str = ""
    chain_of_custody_notes: list[str] = Field(default_factory=list)
    verification_status: Literal["formally_marked", "narrative_mention_only", "disputed", "missing"] = "formally_marked"


class TimelineEvent(BaseModel):
    """Single chronological event in the case timeline."""

    event_id: str
    stage: Literal["incident", "investigation", "recovery_seizure", "arrest", "medical_forensic", "trial_procedural"]
    date_text: Optional[str] = None
    time_text: Optional[str] = None
    location: Optional[str] = None
    description: str
    accused_involved: list[str] = Field(default_factory=list)
    witness_involved: list[str] = Field(default_factory=list)
    related_exhibit: Optional[str] = None
    source_reference: str = ""
    has_date_conflict: bool = False
    conflicting_dates: list[str] = Field(default_factory=list)


class EvidenceTimeline(BaseModel):
    """Chronological timeline of case events, preserving conflicting dates without guessing."""

    events: list[TimelineEvent] = Field(default_factory=list)
    date_conflicts_detected: list[str] = Field(default_factory=list)


class AccusedEvidenceMapping(BaseModel):
    """Strict accused-wise evidence attribution; never leaks co-accused recovery to another accused."""

    accused_name: str
    proceeding_id: Optional[str] = None
    allegations: list[str] = Field(default_factory=list)
    direct_evidence: list[str] = Field(default_factory=list)
    circumstantial_evidence: list[str] = Field(default_factory=list)
    witness_testimony: list[str] = Field(default_factory=list)
    documentary_evidence: list[str] = Field(default_factory=list)
    physical_exhibits: list[str] = Field(default_factory=list)
    recovery_evidence: list[str] = Field(default_factory=list)
    expert_evidence: list[str] = Field(default_factory=list)
    exculpatory_or_defense_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    related_charges: list[str] = Field(default_factory=list)


class ContradictionEntry(BaseModel):
    """Structured contradiction entry distinguishing materiality and resolution status."""

    contradiction_id: str
    issue: str
    source_a: str
    source_b: str
    conflicting_content: str
    related_witness_or_accused: list[str] = Field(default_factory=list)
    related_charge: Optional[str] = None
    materiality: Literal["material_contradiction", "minor_inconsistency", "clarified_discrepancy", "missing_information"] = "material_contradiction"
    resolution_status: Literal["resolved", "unresolved", "uncertain"] = "unresolved"


class ContradictionMatrix(BaseModel):
    """Structured contradiction matrix across testimonies, exhibits, and investigation records."""

    entries: list[ContradictionEntry] = Field(default_factory=list)
    material_count: int = 0
    minor_count: int = 0


class RecoveryChainAnalysis(BaseModel):
    """Analysis of recovery and chain of custody without assuming recovery proves guilt."""

    recovery_id: str
    item_description: str
    recovered_by: Optional[str] = None
    recovered_from: Optional[str] = None
    date_and_location: Optional[str] = None
    seizure_documentation: Optional[str] = None
    witnesses_present: list[str] = Field(default_factory=list)
    identification_notes: Optional[str] = None
    exhibit_marking: Optional[str] = None
    custody_transfers: list[str] = Field(default_factory=list)
    forensic_examination: Optional[str] = None
    missing_links: list[str] = Field(default_factory=list)


class MedicalForensicComparison(BaseModel):
    """Medical/forensic comparison gated strictly on presence of source records."""

    status: Literal["available", "not_available"] = "not_available"
    source_records: list[str] = Field(default_factory=list)
    comparisons: list[str] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    notes: str = "No medical, post-mortem, or forensic report present in the supplied record."


class EvidenceAnalysisReport(BaseModel):
    """Complete analytical report generated by the Evidence Analysis Agent."""

    case_id: str = Field(description="Case identifier.")
    evidence_items: list[EvidenceItemAnalysis] = Field(
        default_factory=list,
        description="All analyzed evidentiary items.",
    )
    corroboration_links: list[CorroborationLink] = Field(
        default_factory=list,
        description="Corroborative connections identified across the record.",
    )
    evidentiary_contradictions: list[str] = Field(
        default_factory=list,
        description="Internal contradictions discovered among exhibits and testimonies.",
    )
    missing_evidence_gaps: list[str] = Field(
        default_factory=list,
        description="Crucial investigative omissions (e.g. failure to seize weapon, no call detail records, absence of independent panch).",
    )
    documentary_compliance_assessment: str = Field(
        description="Assessment of admissibility under the Bharatiya Sakshya Adhiniyam, 2023 (including Sections 57, 61, 63).",
    )
    summary: str = Field(
        description="Objective evidentiary summary. Strictly descriptive; does not pronounce guilt or innocence.",
    )
    canonical_witnesses: list[CanonicalWitnessRecord] = Field(default_factory=list)
    canonical_exhibits: list[CanonicalExhibitRecord] = Field(default_factory=list)
    timeline: Optional[EvidenceTimeline] = Field(default=None)
    accused_mappings: list[AccusedEvidenceMapping] = Field(default_factory=list)
    contradiction_matrix: Optional[ContradictionMatrix] = Field(default=None)
    recovery_analyses: list[RecoveryChainAnalysis] = Field(default_factory=list)
    medical_forensic_comparison: MedicalForensicComparison = Field(default_factory=MedicalForensicComparison)
