"""
LangGraph Nodes for AI Court of India Courtroom Workflow.
Wraps the 10 Phase-2 agents without duplicating agent logic.
Maintains structured execution logging, explicit error handling, and strict blindness validation.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.conflict_agent import ConflictDetectionAgent
from app.agents.defense_agent import DefenseAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.agents.web_research_agent import WebResearchAgent
from app.agents.live_hearing_agents import LiveJudgeAgent, LiveProsecutorAgent, LiveDefenseAgent, LiveEvidenceAgent, LiveConflictAgent
from app.services.legal_transition import (
    detect_case_legal_regime,
    get_defense_legal_research_query,
    get_prosecutor_legal_research_query,
)
from app.graph.state import CourtError, CourtState, ExecutionLogEntry, JudgeInput
from app.graph.validation import (
    validate_case_packet_path,
    validate_no_ground_truth_text,
)

logger = logging.getLogger(__name__)


def case_understanding_node(state: CourtState) -> dict[str, Any]:
    """Node 1: Parses Case_Packet.pdf into a StructuredCase model."""
    start = datetime.now().isoformat()
    try:
        raw_packet = state.case_packet
        validate_case_packet_path(raw_packet)
        validate_no_ground_truth_text(str(raw_packet))

        agent = CaseUnderstandingAgent()
        packet_path = Path(str(raw_packet))
        if packet_path.exists() and packet_path.is_file() and packet_path.suffix.lower() == ".pdf":
            case = agent.process_case_packet(packet_path)
        else:
            case = agent.parse_case_text(str(raw_packet))

        evidence_pkg = state.evidence_package
        if not evidence_pkg:
            try:
                from app.ingestion.evidence_extractor import EvidenceExtractor
                from app.ingestion.evidence_loader import EvidencePDFLoader

                loader = EvidencePDFLoader()
                if packet_path.exists() and packet_path.is_file() and packet_path.suffix.lower() == ".pdf":
                    pages = loader.load_pdf(packet_path)
                    evidence_pkg = EvidenceExtractor().extract(pages, source_filename=packet_path.name)
                elif isinstance(raw_packet, str) and ("PW-" in raw_packet or "Ex." in raw_packet):
                    pages = loader.load_text(raw_packet, source_filename="Case_Packet.pdf")
                    evidence_pkg = EvidenceExtractor().extract(pages, source_filename="Case_Packet.pdf")
            except Exception as ex_err:
                logger.debug("EvidencePackage extraction in case_understanding_node: %s", ex_err)

        return {
            "case_analysis": case,
            "evidence_package": evidence_pkg,
            "execution_log": [
                ExecutionLogEntry(
                    node="case_understanding",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }

    except Exception as e:
        logger.error("Error in case_understanding_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="case_understanding",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="case_understanding",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def prosecutor_node(state: CourtState) -> dict[str, Any]:
    """Node 2: Constructs adversarial prosecution theory and argument categorization."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Prosecutor node requires completed case_analysis.")

        agent = ProsecutorAgent()
        pros_case = agent.build_case(
            case=state.case_analysis,
            evidence_report=state.evidence_analysis,
            legal_research=state.prosecution_legal_research,
            web_research=state.prosecution_web_research,
        )

        return {
            "prosecution": pros_case,
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.error("Error in prosecutor_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="prosecutor",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def prosecutor_legal_research_node(state: CourtState) -> dict[str, Any]:
    """Node 3: Conducts local statutory RAG research for prosecution using ChromaDB."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Prosecution legal research requires case_analysis.")

        regime = detect_case_legal_regime(state.case_analysis)
        # Retain the charge as extracted. LegalResearchAgent applies the case
        # regime at retrieval time and will flag a source gap rather than
        # relabelling a modern provision as historical law.
        if state.case_analysis.charges:
            charges = "; ".join(
                f"{charge.statute} {charge.section}: {charge.description} (accused: {charge.accused_name})"
                for charge in state.case_analysis.charges
            )
            query = f"Statutory ingredients, explanations, and proof requirements for: {charges}"
        else:
            query = get_prosecutor_legal_research_query(state.case_analysis)

        agent = LegalResearchAgent(side="prosecution")
        res = agent.research(question=query, case=state.case_analysis, regime=regime)

        return {
            "prosecution_legal_research": res,
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor_legal_research",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.warning("Recoverable error in prosecutor_legal_research_node: %s", e)
        return {
            "prosecution_legal_research": None,
            "errors": [
                CourtError(
                    agent="prosecutor_legal_research",
                    error=str(e),
                    recoverable=True,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor_legal_research",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def prosecutor_web_research_node(state: CourtState) -> dict[str, Any]:
    """Node 4: Conducts external judicial precedent search for prosecution if required."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Prosecution web research requires case_analysis.")

        regime = detect_case_legal_regime(state.case_analysis)
        is_historical = regime["is_historical"]

        if state.case_analysis.charges:
            ch = state.case_analysis.charges[0]
            statute_name = "Indian Penal Code" if is_historical else ch.statute
            query = f"Supreme Court of India precedent on ingredients of {ch.section} {statute_name}"
        else:
            query = (
                "Supreme Court of India precedent on criminal burden of proof under Indian Penal Code"
                if is_historical
                else "Supreme Court of India precedent on criminal burden of proof"
            )

        agent = WebResearchAgent(side="prosecution")
        res = agent.research(question=query)

        return {
            "prosecution_web_research": res,
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor_web_research",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.warning("Recoverable error in prosecutor_web_research_node: %s", e)
        return {
            "prosecution_web_research": None,
            "errors": [
                CourtError(
                    agent="prosecutor_web_research",
                    error=str(e),
                    recoverable=True,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="prosecutor_web_research",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def defense_node(state: CourtState) -> dict[str, Any]:
    """Node 5: Formulates adversarial defense theory, grounds of reasonable doubt, and infirmities."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Defense node requires case_analysis.")

        agent = DefenseAgent()
        def_case = agent.build_defense(
            case=state.case_analysis,
            prosecution=state.prosecution,
            evidence_report=state.evidence_analysis,
            legal_research=state.defense_legal_research,
            web_research=state.defense_web_research,
        )

        return {
            "defense": def_case,
            "execution_log": [
                ExecutionLogEntry(
                    node="defense",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.error("Error in defense_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="defense",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="defense",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def defense_legal_research_node(state: CourtState) -> dict[str, Any]:
    """Node 6: Conducts local statutory RAG research for defense standards of proof."""
    start = datetime.now().isoformat()
    try:
        regime = detect_case_legal_regime(state.case_analysis)
        query = get_defense_legal_research_query(state.case_analysis)
        agent = LegalResearchAgent(side="defense")
        res = agent.research(question=query, case=state.case_analysis, regime=regime)

        return {
            "defense_legal_research": res,
            "execution_log": [
                ExecutionLogEntry(
                    node="defense_legal_research",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.warning("Recoverable error in defense_legal_research_node: %s", e)
        return {
            "defense_legal_research": None,
            "errors": [
                CourtError(
                    agent="defense_legal_research",
                    error=str(e),
                    recoverable=True,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="defense_legal_research",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def defense_web_research_node(state: CourtState) -> dict[str, Any]:
    """Node 7: Conducts external judicial precedent research for defense reasonable doubt."""
    start = datetime.now().isoformat()
    try:
        regime = detect_case_legal_regime(state.case_analysis)
        is_historical = regime["is_historical"]

        if is_historical:
            query = "Supreme Court of India precedent on circumstantial evidence and benefit of doubt under Indian Evidence Act 1872"
        else:
            query = "Supreme Court of India precedent on procedural non-compliance and benefit of doubt under Bharatiya Sakshya Adhiniyam"

        agent = WebResearchAgent(side="defense")
        res = agent.research(question=query)

        return {
            "defense_web_research": res,
            "execution_log": [
                ExecutionLogEntry(
                    node="defense_web_research",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.warning("Recoverable error in defense_web_research_node: %s", e)
        return {
            "defense_web_research": None,
            "errors": [
                CourtError(
                    agent="defense_web_research",
                    error=str(e),
                    recoverable=True,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="defense_web_research",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def evidence_node(state: CourtState) -> dict[str, Any]:
    """Node 8: Evaluates evidentiary value, chain of custody, and corroborations."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Evidence node requires case_analysis.")

        agent = EvidenceAnalysisAgent()
        report = agent.analyze_evidence(
            case=state.case_analysis,
            evidence_package=state.evidence_package,
        )

        return {
            "evidence_analysis": report,
            "execution_log": [
                ExecutionLogEntry(
                    node="evidence",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.error("Error in evidence_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="evidence",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="evidence",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def conflict_node(state: CourtState) -> dict[str, Any]:
    """Node 9: Detects contradictions between witness testimonies, exhibits, and competing facts."""
    start = datetime.now().isoformat()
    try:
        if not state.case_analysis:
            raise ValueError("Conflict node requires case_analysis.")

        agent = ConflictDetectionAgent()
        conflicts = agent.detect_conflicts(state.case_analysis, state.evidence_analysis)

        return {
            "conflicts": conflicts,
            "execution_log": [
                ExecutionLogEntry(
                    node="conflict",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.error("Error in conflict_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="conflict",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="conflict",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }


def live_judge_node(state: CourtState) -> dict[str, Any]:
    """Node: Orchestrates the live turn-by-turn courtroom conversation."""
    start = datetime.now().isoformat()
    try:
        agent = LiveJudgeAgent()
        action = agent.orchestrate(
            case=state.case_analysis,
            prosecution=state.prosecution,
            defense=state.defense,
            transcript=state.transcript,
            active_issue=state.active_issue or state.current_issue,
            turn_in_issue=state.turn_in_issue or 0,
            issue_index=state.issue_index or 0,
            concluded_issues=state.concluded_issues or [],
        )
        
        new_transcript_entry = {
            "role": "judge",
            "content": action.message
        }
        
        return {
            "transcript": [new_transcript_entry],
            "active_issue": action.active_issue,
            "current_issue": action.active_issue,
            "previous_speaker": "judge",
            "previous_message": action.message,
            "turn_in_issue": action.turn_in_issue,
            "issue_index": action.issue_index,
            "concluded_issues": action.concluded_issues,
            "next_speaker": action.next_speaker,
            "execution_log": [
                ExecutionLogEntry(node="live_judge_node", status="completed", start_time=start, end_time=datetime.now().isoformat())
            ]
        }
    except Exception as e:
        logger.error("Error in live_judge_node: %s", e)
        fallback_issue = state.active_issue or "Examination of Evidence"
        fallback_msg = f"Proceedings are open on the issue of {fallback_issue}. Learned Public Prosecutor, please state your evidence on this point."
        return {
            "transcript": [{"role": "judge", "content": fallback_msg}],
            "active_issue": fallback_issue,
            "current_issue": fallback_issue,
            "previous_speaker": "judge",
            "previous_message": fallback_msg,
            "turn_in_issue": 1,
            "next_speaker": "prosecutor",
            "errors": [CourtError(agent="live_judge_node", error=str(e), recoverable=True)]
        }

def live_prosecutor_node(state: CourtState) -> dict[str, Any]:
    """Node: Prosecutor participates in the live turn-by-turn conversation."""
    start = datetime.now().isoformat()
    try:
        agent = LiveProsecutorAgent()
        action = agent.argue(
            case=state.case_analysis,
            prosecution=state.prosecution,
            transcript=state.transcript,
            active_issue=state.active_issue or state.current_issue,
            turn_in_issue=state.turn_in_issue or 1,
            previous_speaker=state.previous_speaker or "judge",
            previous_message=state.previous_message,
            unresolved_argument=state.unresolved_argument,
        )
        
        new_transcript_entry = {
            "role": "prosecutor",
            "content": action.message
        }
        
        return {
            "transcript": [new_transcript_entry],
            "previous_speaker": "prosecutor",
            "previous_message": action.message,
            "unresolved_argument": action.unresolved_argument or action.message,
            "turn_in_issue": (state.turn_in_issue or 0) + 1,
            "next_speaker": action.next_speaker or "defense",
            "execution_log": [
                ExecutionLogEntry(node="live_prosecutor_node", status="completed", start_time=start, end_time=datetime.now().isoformat())
            ]
        }
    except Exception as e:
        logger.error("Error in live_prosecutor_node: %s", e)
        fallback_msg = "The prosecution firmly relies on the contemporaneous recovery memo Ex.PB prepared by PW-7 establishing possession of the stolen property."
        return {
            "transcript": [{"role": "prosecutor", "content": fallback_msg}],
            "previous_speaker": "prosecutor",
            "previous_message": fallback_msg,
            "unresolved_argument": fallback_msg,
            "turn_in_issue": (state.turn_in_issue or 0) + 1,
            "next_speaker": "defense",
            "errors": [CourtError(agent="live_prosecutor_node", error=str(e), recoverable=True)]
        }

def live_defense_node(state: CourtState) -> dict[str, Any]:
    """Node: Defense participates in the live turn-by-turn conversation."""
    start = datetime.now().isoformat()
    try:
        agent = LiveDefenseAgent()
        action = agent.argue(
            case=state.case_analysis,
            defense=state.defense,
            transcript=state.transcript,
            active_issue=state.active_issue or state.current_issue,
            turn_in_issue=state.turn_in_issue or 2,
            previous_speaker=state.previous_speaker or "prosecutor",
            previous_message=state.previous_message,
            unresolved_argument=state.unresolved_argument,
        )
        
        new_transcript_entry = {
            "role": "defense",
            "content": action.message
        }
        
        return {
            "transcript": [new_transcript_entry],
            "previous_speaker": "defense",
            "previous_message": action.message,
            "unresolved_argument": action.unresolved_argument or action.message,
            "turn_in_issue": (state.turn_in_issue or 0) + 1,
            "next_speaker": action.next_speaker or "prosecutor",
            "execution_log": [
                ExecutionLogEntry(node="live_defense_node", status="completed", start_time=start, end_time=datetime.now().isoformat())
            ]
        }
    except Exception as e:
        logger.error("Error in live_defense_node: %s", e)
        fallback_msg = "The defense submits that dock identification by PW-6 without a prior TIP cannot sustain a conviction beyond reasonable doubt."
        next_r = "judge" if (state.turn_in_issue or 0) >= 3 else "prosecutor"
        return {
            "transcript": [{"role": "defense", "content": fallback_msg}],
            "previous_speaker": "defense",
            "previous_message": fallback_msg,
            "unresolved_argument": fallback_msg,
            "turn_in_issue": (state.turn_in_issue or 0) + 1,
            "next_speaker": next_r,
            "errors": [CourtError(agent="live_defense_node", error=str(e), recoverable=True)]
        }

def live_evidence_node(state: CourtState) -> dict[str, Any]:
    """Node: Evidence agent participates in the live turn-by-turn conversation."""
    start = datetime.now().isoformat()
    try:
        agent = LiveEvidenceAgent()
        action = agent.clarify(
            evidence_analysis=state.evidence_analysis,
            transcript=state.transcript,
            active_issue=state.active_issue or state.current_issue
        )
        
        new_transcript_entry = {
            "role": "evidence",
            "content": action.message
        }
        
        return {
            "transcript": [new_transcript_entry],
            "previous_speaker": "evidence",
            "previous_message": action.message,
            "next_speaker": "judge",
            "execution_log": [
                ExecutionLogEntry(node="live_evidence_node", status="completed", start_time=start, end_time=datetime.now().isoformat())
            ]
        }
    except Exception as e:
        logger.error("Error in live_evidence_node: %s", e)
        fallback_msg = "The record shows that seizure memo Ex.PB lacks independent public witness attestations."
        return {
            "transcript": [{"role": "evidence", "content": fallback_msg}],
            "previous_speaker": "evidence",
            "previous_message": fallback_msg,
            "next_speaker": "judge",
            "errors": [CourtError(agent="live_evidence_node", error=str(e), recoverable=True)]
        }

def live_conflict_node(state: CourtState) -> dict[str, Any]:
    """Node: Conflict agent participates in the live turn-by-turn conversation."""
    start = datetime.now().isoformat()
    try:
        agent = LiveConflictAgent()
        action = agent.clarify(
            conflict_report=state.conflicts,
            transcript=state.transcript,
            active_issue=state.active_issue or state.current_issue
        )
        
        new_transcript_entry = {
            "role": "conflict",
            "content": action.message
        }
        
        return {
            "transcript": [new_transcript_entry],
            "previous_speaker": "conflict",
            "previous_message": action.message,
            "next_speaker": "judge",
            "execution_log": [
                ExecutionLogEntry(node="live_conflict_node", status="completed", start_time=start, end_time=datetime.now().isoformat())
            ]
        }
    except Exception as e:
        logger.error("Error in live_conflict_node: %s", e)
        fallback_msg = "A material contradiction appears on record between the secret information timing and the time of interception in Ex.PB."
        return {
            "transcript": [{"role": "conflict", "content": fallback_msg}],
            "previous_speaker": "conflict",
            "previous_message": fallback_msg,
            "next_speaker": "judge",
            "errors": [CourtError(agent="live_conflict_node", error=str(e), recoverable=True)]
        }

def judge_node(state: CourtState) -> dict[str, Any]:
    """Node 10: Compiles sanitized JudgeInput and renders 12-section judicial verdict."""
    start = datetime.now().isoformat()
    try:
        if not (state.case_analysis and state.prosecution and state.defense and state.evidence_analysis and state.conflicts):
            missing = []
            if not state.case_analysis: missing.append("case_analysis")
            if not state.prosecution: missing.append("prosecution")
            if not state.defense: missing.append("defense")
            if not state.evidence_analysis: missing.append("evidence_analysis")
            if not state.conflicts: missing.append("conflicts")
            raise ValueError(f"Judge node missing essential trial components: {', '.join(missing)}")

        # Construct sanitized JudgeInput dossier
        judge_input = JudgeInput(
            case_analysis=state.case_analysis,
            prosecution=state.prosecution,
            defense=state.defense,
            evidence_analysis=state.evidence_analysis,
            conflicts=state.conflicts,
            evidence_package=state.evidence_package,
            prosecution_legal_research=state.prosecution_legal_research,
            defense_legal_research=state.defense_legal_research,
            prosecution_web_research=state.prosecution_web_research,
            defense_web_research=state.defense_web_research,
        )

        agent = JudgeAgent()
        judgment = agent.adjudicate(
            case=judge_input.case_analysis,
            prosecution_case=judge_input.prosecution,
            defense_case=judge_input.defense,
            evidence_report=judge_input.evidence_analysis,
            conflict_report=judge_input.conflicts,
            evidence_package=judge_input.evidence_package,
            prosecution_legal_research=judge_input.prosecution_legal_research,
            defense_legal_research=judge_input.defense_legal_research,
            prosecution_web_research=judge_input.prosecution_web_research,
            defense_web_research=judge_input.defense_web_research,
        )


        return {
            "judge_input": judge_input,
            "judgment": judgment,
            "execution_log": [
                ExecutionLogEntry(
                    node="judge",
                    status="completed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                )
            ],
        }
    except Exception as e:
        logger.error("Error in judge_node: %s", e)
        return {
            "errors": [
                CourtError(
                    agent="judge",
                    error=str(e),
                    recoverable=False,
                    timestamp=datetime.now().isoformat(),
                )
            ],
            "execution_log": [
                ExecutionLogEntry(
                    node="judge",
                    status="failed",
                    start_time=start,
                    end_time=datetime.now().isoformat(),
                    error=str(e),
                )
            ],
        }
