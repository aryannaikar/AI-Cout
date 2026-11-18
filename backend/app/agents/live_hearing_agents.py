"""
Live Hearing Agents for AI Court of India.
Powers the true conversational courtroom debate between Judge, Prosecutor, Defense,
and impartial support agents (Evidence and Conflict Analysis).

Debate Flow per Issue:
Judge (introduces issue)
  -> Prosecutor (1st affirmative argument)
  -> Defense (directly challenges argument)
  -> Prosecutor (responds to Defense's challenge)
  -> Defense (counters Prosecutor's response)
  -> Judge (intervenes / clarifies / introduces next issue)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import DefenseCase, ProsecutionCase
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class JudgeAction(BaseModel):
    message: str = Field(description="What the Judge says out loud in the courtroom (1-2 sentences max).")
    next_speaker: str = Field(
        default="prosecutor",
        description="Who speaks next: 'prosecutor', 'defense', 'evidence', 'conflict', or 'end_hearing'."
    )
    active_issue: Optional[str] = Field(
        default=None,
        description="The current specific issue being debated."
    )
    turn_in_issue: int = Field(
        default=1,
        description="Turn counter within current issue."
    )
    issue_index: int = Field(
        default=0,
        description="Index of the active issue in the issue list."
    )
    concluded_issues: List[str] = Field(
        default_factory=list,
        description="List of issues concluded so far."
    )


class LawyerAction(BaseModel):
    message: str = Field(default="", description="What you say in the courtroom (1-3 sentences max).")
    next_speaker: Optional[str] = Field(
        default=None,
        description="Next speaker in courtroom debate: 'defense', 'prosecutor', or 'judge'."
    )
    unresolved_argument: Optional[str] = Field(
        default=None,
        description="The point of contention requiring reply."
    )


def extract_grounded_case_context(
    case: Optional[StructuredCase],
    prosecution: Optional[ProsecutionCase] = None,
    defense: Optional[DefenseCase] = None,
) -> Dict[str, Any]:
    """Extracts factual matrix and strict evidentiary bounds directly from case materials."""
    raw_title = (case.case_title or "").strip() if case else ""
    if raw_title:
        case_title = raw_title
    elif case and case.accused:
        case_title = f"{case.accused[0]} & Ors. v. State" if len(case.accused) > 1 else f"{case.accused[0]} v. State"
    elif case and (case.court_identifier or "").strip():
        case_title = case.court_identifier.strip()
    else:
        case_title = "Present Criminal Proceeding"

    court_id = (
        case.court_identifier.strip()
        if case and (case.court_identifier or "").strip()
        else "Trial / Appellate Proceeding on Record"
    )
    accused = ", ".join(case.accused) if case and case.accused else "Accused / Petitioner(s)"

    allegations = (
        case.allegations_summary
        if case and case.allegations_summary
        else "Allegations as set forth in the supplied case packet."
    )

    witnesses = []
    if case and case.witnesses:
        for w in case.witnesses:
            witnesses.append(f"{w.witness_id} ({w.witness_name}): {w.testimony_summary or 'Deposed on case facts'}")
    else:
        witnesses = ["No witnesses extracted from case packet."]

    exhibits = []
    if case and case.exhibits:
        for e in case.exhibits:
            exhibits.append(f"{e.exhibit_id}: {e.title}")
    else:
        exhibits = ["No exhibits extracted from case packet."]

    charges = []
    if case and case.charges:
        active_charges = (
            case.current_charges()
            if hasattr(case, "current_charges")
            else [c for c in case.charges if c.record_status == "current"]
        )
        for c in (active_charges or case.charges):
            charges.append(f"{c.statute} {c.section} ({c.description}) [accused: {c.accused_name}]")
    else:
        charges = ["No specific statutory charges extracted from case packet."]

    prepared_arguments = []
    if prosecution:
        prepared_arguments.append(f"Prosecution Theory: {prosecution.prosecution_theory}")
        for arg in prosecution.argument_components:
            prepared_arguments.append(f"- {arg.content}")
        if prosecution.addressed_weaknesses:
            for w in prosecution.addressed_weaknesses:
                prepared_arguments.append(f"- Weakness Mitigated: {w}")
    if defense:
        prepared_arguments.append(f"Defense Theory: {defense.defense_theory}")
        for arg in defense.argument_components:
            prepared_arguments.append(f"- {arg.content}")
        if defense.reasonable_doubt_grounds:
            for r in defense.reasonable_doubt_grounds:
                prepared_arguments.append(f"- Reasonable Doubt Ground: {r}")

    return {
        "title": case_title,
        "court_id": court_id,
        "accused": accused,
        "allegations": allegations,
        "witnesses": witnesses,
        "exhibits": exhibits,
        "charges": charges,
        "prepared_arguments": prepared_arguments,
    }


def get_case_issues(case: Optional[StructuredCase]) -> List[str]:
    """Returns clean, case-grounded issues, strictly filtering out ungrounded electronic records."""
    if case and case.legal_issues:
        filtered = [
            iss for iss in case.legal_issues
            if "63 bsa" not in iss.lower() and "electronic" not in iss.lower() and "newborn" not in iss.lower()
        ]
        if filtered:
            return filtered

    if case and case.charges:
        active_charges = (
            case.current_charges()
            if hasattr(case, "current_charges")
            else [c for c in case.charges if c.record_status == "current"]
        )
        issues = []
        for ch in (active_charges or case.charges)[:2]:
            issues.append(f"Whether the prosecution proved the essential statutory ingredients of {ch.section} ({ch.statute}) beyond reasonable doubt?")
        issues.append("Whether the evidentiary chain of custody was maintained in compliance with statutory procedure?")
        issues.append("Whether the accused is entitled to the benefit of reasonable doubt?")
        return issues

    return [
        "Whether the prosecution has proved the statutory ingredients of the charged offences beyond reasonable doubt?",
        "Whether the evidentiary recovery was effected in accordance with statutory procedure and independent witnesses?",
        "Whether the accused is entitled to the benefit of reasonable doubt?"
    ]


def validate_clean_message(msg: str, fallback: str) -> str:
    """Ensures response is never empty, never 'Proceed.', and never contains newborn child hallucinations."""
    if not msg or not isinstance(msg, str):
        return fallback
    cleaned = msg.strip().strip('"').strip("'")
    cleaned_lower = cleaned.lower()
    if cleaned_lower in ["proceed", "proceed.", "i proceed", "proceed with the case", "proceed.", ""]:
        return fallback
    if len(cleaned) < 12:
        return fallback
    if "newborn" in cleaned_lower or "infant" in cleaned_lower or "abandoned his child" in cleaned_lower:
        logger.warning("Rejected hallucinated newborn child content in courtroom debate.")
        return fallback
    return cleaned


class LiveJudgeAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def orchestrate(
        self,
        case: Optional[StructuredCase],
        prosecution: Optional[ProsecutionCase],
        defense: Optional[DefenseCase],
        transcript: List[Dict[str, Any]],
        active_issue: Optional[str] = None,
        turn_in_issue: int = 0,
        issue_index: int = 0,
        concluded_issues: Optional[List[str]] = None,
    ) -> JudgeAction:
        ctx = extract_grounded_case_context(case, prosecution, defense)
        issues = get_case_issues(case)
        concluded = list(concluded_issues or [])
        total_transcript_turns = len(transcript)

        # Decide current active issue
        if issue_index >= len(issues):
            issue_index = len(issues) - 1
        current_issue = active_issue or issues[issue_index]

        # Case ends if enough turns have transpired or all issues debated
        if total_transcript_turns >= 12 or (issue_index >= len(issues) - 1 and turn_in_issue >= 5):
            msg = (
                "The Court has heard full arguments from both the Prosecutor and the Defence on all issues raised. "
                "Oral arguments are now closed, and the Court will proceed to deliver its final judgment."
            )
            return JudgeAction(
                message=msg,
                next_speaker="end_hearing",
                active_issue="Oral Hearing Concluded",
                turn_in_issue=turn_in_issue + 1,
                issue_index=issue_index,
                concluded_issues=concluded + [current_issue]
            )

        # START OF HEARING or TRANSITION TO NEW ISSUE (turn_in_issue == 0)
        if turn_in_issue == 0 or not transcript:
            intro_msg = (
                f"This Court is now hearing the case of {ctx['title']}. The first issue before us is: {current_issue}. "
                "Learned Public Prosecutor, please state your main evidence linking the accused to this issue."
            )
            return JudgeAction(
                message=intro_msg,
                next_speaker="prosecutor",
                active_issue=current_issue,
                turn_in_issue=1,
                issue_index=issue_index,
                concluded_issues=concluded
            )

        # JUDGE INTERVENTION AFTER 4 LAWYER TURNS (turn_in_issue >= 5)
        # Sequence so far: Judge (0) -> Pros (1) -> Def (2) -> Pros (3) -> Def (4) -> Judge (5)
        last_speaker = transcript[-1]["role"] if transcript else "defense"
        last_content = transcript[-1]["content"] if transcript else ""

        # Transition to next issue if available
        if issue_index + 1 < len(issues):
            next_idx = issue_index + 1
            next_issue = issues[next_idx]
            transition_msg = (
                f"The Court has taken note of both sides' arguments on {current_issue}. "
                f"We now move to the next issue: {next_issue}. Learned Prosecutor, please state your position on this."
            )
            return JudgeAction(
                message=transition_msg,
                next_speaker="prosecutor",
                active_issue=next_issue,
                turn_in_issue=1,
                issue_index=next_idx,
                concluded_issues=concluded + [current_issue]
            )

        # If on the last issue and lawyers have exchanged points, close hearing
        conclude_msg = (
            "The Court has recorded the arguments of both sides on all issues. "
            "Arguments are now concluded, and the Court will proceed to write its judgment."
        )
        return JudgeAction(
            message=conclude_msg,
            next_speaker="end_hearing",
            active_issue=current_issue,
            turn_in_issue=turn_in_issue + 1,
            issue_index=issue_index,
            concluded_issues=concluded + [current_issue]
        )


class LiveProsecutorAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def argue(
        self,
        case: Optional[StructuredCase],
        prosecution: Optional[ProsecutionCase],
        transcript: List[Dict[str, Any]],
        active_issue: Optional[str],
        turn_in_issue: int = 1,
        previous_speaker: Optional[str] = "judge",
        previous_message: Optional[str] = None,
        unresolved_argument: Optional[str] = None,
    ) -> LawyerAction:
        ctx = extract_grounded_case_context(case, prosecution=prosecution)
        issue = active_issue or "The statutory ingredients and evidentiary proof of the charged offences"
        prev_spk = previous_speaker or (transcript[-1]["role"] if transcript else "judge")
        prev_msg = previous_message or (transcript[-1]["content"] if transcript else "")

        # Dynamic case-grounded fallbacks
        if case and case.charges:
            first_charge = f"{case.charges[0].section} {case.charges[0].statute}"
            if turn_in_issue <= 2:
                fallback_msg = (
                    f"The prosecution submits that the documentary and ocular evidence on record establishes "
                    f"the foundational elements of {first_charge} beyond reasonable doubt."
                )
            else:
                fallback_msg = (
                    f"The chain of evidentiary custody and witness depositions directly corroborates the charges under {first_charge}, "
                    f"leaving no reasonable doubt as to the guilt of the accused."
                )
        else:
            if turn_in_issue <= 2:
                fallback_msg = (
                    "The prosecution relies on the documentary seizure memos and witness testimonies on record "
                    "which establish that the accused committed the alleged offences."
                )
            else:
                fallback_msg = (
                    "The evidentiary record and witness depositions establish a complete chain of circumstances "
                    "connecting the accused to the charged offences beyond reasonable doubt."
                )

        prepared_args_text = "\n".join(ctx.get("prepared_arguments", []))
        
        system_prompt = f"""You are the Public Prosecutor in a LIVE turn-by-turn Indian criminal trial.
