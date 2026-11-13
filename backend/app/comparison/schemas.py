"""
Pydantic data models for Phase 5 — AI Court Judgment Comparison Engine.
Defines normalized judgment representation, error detection schemas,
individual comparison dimensions, and the complete 17-section comparison report.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class EpistemicType(str, Enum):
    """Rigorous categorization of assertions into distinct epistemic levels."""
    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    CLAIM = "CLAIM"
    INFERENCE = "INFERENCE"
    LEGAL_CONCLUSION = "LEGAL_CONCLUSION"


class StatuteEra(str, Enum):
    """Distinguishes between historical and modern Indian criminal codifications."""
    HISTORICAL_IPC_CRPC = "HISTORICAL_IPC_CRPC"
    MODERN_BNS_BNSS_BSA = "MODERN_BNS_BNSS_BSA"
    SPECIAL_ACT = "SPECIAL_ACT"
    OTHER = "OTHER"


class OperativeVerdict(str, Enum):
    """Standardized classification of operative judicial verdicts."""
    CONVICTION = "CONVICTION"
    ACQUITTAL = "ACQUITTAL"
    APPEAL_ALLOWED = "APPEAL_ALLOWED"
    APPEAL_DISMISSED = "APPEAL_DISMISSED"
    PARTIAL_CONVICTION = "PARTIAL_CONVICTION"
    DISCHARGE = "DISCHARGE"
    REMAND = "REMAND"
    SENTENCE_MODIFIED = "SENTENCE_MODIFIED"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"


class ComparisonCategoryStatus(str, Enum):
    """Standardized statuses for individual comparison categories."""
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    MISSING_IN_AI = "MISSING_IN_AI"
    UNSUPPORTED_BY_SOURCE = "UNSUPPORTED_BY_SOURCE"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


AlignmentStatus = Literal["aligned", "partially_aligned", "not_aligned"]
ErrorSeverity = Literal["low", "medium", "high", "critical"]


class NormalizedParty(BaseModel):
    """Case parties identification."""
    appellant_or_accused: str = Field(default="Accused / Appellant", description="Accused or Appellant name(s)")
    respondent_or_state: str = Field(default="State", description="Prosecution or Respondent State entity")


class NormalizedWitness(BaseModel):
    """Witness deposition and credibility profile."""
    witness_id: str = Field(description="Designation (e.g., 'PW-1', 'DW-1')")
    name: str = Field(default="", description="Name of the witness")
    designation: str = Field(default="", description="Role (e.g. 'Investigating Officer', 'Eye-witness', 'Panch')")
    testimony_summary: str = Field(default="", description="Substance of deposition")
    credibility_finding: Optional[str] = Field(default=None, description="Court's credibility assessment")


class NormalizedEvidenceItem(BaseModel):
    """Exhibits and evidentiary articles considered by the court."""
    exhibit_id: str = Field(description="Exhibit identifier (e.g., 'Ex. P-1', 'Ex. PW-2/A')")
    description: str = Field(description="Description of the evidence item")
    evidence_type: str = Field(
        default="DOCUMENTARY",
        description="DOCUMENTARY, PHYSICAL, RECOVERY, IDENTIFICATION, ELECTRONIC, PROCEDURAL, OTHER",
    )
    admitted_or_proved: Optional[bool] = Field(default=None, description="Whether marked proved or admitted")
    judicial_assessment: Optional[str] = Field(default=None, description="Assessment of evidentiary value")


class NormalizedCharge(BaseModel):
    """Alleged offence and statutory provisions."""
    statute: str = Field(description="Statute and section (e.g. 'IPC Section 411', 'BNS Section 317')")
    era: StatuteEra = Field(default=StatuteEra.OTHER, description="Code era (Historical vs Modern)")
    offence: str = Field(default="", description="Name or description of offence")
    finding: Optional[str] = Field(default=None, description="Finding on this charge")
    accused_name: Optional[str] = Field(default=None, description="Specific accused person this charge applied to")
    procedural_stage: Optional[str] = Field(default=None, description="trial_charge, conviction, appellate_subject")


class NormalizedFact(BaseModel):
    """Material fact evaluated in the judgment."""
    statement: str = Field(description="Statement of fact")
    epistemic_type: EpistemicType = Field(default=EpistemicType.FACT, description="Epistemic nature")
    is_material: bool = Field(default=True, description="Whether this is a material fact")
    source: Optional[str] = Field(default=None, description="Source or reference")


class NormalizedIssue(BaseModel):
    """Point or question framed for judicial determination."""
    issue_id: str = Field(description="Issue number or identifier")
    statement: str = Field(description="Formal question of law or fact framed for decision")
    applicable_law: Optional[str] = Field(default=None, description="Governing statutory provision")
    finding: Optional[str] = Field(default=None, description="Judicial finding (e.g. 'PROVED', 'NOT PROVED')")
    reasoning_summary: Optional[str] = Field(default=None, description="Core judicial reasoning on this issue")


class NormalizedReasoning(BaseModel):
    """Detailed structure of judicial ratio decidendi and chains of reasoning."""
    ratio_decidendi: str = Field(default="", description="Central legal and factual reasoning justifying verdict")
    key_chains: List[str] = Field(default_factory=list, description="Step-by-step chains of logical inference")
    evaluated_credibility: bool = Field(default=False, description="Whether witness credibility was evaluated")
    evaluated_contradictions: bool = Field(default=False, description="Whether contradictions were analyzed")
    evaluated_missing_evidence: bool = Field(default=False, description="Whether investigative gaps were noted")
    connected_evidence_to_findings: bool = Field(default=False, description="Whether evidence connected to findings")


class NormalizedJudgment(BaseModel):
    """
    Common normalized intermediate representation capturing all 18 required elements:
    1. Case identification
    2. Parties
    3. Charges / allegations
    4. Material facts
    5. Legal issues
    6. Prosecution witnesses
    7. Defence witnesses
    8. Documentary evidence
    9. Physical/material evidence
    10. Recovery evidence
    11. Identification evidence
    12. Legal provisions
    13. Prosecution arguments
    14. Defence arguments
    15. Findings
    16. Legal reasoning
    17. Verdict
    18. Final order
    """
    case_title: str = Field(description="Formal case caption")
    case_number: Optional[str] = Field(default=None, description="Court case number / Sessions number")
    presiding_court: Optional[str] = Field(default=None, description="Name of the court")
    date_of_decision: Optional[str] = Field(default=None, description="Date of decision")
    verdict: OperativeVerdict = Field(description="Standardized operative verdict")
    verdict_raw: str = Field(default="", description="Original raw verdict text")
    verdict_normalization_explanation: Optional[str] = Field(default=None, description="Explanation of how verdict was extracted and normalized")
    final_order: str = Field(default="", description="Operative order, sentences, discharge, disposal")
    parties: NormalizedParty = Field(default_factory=NormalizedParty, description="Parties to the case")
    charges: List[NormalizedCharge] = Field(default_factory=list, description="Statutory charges")
    material_facts: List[NormalizedFact] = Field(default_factory=list, description="Material facts")
    legal_issues: List[NormalizedIssue] = Field(default_factory=list, description="Points for determination")
    prosecution_witnesses: List[NormalizedWitness] = Field(default_factory=list, description="Prosecution witnesses")
    defence_witnesses: List[NormalizedWitness] = Field(default_factory=list, description="Defence witnesses")
    evidence_items: List[NormalizedEvidenceItem] = Field(default_factory=list, description="Exhibits and evidence")
    legal_provisions: List[str] = Field(default_factory=list, description="Statutory provisions and doctrines")
    prosecution_arguments: List[str] = Field(default_factory=list, description="Prosecution submissions")
    defence_arguments: List[str] = Field(default_factory=list, description="Defence submissions")
    findings: Dict[str, str] = Field(default_factory=dict, description="Findings per charge or per issue")
    reasoning: NormalizedReasoning = Field(default_factory=NormalizedReasoning, description="Ratio decidendi & reasoning")
    raw_text: Optional[str] = Field(default=None, description="Original raw judgment text")
    is_ground_truth_summary: bool = Field(default=False, description="Whether judgment is an evaluation summary rather than full transcript")
    extraction_warnings: List[str] = Field(default_factory=list, description="Warnings encountered during extraction")
    extraction_errors: List[str] = Field(default_factory=list, description="Critical extraction failures")


class ComparisonErrorDetail(BaseModel):
    """
    Specific detected discrepancy or hallucination in the AI judgment.
    Includes severity, claims, and authoritative reference.
    """
    type: str = Field(description="Error category: hallucinated_fact, unrelated_issue, wrong_legal_provision, etc.")
    severity: ErrorSeverity = Field(description="low | medium | high | critical")
    ai_claim: str = Field(description="Claim or determination made by AI Court")
    real_court_position: str = Field(description="Authoritative position of Real Court (never invented)")
    explanation: str = Field(description="Detailed explanation of error and legal significance")


class VerdictComparisonResult(BaseModel):
    """Evaluation of operative outcome alignment."""
    ai_verdict: str
    real_verdict: str
    alignment: AlignmentStatus
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)
    verdict_normalization_explanation: Optional[str] = Field(default=None, description="Explanation of how verdict was extracted and normalized")


class IssueComparisonResult(BaseModel):
    """Evaluation of issues framed and addressed."""
    matched_issues: List[Dict[str, Any]] = Field(default_factory=list)
    ai_missed_issues: List[str] = Field(default_factory=list)
    ai_unrelated_issues: List[str] = Field(default_factory=list)
    materially_incorrect_issues: List[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class FactualComparisonResult(BaseModel):
    """Evaluation of factual accuracy and epistemic classification."""
    correct_facts: List[str] = Field(default_factory=list)
    incorrect_facts: List[str] = Field(default_factory=list)
    unsupported_facts: List[str] = Field(default_factory=list)
    invented_facts: List[str] = Field(default_factory=list)
    omitted_material_facts: List[str] = Field(default_factory=list)
    epistemic_distinctions: List[Dict[str, str]] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    correctness_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Precision: verified facts vs invented/unsupported")
    completeness_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Recall: covered authoritative material facts")
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class ChargeComparisonResult(BaseModel):
    """Evaluation of statutory charge alignment and historical applicability."""
    matched_charges: List[Dict[str, Any]] = Field(default_factory=list)
    missing_charges: List[str] = Field(default_factory=list)
    incorrectly_introduced_charges: List[str] = Field(default_factory=list)
    historical_law_mismatches: List[str] = Field(default_factory=list)
    procedural_or_coaccused_charges: List[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class WitnessComparisonResult(BaseModel):
    """Evaluation of witness appreciation and substance of testimony."""
    witness_count_ai: int = 0
    witness_count_real: int = 0
    correctly_analyzed_witnesses: List[str] = Field(default_factory=list)
    misattributed_testimony: List[str] = Field(default_factory=list)
    omitted_key_witnesses: List[str] = Field(default_factory=list)
    substantive_testimony_alignment: str = ""
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class EvidenceComparisonResult(BaseModel):
    """Evaluation of documentary, physical, and recovery evidence."""
    correctly_considered: List[str] = Field(default_factory=list)
    ignored_evidence: List[str] = Field(default_factory=list)
    misattributed_evidence: List[str] = Field(default_factory=list)
    invented_evidence: List[str] = Field(default_factory=list)
    improperly_proved_evidence: List[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class LegalProvisionComparisonResult(BaseModel):
    """Evaluation of statutory provisions, Acts, and rules cited."""
    correct_provisions: List[str] = Field(default_factory=list)
    missing_provisions: List[str] = Field(default_factory=list)
    incorrectly_cited_provisions: List[str] = Field(default_factory=list)
    historically_inapplicable_provisions: List[str] = Field(default_factory=list)
    procedural_or_coaccused_provisions: List[str] = Field(default_factory=list)
    unconnected_provisions: List[str] = Field(default_factory=list)
    matched_count: int = 0
    missing_count: int = 0
    incorrect_count: int = 0
    inapplicable_count: int = 0
    procedural_count: int = 0
    unconnected_count: int = 0
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class ReasoningThemeComparison(BaseModel):
    """Evaluation of an individual judicial reasoning theme."""
    theme_id: str = Field(description="Unique identifier for the judicial theme")
    theme_name: str = Field(description="Title of the judicial theme")
    real_court_position: str = Field(description="Real Supreme Court ratio on this theme")
    ai_position: str = Field(description="AI judgment position or holding on this theme")
    match_status: str = Field(description="MATCH | PARTIAL_MATCH | MISMATCH")
    source_evidence: str = Field(default="", description="Citation or evidentiary basis for this theme")


class LegalReasoningComparisonResult(BaseModel):
    """Evaluation of ratio decidendi and chains of logical inference."""
    addressed_actual_legal_issue: bool = False
    considered_relevant_evidence: bool = False
    applied_correct_law: bool = False
    evaluated_credibility_correctly: bool = False
    considered_contradictions: bool = False
    considered_missing_evidence: bool = False
    connected_evidence_to_findings: bool = False
    logically_valid_chain_of_reasoning: bool = False
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)
    matched_themes_count: int = Field(default=0)
    total_real_themes_count: int = Field(default=0)
    theme_evaluations: List[ReasoningThemeComparison] = Field(
        default_factory=list, description="Individual judicial theme evaluations"
    )


class FindingComparisonResult(BaseModel):
    """Evaluation of findings on each charge and major issue."""
    issue_findings: List[Dict[str, Any]] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class FinalOrderComparisonResult(BaseModel):
    """Evaluation of final operative order independently from reasoning."""
    ai_final_order: str
    real_final_order: str
    alignment: AlignmentStatus
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    ai_extracted_position: Optional[str] = Field(default=None)
    real_extracted_position: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_assessable: bool = Field(default=True)


class ComparisonScores(BaseModel):
    """Comprehensive score breakdown and weighted overall calculation."""
    verdict_alignment: float = Field(ge=0.0, le=100.0)
    issue_alignment: float = Field(ge=0.0, le=100.0)
    factual_accuracy: float = Field(ge=0.0, le=100.0)
    charge_alignment: float = Field(ge=0.0, le=100.0)
    witness_alignment: float = Field(ge=0.0, le=100.0)
    evidence_alignment: float = Field(ge=0.0, le=100.0)
    legal_alignment: float = Field(ge=0.0, le=100.0)
    reasoning_alignment: float = Field(ge=0.0, le=100.0)
    finding_alignment: float = Field(ge=0.0, le=100.0)
    final_order_alignment: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)
    weights: Dict[str, float] = Field(default_factory=dict)
    substantive_score: Optional[float] = Field(default=None, description="Score of substantive categories excluding verdict")
    verdict_score: Optional[float] = Field(default=None, description="Operative verdict alignment score")
    active_weights: Dict[str, float] = Field(default_factory=dict, description="Normalized weights after excluding unassessable categories")
    excluded_categories: List[str] = Field(default_factory=list, description="Categories excluded from weighted denominator")
    scoring_formula: Optional[str] = Field(default=None, description="Documented formula used for score calculation")


class ComparisonReport(BaseModel):
    """
    Formal structured 17-section report comparing AI Court Judgment vs Real Court Judgment.
    """
    comparison_id: str = Field(description="Unique comparison identifier")
    case_id: Optional[str] = Field(default=None, description="Case identifier")
    case_title: str = Field(description="Case title")
    mode: Literal["post_trial", "manual"] = Field(description="post_trial or manual")
    timestamp: str = Field(description="ISO timestamp of comparison")

    # 1. Case Information
    case_information: Dict[str, Any] = Field(default_factory=dict)

    # 2. Overall Assessment
    overall_assessment: str = Field(description="Executive summary of alignment and divergence")

    # 3. Verdict Comparison
    verdict_comparison: VerdictComparisonResult

    # 4. Issue Comparison
    issue_comparison: IssueComparisonResult

    # 5. Factual Comparison
    factual_comparison: FactualComparisonResult

    # 6. Charge Comparison
    charge_comparison: ChargeComparisonResult

    # 7. Witness Comparison
    witness_comparison: WitnessComparisonResult

    # 8. Evidence Comparison
    evidence_comparison: EvidenceComparisonResult

    # 9. Legal Provision Comparison
    legal_provision_comparison: LegalProvisionComparisonResult

    # 10. Legal Reasoning Comparison
    reasoning_comparison: LegalReasoningComparisonResult

    # 11. Finding Comparison
    finding_comparison: FindingComparisonResult

    # 12. Final Order Comparison
    final_order_comparison: FinalOrderComparisonResult

    # 13. Major Errors
    major_errors: List[ComparisonErrorDetail] = Field(default_factory=list)

    # 14. Missing Important Points
    missing_important_points: List[str] = Field(default_factory=list)

    # 15. Unrelated / Hallucinated Points
    unrelated_hallucinated_points: List[str] = Field(default_factory=list)

    # 16. Scores
    scores: ComparisonScores

    # 17. Overall Conclusion
    overall_conclusion: str = Field(description="Formal ratio and benchmark verdict conclusion")
