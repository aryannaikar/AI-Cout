"""
Pydantic data models package for AI Court of India.
"""

from app.models.case_models import (
    Charge,
    Exhibit,
    Party,
    StructuredCase,
    WitnessStatement,
)
from app.models.conflict_models import (
    Conflict,
    ConflictCategory,
    ConflictReport,
    ConflictSeverity,
)
from app.models.evidence_models import (
    CorroborationLink,
    EvidenceAnalysisReport,
    EvidenceItemAnalysis,
    EvidenceType,
)
from app.models.judgment_models import (
    ArgumentComponent,
    DefenseCase,
    Judgment,
    JudicialIssueAnalysis,
    ProsecutionCase,
    StatementType,
)
from app.models.legal_models import (
    ApplicableProvision,
    LegalResearchResult,
    WebResearchItem,
    WebResearchResult,
)

from app.models.evidence_package_models import (
    CaseIdentification,
    ChargeAllegation,
    ClaimType,
    ContradictionRecord,
    EvidenceItem,
    EvidenceLink,
    EvidencePackage,
    IdentificationRecord,
    MissingEvidenceRecord,
    PhysicalEvidenceItem,
    ProceduralRecord,
    RecoveryRecord,
    SourceReference,
    StatementRecord,
    TestimonyClaim,
    Witness,
)

__all__ = [
    "Party",
    "Charge",
    "WitnessStatement",
    "Exhibit",
    "StructuredCase",
    "ApplicableProvision",
    "LegalResearchResult",
    "WebResearchItem",
    "WebResearchResult",
    "EvidenceType",
    "EvidenceItemAnalysis",
    "CorroborationLink",
    "EvidenceAnalysisReport",
    "ConflictCategory",
    "ConflictSeverity",
    "Conflict",
    "ConflictReport",
    "StatementType",
    "ArgumentComponent",
    "ProsecutionCase",
    "DefenseCase",
    "JudicialIssueAnalysis",
    "Judgment",
    "SourceReference",
    "CaseIdentification",
    "ChargeAllegation",
    "ClaimType",
    "Witness",
    "EvidenceItem",
    "PhysicalEvidenceItem",
    "RecoveryRecord",
    "IdentificationRecord",
    "TestimonyClaim",
    "StatementRecord",
    "ProceduralRecord",
    "EvidenceLink",
    "ContradictionRecord",
    "MissingEvidenceRecord",
    "EvidencePackage",
]