CASE: {ctx['title']} ({ctx['court_id']})
CHARGES: {ctx['charges']}
CURRENT ISSUE UNDER DEBATE: {issue}
RECORD EVIDENCE: {ctx['exhibits']}
WITNESSES: {ctx['witnesses']}

YOUR PRIVATE PREPARATION (Use as knowledge to answer, do NOT read as a speech):
{prepared_args_text}

LANGUAGE STYLE RULES (MANDATORY):
- Use clear, natural English. Keep sentences short and to the point.
- You must still sound like a lawyer arguing in court — professional and firm.
- If you use a legal term (e.g. testimony, conscious possession, corroboration, reasonable doubt), that is fine — but keep the overall sentence easy to follow.
- Do NOT use unnecessarily complex legal phrasing when a simpler expression carries the same meaning.
- Example: Instead of "the prosecution's reliance is flawed as it lacks corroboration", say "the prosecution is heavily relying on PW-6, but there is no independent witness to support what he said."

CRITICAL CONVERSATIONAL RULES:
1. SHORT & PUNCHY: Exactly 1 to 3 short sentences. Make ONE focused point.
2. DIRECT RESPONSE: Always respond to what the previous speaker actually said.
   - If responding to the Judge: State your strongest evidence on the issue.
   - If responding to Defence Counsel: Directly address their challenge with record evidence.
