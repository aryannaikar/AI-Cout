"""
Pydantic data models for Prosecution Arguments, Defense Arguments, and the 12-section Judicial Verdict.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StatementType(str, Enum):
    """Rigorous epistemic classification required of all courtroom arguments."""

    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    LEGAL_RULE = "LEGAL_RULE"
    INFERENCE = "INFERENCE"
    ARGUMENT = "ARGUMENT"


class ArgumentComponent(BaseModel):
    """An individual constituent proposition of a legal submission."""

    statement_type: StatementType = Field(
        description="Epistemic nature: FACT, EVIDENCE, LEGAL_RULE, INFERENCE, or ARGUMENT."
    )
    content: str = Field(description="The proposition or assertion.")
    source_reference: Optional[str] = Field(
        default=None,
        description="Grounded citation or evidentiary source (e.g. 'PW-1 at Page 12', 'BNS Section 317(2)', 'Ex. P-4').",
    )


class ProsecutionCase(BaseModel):
    """Complete adversarial case submitted by the Prosecutor Agent."""

    case_id: str = Field(description="Case identifier.")
    prosecution_theory: str = Field(description="Central narrative and theory of guilt.")
    statutory_elements: list[str] = Field(
        default_factory=list,
        description="Elements of offences that must be established beyond reasonable doubt.",
    )
    argument_components: list[ArgumentComponent] = Field(
        default_factory=list,
        description="Structured arguments explicitly categorized by statement type.",
    )
    supporting_witnesses: list[str] = Field(
        default_factory=list,
        description="Witnesses establishing the chain of events.",
    )
    supporting_exhibits: list[str] = Field(
        default_factory=list,
        description="Physical and digital exhibits corroborating charges.",
    )
    addressed_weaknesses: list[str] = Field(
        default_factory=list,
        description="Proactive explanation or mitigation of evidentiary infirmities in the case packet.",
    )
    legal_citations: list[str] = Field(
        default_factory=list,
        description="Statutory citations retrieved via Phase 1 Legal RAG.",
    )
    final_prayer: str = Field(description="Formal request for conviction and statutory sentencing.")


class DefenseCase(BaseModel):
    """Complete adversarial defense submitted by the Defense Agent."""

    case_id: str = Field(description="Case identifier.")
    defense_theory: str = Field(description="Central theory of defense (e.g. false implication, alibi, lack of mens rea).")
    argument_components: list[ArgumentComponent] = Field(
        default_factory=list,
        description="Structured arguments explicitly categorized by statement type.",
    )
    reasonable_doubt_grounds: list[str] = Field(
        default_factory=list,
        description="Specific material doubts raised by the record (e.g. contradiction between medical and ocular testimony).",
    )
    witness_inconsistencies_highlighted: list[str] = Field(
        default_factory=list,
        description="Witness contradictions undermining prosecution credibility.",
    )
    missing_evidence_highlighted: list[str] = Field(
        default_factory=list,
        description="Investigative omissions creating reasonable doubt.",
    )
    alternative_interpretation: str = Field(
        description="Plausible exculpatory interpretation of the facts supported by the evidence.",
    )
    legal_citations: list[str] = Field(
        default_factory=list,
        description="Statutory citations retrieved via Phase 1 Legal RAG supporting the defense.",
    )
    final_prayer: str = Field(description="Formal request for complete acquittal and discharge.")


class JudicialIssueAnalysis(BaseModel):
    """Independent analysis by the Judge of a specific issue in controversy."""

    issue_number: int = Field(description="Issue number (e.g. 1, 2, 3).")
    issue_statement: str = Field(description="Formal question of law or fact framed for decision.")
    applicable_law: str = Field(description="Statutory section and standard of proof governing this issue.")
    prosecution_submission_summary: str = Field(description="Summary of prosecution's argument on this issue.")
    defense_submission_summary: str = Field(description="Summary of defense's argument on this issue.")
    evidentiary_evaluation: str = Field(description="Independent judicial appreciation of oral and documentary evidence.")
    judicial_finding: str = Field(description="Finding: 'PROVED', 'NOT PROVED', or 'DISPROVED'.")


class Judgment(BaseModel):
    """
    Formal, exhaustive judicial verdict rendered by the Judge Agent.
    Strictly follows the 12-section judicial reasoning framework.
    """

    judgment_id: str = Field(default="JUDG-001", description="Judgment identifier.")
    case_title: str = Field(description="Formal case title.")
    presiding_court: str = Field(default="Court of Sessions / AI Court of India", description="Court name.")
    date_of_decision: str = Field(description="Date of verdict.")

    # 1. Case background
    case_background: str = Field(description="Section 1: Factual background, FIR narrative, and prosecution origin.")

    # 2. Issues for determination
    issues_for_determination: list[str] = Field(
        description="Section 2: Points for determination formulated by the court."
    )

    # 3. Applicable law
    applicable_law: list[str] = Field(
        description="Section 3: Governing provisions of BNS, BSA, IT Act, and the Constitution."
    )

    # 4. Evidence assessment
    evidence_assessment: str = Field(
        description="Section 4: Judicial assessment of exhibits, electronic records, and chain of custody."
    )

    # 5. Witness assessment
    witness_assessment: str = Field(
        description="Section 5: Credibility analysis of prosecution and defense witnesses."
    )

    # 6. Prosecution submissions
    prosecution_submissions: str = Field(
        description="Section 6: Summary of submissions made on behalf of the State."
    )

    # 7. Defense submissions
    defense_submissions: str = Field(
        description="Section 7: Summary of submissions made on behalf of the accused."
    )

    # 8. Analysis of each issue
    issue_analyses: list[JudicialIssueAnalysis] = Field(
        description="Section 8: Systematic analysis and determination of each issue framed."
    )

    # 9. Findings
    findings_per_charge: dict[str, str] = Field(
        description="Section 9: Specific finding per charge (e.g. {'Section 303 BNS': 'Guilty', 'Section 66 IT Act': 'Acquitted'})."
    )

    # 10. Final decision
    final_decision: str = Field(
        description="Section 10: Formal operative verdict ('CONVICTION', 'ACQUITTAL', or 'PARTIAL CONVICTION')."
    )

    # 11. Reasons
    reasons: str = Field(
        description="Section 11: Ratio decidendi and detailed reasoning justifying the decision."
    )

    # 12. Legal citations
    legal_citations: list[str] = Field(
        description="Section 12: Grounded statutory citations supporting the judgment."
    )
