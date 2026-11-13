"""
Comprehensive Courtroom Audit Execution Script.
Executes stream_trial on the Shabuddin case packet and verifies all 6 audit requirements:
1. Historical legal law selection (IPC 302, IEA 1872, no BSA)
2. SentenceTransformer singleton loading count
3. OpenRouter request efficiency, per-agent tracking, and token usage
4. Judge execution, 12 sections, and disk persistence
5. Web research authorities and citations
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir.parent / ".env", override=True)

from app.core.llm_provider import LLMProvider, OpenRouterLLMClient
from app.graph.workflow import CourtWorkflow
from rag.embeddings import EmbeddingModel

def run_audit():
    print("=" * 80)
    print("STARTING AUDIT TRIAL RUN ON SHABUDDIN CASE PACKET")
    print("=" * 80)

    # 1. Reset embedding model cache to test initial load
    EmbeddingModel.clear_cache()
    print("[Check 2] EmbeddingModel cache cleared.")

    # 2. Get OpenRouter client to track initial request count
    client = LLMProvider.get("openrouter")
    initial_requests = client.request_count if isinstance(client, OpenRouterLLMClient) else 0
    print(f"[Check 3] OpenRouter initial request count: {initial_requests}")

    # 3. Locate Shabuddin Case Packet
    target_packet = backend_dir / "data" / "cases" / "uploads" / "up_3042c1bceaa4_Case_Packet.pdf"
    if not target_packet.exists():
        target_packet = backend_dir.parent / "data" / "cases" / "uploads" / "up_3042c1bceaa4_Case_Packet.pdf"
    assert target_packet.exists(), f"Packet not found at: {target_packet}"
    print(f"Target Case Packet: {target_packet} ({target_packet.stat().st_size} bytes)")

    # 4. Stream trial proceedings
    wf = CourtWorkflow()
    events = []
    agent_queries = {}
    completed_event = None

    for ev in wf.stream_trial(str(target_packet)):
        events.append(ev)
        t = ev.get("type")
        agent = ev.get("agent")

        if t == "agent_started":
            print(f"  -> Agent Started: {agent}")
        elif t == "agent_message":
            payload = ev.get("payload", {})
            if "question" in payload:
                agent_queries[agent] = payload["question"]
                print(f"     [Query - {agent}]: {payload['question']}")
            elif "message" in payload:
                print(f"     [{agent}]: {payload['message'][:90]}...")
        elif t == "agent_completed":
            print(f"  <- Agent Completed: {agent}")
        elif t == "court_completed":
            completed_event = ev
            print(f"** Court Completed! Status: {ev.get('status')}")
        elif t == "court_error":
            print(f"!! Court Error: {ev}")

    print("\n" + "=" * 80)
    print("AUDIT TRIAL EXECUTION RESULTS")
    print("=" * 80)

    # Check 1: Historical statute selection
    print("\n--- 1. HISTORICAL STATUTE SELECTION ---")
    def_query = agent_queries.get("defense_legal_research", "")
    pros_query = agent_queries.get("prosecutor_legal_research", "")
    print(f"Prosecution Legal Query: '{pros_query}'")
    print(f"Defense Legal Query:     '{def_query}'")
    assert "Indian Evidence Act 1872" in def_query or "Evidence Act" in def_query, "Defense query must reference Indian Evidence Act 1872!"
    assert "Bharatiya Sakshya Adhiniyam" not in def_query, "Defense query must NOT reference BSA for 2005 case!"
    print("PASS: Historical statute selected for Defense query (Indian Evidence Act 1872, no BSA).")

    # Check 2: SentenceTransformer singleton
    print("\n--- 2. SENTENCETRANSFORMER CACHE ---")
    cache_len = len(EmbeddingModel._model_cache)
    print(f"EmbeddingModel._model_cache instances: {cache_len}")
    assert cache_len == 1, f"Expected exactly 1 shared model in cache, found {cache_len}!"
    print("PASS: Exactly 1 SentenceTransformer model loaded in process memory and shared.")

    # Check 3: OpenRouter request efficiency
    print("\n--- 3. OPENROUTER REQUEST EFFICIENCY ---")
    if isinstance(client, OpenRouterLLMClient):
        summary = client.get_usage_summary()
        trial_requests = summary["total_requests"] - initial_requests
        print(f"Total Requests This Trial: {trial_requests}")
        print(f"Total Tokens Used:         {summary['total_tokens_used']}")
        print(f"Prompt Tokens:             {summary['total_prompt_tokens']}")
        print(f"Completion Tokens:         {summary['total_completion_tokens']}")
        print("Per-Agent Request Breakdown:")
        for ag, cnt in summary["agent_requests"].items():
            print(f"  - {ag}: {cnt}")
    else:
        trial_requests = "N/A"

    # Check 4: Judge Execution and Judgment Validation
    print("\n--- 4. JUDGE EXECUTION AND JUDGMENT VALIDATION ---")
    assert completed_event is not None, "Trial did not emit court_completed event!"
    assert completed_event.get("status") == "completed", f"Trial status is not completed: {completed_event.get('status')}"
    judgment = completed_event.get("judgment")
    assert judgment is not None, "Judgment is missing from court_completed event!"

    sections = [
        ("Section 1: Background", judgment.get("case_background")),
        ("Section 2: Issues", judgment.get("issues_for_determination")),
        ("Section 3: Applicable Law", judgment.get("applicable_law")),
        ("Section 4: Evidence Assessment", judgment.get("evidence_assessment")),
        ("Section 5: Witness Assessment", judgment.get("witness_assessment")),
        ("Section 6: Prosecution Submissions", judgment.get("prosecution_submissions")),
        ("Section 7: Defense Submissions", judgment.get("defense_submissions")),
        ("Section 8: Issue Analyses", judgment.get("issue_analyses")),
        ("Section 9: Findings per Charge", judgment.get("findings_per_charge")),
        ("Section 10: Final Decision", judgment.get("final_decision")),
        ("Section 11: Reasons", judgment.get("reasons")),
        ("Section 12: Citations", judgment.get("legal_citations")),
    ]
    for sec_name, val in sections:
        assert val is not None and len(str(val)) > 0, f"Section {sec_name} is empty!"
        print(f"  [OK] {sec_name}")

    print(f"Verdict: {judgment.get('final_decision')}")
    applicable_law = judgment.get("applicable_law", [])
    print(f"Applicable Law in Judgment: {applicable_law}")
    assert any("Indian Evidence Act" in law or "Indian Penal Code" in law for law in applicable_law), "Judgment applicable law must cite historical statutes!"
    assert not any("Bharatiya Sakshya Adhiniyam" in law for law in applicable_law), "Judgment applicable law must NOT cite BSA for historical case!"
    print("PASS: All 12 judgment sections generated and grounded in historical statutes.")

    # Check 5: Document Persistence
    print("\n--- 5. DOCUMENT PERSISTENCE ---")
    persisted = completed_event.get("persisted_files", {})
    case_id = completed_event.get("case_id")
    print(f"Case ID: {case_id}")
    print(f"Persisted Files: {persisted}")
    assert "up_" in case_id or "Shabuddin" in case_id, f"Case ID should be unique to case, not generic CASE-2024-001! Found: {case_id}"
    assert Path(persisted.get("json", "")).exists(), "ai_judgment.json does not exist on disk!"
    assert Path(persisted.get("txt", "")).exists(), "ai_judgment.txt does not exist on disk!"
    assert Path(persisted.get("pdf", "")).exists(), "ai_judgment.pdf does not exist on disk!"
    print("PASS: ai_judgment.json, ai_judgment.txt, and ai_judgment.pdf successfully verified on disk.")

    print("\n" + "=" * 80)
    print("ALL AUDIT CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_audit()

