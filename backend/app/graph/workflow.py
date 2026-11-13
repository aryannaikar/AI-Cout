"""
LangGraph Courtroom Workflow Compilation and Execution Engine.
Constructs the deterministic courtroom orchestration graph with parallel branches:
Case Understanding -> [Prosecution Branch & Defense Branch] -> Evidence -> Conflict -> Judge -> END.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional, Union

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from langgraph.graph import END, START, StateGraph

from datetime import datetime
import time

from app.graph.nodes import (
    case_understanding_node,
    conflict_node,
    defense_legal_research_node,
    defense_node,
    defense_web_research_node,
    evidence_node,
    judge_node,
    prosecutor_legal_research_node,
    prosecutor_node,
    prosecutor_web_research_node,
    live_judge_node,
    live_prosecutor_node,
    live_defense_node,
    live_evidence_node,
    live_conflict_node,
)
from app.graph.state import CourtState
from app.graph.validation import validate_case_packet_path, validate_no_ground_truth_text
from app.models.execution_models import ExecutionReport

logger = logging.getLogger(__name__)


def create_court_graph() -> StateGraph:
    """
    Build the uncompiled StateGraph for the courtroom proceedings.
    Registers all 13 nodes and wires parallel prosecution and defense tracks,
    followed by a live conversational loop, and then final judgment.
    """
    builder = StateGraph(CourtState)

    # 1. Register logical nodes
    builder.add_node("case_understanding", case_understanding_node)
    builder.add_node("prosecutor", prosecutor_node)
    builder.add_node("prosecutor_legal_research", prosecutor_legal_research_node)
    builder.add_node("prosecutor_web_research", prosecutor_web_research_node)

    builder.add_node("defense", defense_node)
    builder.add_node("defense_legal_research", defense_legal_research_node)
    builder.add_node("defense_web_research", defense_web_research_node)

    builder.add_node("evidence", evidence_node)
    builder.add_node("conflict", conflict_node)
    
    # New live hearing nodes
    builder.add_node("live_judge", live_judge_node)
    builder.add_node("live_prosecutor", live_prosecutor_node)
    builder.add_node("live_defense", live_defense_node)
    builder.add_node("live_evidence", live_evidence_node)
    builder.add_node("live_conflict", live_conflict_node)

    # Final judgment node
    builder.add_node("judge", judge_node)

    # 2. Wire edges
    # START -> Case Understanding
    builder.add_edge(START, "case_understanding")

    # Sequential flow to allow Defense to respond to Prosecution
    builder.add_edge("case_understanding", "prosecutor")

    # Prosecution branch sequence: Prosecutor -> Local RAG -> Web Research
    builder.add_edge("prosecutor", "prosecutor_legal_research")
    builder.add_edge("prosecutor_legal_research", "prosecutor_web_research")

    # Connect Prosecution end to Defense start
    builder.add_edge("prosecutor_web_research", "defense")

    # Defense branch sequence: Defense -> Local RAG -> Web Research
    builder.add_edge("defense", "defense_legal_research")
    builder.add_edge("defense_legal_research", "defense_web_research")

    # Connect Defense end to Evidence Analysis
    builder.add_edge("defense_web_research", "evidence")

    # Post-evidence conflict reasoning
    builder.add_edge("evidence", "conflict")
    
    # Enter Live Hearing
    builder.add_edge("conflict", "live_judge")
    
    # Live Hearing Conditional Router
    def live_hearing_router(state: CourtState) -> str:
        speaker = (state.next_speaker or "").strip().lower()
        if speaker == "end_hearing" or len(state.transcript) >= 14:
            return "judge"
        if "prosecut" in speaker:
            return "live_prosecutor"
        if "defen" in speaker:
            return "live_defense"
        if "evid" in speaker:
            return "live_evidence"
        if "conflic" in speaker:
            return "live_conflict"
        if "judge" in speaker or "conclude" in speaker:
            return "live_judge"
        return "judge" # fallback

    builder.add_conditional_edges("live_judge", live_hearing_router)
    builder.add_conditional_edges("live_prosecutor", live_hearing_router)
    builder.add_conditional_edges("live_defense", live_hearing_router)
    builder.add_conditional_edges("live_evidence", live_hearing_router)
    builder.add_conditional_edges("live_conflict", live_hearing_router)

    # Final judgment node to END
    builder.add_edge("judge", END)

    return builder


class CourtWorkflow:
    """
    High-level orchestrator wrapping the compiled LangGraph courtroom graph.
    Integrates real execution, disk persistence (JSON, TXT, PDF), and execution reporting.
    """

    def __init__(self):
        self.builder = create_court_graph()
        self.app = self.builder.compile()
        logger.info("Compiled LangGraph CourtWorkflow successfully.")

    def run(
        self,
        case_packet: Union[str, Path, dict[str, Any]],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> CourtState:
        """
        Execute the full trial proceeding, persist artifacts, and return complete state.

        Args:
            case_packet: File path to Case_Packet.pdf, or raw text of case packet,
                         or an initial state dictionary.
            output_dir: Optional custom directory to persist judgment artifacts.

        Returns:
            Final populated CourtState containing complete trial record, judgment,
            and attached ExecutionReport.
        """
        start_time = time.perf_counter()

        if isinstance(case_packet, dict):
            init_data = case_packet
        else:
            validate_case_packet_path(case_packet)
            validate_no_ground_truth_text(str(case_packet))
            if isinstance(case_packet, Path) or (
                isinstance(case_packet, str)
                and (case_packet.lower().endswith(".pdf") or "/" in case_packet or "\\" in case_packet)
                and "\n" not in case_packet
            ):
                if not Path(case_packet).exists():
                    raise FileNotFoundError(f"Case packet file not found: {case_packet}")
            init_data = {"case_packet": str(case_packet)}

        initial_state = CourtState(**init_data)
        output = self.app.invoke(initial_state, config={"recursion_limit": 100})

        if isinstance(output, CourtState):
            final_state = output
        else:
            final_state = CourtState(**output)

        elapsed = time.perf_counter() - start_time

        case_id = _workflow_case_id(case_packet, final_state.case_analysis)

        agent_statuses = {}
        for entry in final_state.execution_log:
            agent_statuses[entry.node] = entry.status

        if final_state.judgment and not final_state.errors:
            overall_status = "completed"
        elif final_state.judgment and final_state.errors:
            overall_status = "partial"
        else:
            overall_status = "failed"

        report = ExecutionReport(
            case_id=case_id,
            status=overall_status,
            ai_judgment=final_state.judgment,
            execution_log=final_state.execution_log,
            agent_statuses=agent_statuses,
            errors=final_state.errors,
            execution_time_seconds=round(elapsed, 3),
        )
        final_state.execution_report = report

        # Persist judgment and report if judgment was successfully rendered
        if final_state.judgment:
            from app.services.judgment_writer import JudgmentWriter
            writer = JudgmentWriter()
            target_out = output_dir or writer.get_case_output_dir(case_id)
            writer.persist_judgment(case_id=case_id, judgment=final_state.judgment, custom_output_dir=target_out)
            writer.persist_execution_report(case_id=case_id, report_data=report.model_dump(), custom_output_dir=target_out)
            logger.info("Persisted AI Judgment and execution report for '%s' to '%s'", case_id, target_out)

        return final_state

    def stream_trial(
        self,
        case_packet: Union[str, Path, dict[str, Any]],
        output_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Execute the courtroom proceeding progressively, yielding real-time SSE events
        as each of the 10 agents begins, deliberates, and finishes.
        """
        start_time = time.perf_counter()

        if isinstance(case_packet, dict):
            init_data = case_packet
        else:
            validate_case_packet_path(case_packet)
            validate_no_ground_truth_text(str(case_packet))
            if isinstance(case_packet, Path) or (
                isinstance(case_packet, str)
                and (case_packet.lower().endswith(".pdf") or "/" in case_packet or "\\" in case_packet)
                and "\n" not in case_packet
            ):
                if not Path(case_packet).exists():
                    raise FileNotFoundError(f"Case packet file not found: {case_packet}")
            init_data = {"case_packet": str(case_packet)}

        initial_state = CourtState(**init_data)

        yield {
            "type": "session_started",
            "timestamp": datetime.now().isoformat(),
            "message": "AI Court of India session initiated. Courtroom bench seated.",
        }

        # Accumulate state updates across the streamed execution
        accumulated_state: dict[str, Any] = init_data.copy()
        execution_log_entries = []
        errors = []

        for chunk in self.app.stream(initial_state, config={"recursion_limit": 100}, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                metadata = NODE_METADATA.get(node_name, {
                    "title": node_name.replace("_", " ").title(),
                    "role": "Courtroom Agent",
                    "avatar": "User",
                    "side": "neutral",
                })

                # Event 1: Agent started thinking
                yield {
                    "type": "agent_started",
                    "agent": node_name,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat(),
                }

                # Update accumulated state
                if isinstance(node_update, dict):
                    for k, v in node_update.items():
                        if k == "execution_log":
                            execution_log_entries.extend(v)
                        elif k == "errors":
                            errors.extend(v)
                        else:
                            accumulated_state[k] = v

                # Event 2: Agent message / reasoning payload
                payload = _format_agent_payload(node_name, node_update)
                yield {
                    "type": "agent_message",
                    "agent": node_name,
                    "metadata": metadata,
                    "payload": payload,
                    "timestamp": datetime.now().isoformat(),
                }

                # Event 3: Agent completed
                yield {
                    "type": "agent_completed",
                    "agent": node_name,
                    "metadata": metadata,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                }

        # Build ExecutionReport and persist judgment artifacts
        elapsed = time.perf_counter() - start_time
        judgment = accumulated_state.get("judgment")
        case_analysis = accumulated_state.get("case_analysis")

        case_id = _workflow_case_id(case_packet, case_analysis)

        agent_statuses = {}
        for entry in execution_log_entries:
            agent_statuses[entry.node] = entry.status

        if judgment and not errors:
            overall_status = "completed"
        elif judgment and errors:
            overall_status = "partial"
        else:
            overall_status = "failed"

        report = ExecutionReport(
            case_id=case_id,
            status=overall_status,
            ai_judgment=judgment,
            execution_log=execution_log_entries,
            agent_statuses=agent_statuses,
            errors=errors,
            execution_time_seconds=round(elapsed, 3),
        )

        judgment_dict = judgment.model_dump() if judgment else None
        report_dict = report.model_dump()
        persisted_files: dict[str, str] = {}

        if judgment:
            from app.services.judgment_writer import JudgmentWriter
            writer = JudgmentWriter()
            target_out = output_dir or writer.get_case_output_dir(case_id)
            persisted_files = writer.persist_judgment(case_id=case_id, judgment=judgment, custom_output_dir=target_out)
            writer.persist_execution_report(case_id=case_id, report_data=report_dict, custom_output_dir=target_out)
            logger.info("stream_trial persisted AI Judgment for '%s' to '%s'", case_id, target_out)

        yield {
            "type": "court_completed",
            "case_id": case_id,
            "status": overall_status,
            "judgment": judgment_dict,
            "report": report_dict,
            "persisted_files": persisted_files,
            "execution_time_seconds": round(elapsed, 3),
            "timestamp": datetime.now().isoformat(),
        }


NODE_METADATA = {
    "case_understanding": {
        "title": "Case Understanding Agent",
        "role": "Registrar / Fact Analysis",
        "avatar": "FileText",
        "side": "neutral",
    },
    "prosecutor": {
        "title": "Public Prosecutor Agent",
        "role": "State Prosecution Counsel",
        "avatar": "Scale",
        "side": "prosecution",
    },
    "defense": {
        "title": "Defense Counsel Agent",
        "role": "Defense Legal Representative",
        "avatar": "Shield",
        "side": "defense",
    },
    "prosecutor_legal_research": {
        "title": "Prosecution Legal Research Agent",
        "role": "Statutory Research (Legal RAG)",
        "avatar": "BookOpen",
        "side": "prosecution",
    },
    "defense_legal_research": {
        "title": "Defense Legal Research Agent",
        "role": "Statutory Research (Legal RAG)",
        "avatar": "BookOpen",
        "side": "defense",
    },
    "prosecutor_web_research": {
        "title": "Prosecution Web Research Agent",
        "role": "Judicial Precedent & External Research",
        "avatar": "Globe",
        "side": "prosecution",
    },
    "defense_web_research": {
        "title": "Defense Web Research Agent",
        "role": "Judicial Precedent & External Research",
        "avatar": "Globe",
        "side": "defense",
    },
    "evidence": {
        "title": "Evidence Analysis Agent",
        "role": "Forensic & Evidentiary Appraisal",
        "avatar": "Microscope",
        "side": "neutral",
    },
    "conflict": {
        "title": "Conflict Detection Agent",
        "role": "Adversarial Contradiction Analysis",
        "avatar": "AlertTriangle",
        "side": "neutral",
    },
    "judge": {
        "title": "Final Judgment",
        "role": "Judicial Adjudication & Verdict",
        "avatar": "Award",
        "side": "judicial",
    },
    "live_judge": {
        "title": "Presiding Judge",
        "role": "Courtroom Orchestration",
        "avatar": "Gavel",
        "side": "judicial",
    },
    "live_prosecutor": {
        "title": "Public Prosecutor",
        "role": "State Prosecution Counsel",
        "avatar": "Scale",
        "side": "prosecution",
    },
    "live_defense": {
        "title": "Defense Counsel",
        "role": "Defense Legal Representative",
        "avatar": "Shield",
        "side": "defense",
    },
    "live_evidence": {
        "title": "Independent Evidence Analyst",
        "role": "Fact Verification",
        "avatar": "Microscope",
        "side": "neutral",
    },
    "live_conflict": {
        "title": "Conflict Detection",
        "role": "Testimony Analysis",
        "avatar": "AlertTriangle",
        "side": "neutral",
    },
}


def _format_agent_payload(node_name: str, update: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"node": node_name}
    if not isinstance(update, dict):
        return payload

    if node_name == "case_understanding":
        analysis = update.get("case_analysis")
        if analysis:
            payload["summary"] = f"Case Registered: {analysis.case_title} ({analysis.court_identifier}). Accused: {', '.join(analysis.accused)}. Allegations: {analysis.allegations_summary}"
            payload["charges"] = [f"{c.statute} {c.section}: {c.description}" for c in analysis.charges]
            payload["facts"] = analysis.prosecution_facts
            payload["defense_plea"] = analysis.defense_facts
            payload["witnesses"] = [f"{w.witness_id}: {w.witness_name}" for w in analysis.witnesses]
            payload["exhibits"] = [f"{e.exhibit_id}: {e.title} ({e.exhibit_type})" for e in analysis.exhibits]
    elif node_name == "prosecutor":
        pros = update.get("prosecution")
        if pros:
            payload["summary"] = f"Prosecution Theory: {pros.prosecution_theory}"
            payload["prayer"] = pros.final_prayer
            payload["statutory_elements"] = pros.statutory_elements
            payload["arguments"] = [
                {"type": arg.statement_type.value if hasattr(arg.statement_type, "value") else str(arg.statement_type), "content": arg.content, "source": arg.source_reference}
                for arg in pros.argument_components
            ]
            payload["supporting_witnesses"] = pros.supporting_witnesses
            payload["supporting_exhibits"] = pros.supporting_exhibits
    elif node_name == "defense":
        defense = update.get("defense")
        if defense:
            payload["summary"] = f"Defense Theory: {defense.defense_theory}"
            payload["prayer"] = defense.final_prayer
            payload["reasonable_doubts"] = defense.reasonable_doubt_grounds
            payload["arguments"] = [
                {"type": arg.statement_type.value if hasattr(arg.statement_type, "value") else str(arg.statement_type), "content": arg.content, "source": arg.source_reference}
                for arg in defense.argument_components
            ]
            payload["missing_evidence"] = defense.missing_evidence_highlighted
            payload["witness_inconsistencies"] = defense.witness_inconsistencies_highlighted
    elif node_name in ["prosecutor_legal_research", "defense_legal_research"]:
        key = "prosecution_legal_research" if node_name == "prosecutor_legal_research" else "defense_legal_research"
        res = update.get(key)
        if res:
            payload["question"] = res.question
            payload["findings"] = res.findings
            payload["citations"] = res.citations
            payload["provisions"] = [
                {
                    "act": p.act_name,
                    "section": p.section_or_article,
                    "title": p.title,
                    "citation": p.citation,
                    "page": p.page,
                    "reasoning": p.relevance_reasoning,
                }
                for p in res.applicable_provisions
            ]
    elif node_name in ["prosecutor_web_research", "defense_web_research"]:
        key = "prosecution_web_research" if node_name == "prosecutor_web_research" else "defense_web_research"
        res = update.get(key)
        if res:
            payload["question"] = res.research_question
            payload["findings"] = res.finding
            payload["why_it_matters"] = res.why_it_matters
            payload["sources"] = [
                {
                    "title": s.title,
                    "url": s.url,
                    "summary": s.passage_summary,
                    "relevance": s.why_source_matters,
                }
                for s in res.sources
            ]
    elif node_name == "evidence":
        ev = update.get("evidence_analysis")
        if ev:
            payload["summary"] = ev.summary
            payload["documentary_compliance"] = ev.documentary_compliance_assessment
            payload["missing_gaps"] = ev.missing_evidence_gaps
            payload["contradictions"] = ev.evidentiary_contradictions
            payload["items"] = [
                {
                    "id": item.id,
                    "description": item.description,
                    "type": item.type.value if hasattr(item.type, "value") else str(item.type),
                    "source": item.source,
                    "chain_of_custody_intact": item.chain_of_custody_intact,
                    "confidence": item.confidence,
                    "limitations": item.limitations,
                }
                for item in ev.evidence_items
            ]
    elif node_name == "conflict":
        conf = update.get("conflicts")
        if conf:
            payload["summary"] = conf.summary
            payload["total_conflicts"] = conf.total_conflicts
            payload["critical_count"] = conf.critical_conflicts_count
            payload["conflicts"] = [
                {
                    "id": c.conflict_id,
                    "category": c.category.value if hasattr(c.category, "value") else str(c.category),
                    "statement_a": c.statement_a,
                    "statement_b": c.statement_b,
                    "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                    "explanation": c.explanation,
                }
                for c in conf.conflicts
            ]
    elif node_name == "judge":
        jd = update.get("judgment")
        if jd:
            # Include the complete, structured judgment in the final-agent event.
            # The browser can therefore enable the final-judgment and comparison
            # controls as soon as the judge has rendered a decision, rather than
            # waiting for the terminal SSE event to be processed.
            payload["judgment"] = jd.model_dump() if hasattr(jd, "model_dump") else jd
            payload["summary"] = f"VERDICT: {jd.final_decision}. Ratio Decidendi: {jd.reasons[:250]}..."
            payload["decision"] = jd.final_decision
            payload["findings"] = jd.findings_per_charge
            payload["issues"] = jd.issues_for_determination
            payload["reasons"] = jd.reasons
            payload["citations"] = jd.legal_citations
    elif node_name in ["live_judge", "live_prosecutor", "live_defense", "live_evidence", "live_conflict"]:
        t_arr = update.get("transcript")
        if t_arr and len(t_arr) > 0:
            payload["message"] = t_arr[-1]["content"]
            payload["active_issue"] = update.get("active_issue") or "Courtroom Debate"
    return payload


def _workflow_case_id(case_packet: Union[str, Path, dict[str, Any]], case_analysis: Any) -> str:
    """Keep uploaded-case IDs stable across persistence, SSE, and API lookups."""
    if isinstance(case_packet, (str, Path)):
        stem = Path(str(case_packet)).stem
        if stem.endswith("_Case_Packet"):
            stem = stem[:-len("_Case_Packet")]
        if stem.startswith("up_"):
            return stem
    if case_analysis and case_analysis.case_id and case_analysis.case_id != "CASE-001":
        return case_analysis.case_id
    return "CASE-001"


def run_court(
    case_packet: Union[str, Path, dict[str, Any]],
    config: Optional[dict[str, Any]] = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> CourtState:
    """
    Clean entry point to execute the complete AI Court of India courtroom proceedings.

    Args:
        case_packet: Path to Case_Packet.pdf, raw text, or state dictionary.
        config: Optional configuration dictionary.
        output_dir: Optional custom output directory for persisted artifacts.

    Returns:
        Final CourtState containing complete trial record, AI judgment, and execution report.
    """
    workflow = CourtWorkflow()
    return workflow.run(case_packet, output_dir=output_dir)