3. STRICT FACTUAL GROUNDING: Only refer to facts, charges, exhibits, and witnesses strictly from the current case record provided above.
4. ABSOLUTE PROHIBITION: NEVER say "Proceed." NEVER bring up newborn children or infant abandonment.
5. NEXT SPEAKER: Always set next_speaker to 'defense'."""

        user_prompt = f"""PREVIOUS SPEAKER: {prev_spk.upper()}
PREVIOUS STATEMENT: "{prev_msg}"
ACTIVE ISSUE: {issue}
TURN IN ISSUE: {turn_in_issue}

Give your direct, spoken courtroom response (1-2 sentences), addressing what the previous speaker just said. Use clear, professional language that an ordinary person can follow."""

        try:
            action = self.llm_service.generate_structured(
                prompt=user_prompt,
                response_schema=LawyerAction,
                system_prompt=system_prompt,
                fallback_data={"message": fallback_msg, "next_speaker": "defense"},
            )
            clean_msg = validate_clean_message(action.message, fallback_msg)
            return LawyerAction(
                message=clean_msg,
                next_speaker="defense",
                unresolved_argument=clean_msg
            )
        except Exception as e:
            logger.warning("LiveProsecutorAgent error: %s. Using case fallback.", e)
            return LawyerAction(message=fallback_msg, next_speaker="defense", unresolved_argument=fallback_msg)


class LiveDefenseAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def argue(
        self,
        case: Optional[StructuredCase],
        defense: Optional[DefenseCase],
        transcript: List[Dict[str, Any]],
        active_issue: Optional[str],
        turn_in_issue: int = 2,
        previous_speaker: Optional[str] = "prosecutor",
        previous_message: Optional[str] = None,
        unresolved_argument: Optional[str] = None,
    ) -> LawyerAction:
        ctx = extract_grounded_case_context(case, defense=defense)
        issue = active_issue or "The statutory ingredients and evidentiary proof of the charged offences"
        prev_spk = previous_speaker or (transcript[-1]["role"] if transcript else "prosecutor")
        prev_msg = previous_message or (transcript[-1]["content"] if transcript else "")

        # Decide whether defense responds back to prosecutor or hands off to judge
        # Debate flow: Turn 2 (Def challenges Pros) -> next is prosecutor
        # Turn 4 (Def replies to Pros rebuttal) -> next is judge
        next_role = "prosecutor" if turn_in_issue <= 2 else "judge"

        # Dynamic case-grounded fallbacks
        if case and case.charges:
            first_charge = f"{case.charges[0].section} {case.charges[0].statute}"
            if turn_in_issue <= 2:
                fallback_msg = (
                    f"The prosecution has failed to produce independent corroborative witnesses to prove {first_charge}. "
                    f"Material contradictions in the prosecution case create substantial doubt."
                )
            else:
                fallback_msg = (
                    f"Conjecture cannot take the place of legal proof. Without independent ocular or forensic corroboration, "
                    f"the charges under {first_charge} cannot stand beyond reasonable doubt."
                )
        else:
            if turn_in_issue <= 2:
                fallback_msg = (
                    "The prosecution evidence suffers from serious contradictions and lacks independent civilian corroboration. "
                    "The mandatory procedural requirements were not complied with."
                )
            else:
                fallback_msg = (
                    "Suspicion, however grave, cannot take the place of proof beyond reasonable doubt. "
                    "The accused is entitled to the full benefit of doubt."
                )

        prepared_args_text = "\n".join(ctx.get("prepared_arguments", []))

        system_prompt = f"""You are the Defence Counsel in a LIVE turn-by-turn Indian criminal trial.
CASE: {ctx['title']} ({ctx['court_id']})
CHARGES: {ctx['charges']}
CURRENT ISSUE UNDER DEBATE: {issue}
RECORD EVIDENCE: {ctx['exhibits']}
WITNESSES: {ctx['witnesses']}

YOUR PRIVATE PREPARATION (Use as knowledge to answer, do NOT read as a speech):
{prepared_args_text}

LANGUAGE STYLE RULES (MANDATORY):
- Use clear, natural English. Keep sentences short and direct.
- You must still sound like a lawyer — firm and professional.
- If you use a legal term (e.g. Test Identification Parade, conscious possession, corroboration, reasonable doubt), that is fine — but keep the overall sentence easy to follow.
- Do NOT use unnecessarily complex legal phrasing when a simpler expression works.
- Example: Instead of "the Prosecutor's submission is bereft of evidentiary corroboration", say "the Prosecutor has not provided any independent evidence to support that claim."

CRITICAL CONVERSATIONAL RULES:
1. SHORT & PUNCHY: Exactly 1 to 3 short sentences. Make ONE sharp challenge.
2. DIRECT RESPONSE: Always directly address what the Prosecutor just said.
   - Point out the gaps: absence of independent civilian witnesses, procedural non-compliance, or missing links in the chain of evidence.
3. STRICT FACTUAL GROUNDING: Only refer to facts, charges, exhibits, and witnesses strictly from the current case record provided above.
4. ABSOLUTE PROHIBITION: NEVER say "Proceed." NEVER bring up newborn children or infant abandonment.
5. NEXT SPEAKER: Set next_speaker to '{next_role}'."""

        user_prompt = f"""PREVIOUS SPEAKER: {prev_spk.upper()}
PREVIOUS STATEMENT: "{prev_msg}"
ACTIVE ISSUE: {issue}
TURN IN ISSUE: {turn_in_issue}

Give your direct, spoken courtroom challenge (1-2 sentences), responding to what the Prosecutor just said. Use clear, professional language that an ordinary person can follow."""

        try:
            action = self.llm_service.generate_structured(
                prompt=user_prompt,
                response_schema=LawyerAction,
                system_prompt=system_prompt,
                fallback_data={"message": fallback_msg, "next_speaker": next_role},
            )
            clean_msg = validate_clean_message(action.message, fallback_msg)
            return LawyerAction(
                message=clean_msg,
                next_speaker=next_role,
                unresolved_argument=clean_msg
            )
        except Exception as e:
            logger.warning("LiveDefenseAgent error: %s. Using case fallback.", e)
            return LawyerAction(message=fallback_msg, next_speaker=next_role, unresolved_argument=fallback_msg)


class LiveEvidenceAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def clarify(
        self,
        evidence_analysis: Optional[EvidenceAnalysisReport],
        transcript: List[Dict[str, Any]],
        active_issue: Optional[str],
    ) -> LawyerAction:
        fallback_msg = (
            evidence_analysis.summary
            if evidence_analysis and (evidence_analysis.summary or "").strip()
            else "The evidentiary record relies on the marked exhibits and witness testimonies extracted from the case packet."
        )
        return LawyerAction(message=fallback_msg, next_speaker="judge")


class LiveConflictAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    def clarify(
        self,
        conflict_report: Optional[ConflictReport],
        transcript: List[Dict[str, Any]],
        active_issue: Optional[str],
    ) -> LawyerAction:
        fallback_msg = (
            conflict_report.summary
            if conflict_report and (conflict_report.summary or "").strip()
            else "The factual and evidentiary conflicts identified between the prosecution and defence submissions require judicial determination."
        )
        return LawyerAction(message=fallback_msg, next_speaker="judge")
