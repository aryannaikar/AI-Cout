# AI Court of India - Comprehensive Project Structure & Codebase Map

> **Quick Note for Developers & AI Assistants**:
> This document maps every directory, module, class, method, API endpoint, frontend renderer, and test in **AI-Court-of-India**.
> Refer to this file whenever you need to find where a specific capability, data model, or agent logic resides.

---

## 1. System Architecture & Core Protocols

```mermaid
flowchart TD
    subgraph Client [User Interface - React + Vite]
        Upload[Case Packet PDF Upload]
        LiveStream[SSE Real-Time Courtroom Stream]
        Timeline[Courtroom Timeline Progression]
        AuditView[Post-Trial Comparison Modal]
    end

    subgraph API [FastAPI Backend - port 8000]
        CRoutes["/api/court/* Upload & Stream"]
        AuditRoutes["/api/court/cases/{id}/compare"]
    end

    subgraph Engine [LangGraph Courtroom StateGraph]
        direction TB
        CU[Case Understanding Node]
        P_Branch[Prosecutor Node + Legal & Web Research]
        D_Branch[Defense Node + Legal & Web Research]
        EvNode[Evidence Analysis Node]
        ConfNode[Conflict Detection Node]
        LiveHearing[Live Multi-Turn Hearing & Debate]
        JudgeNode[Final Judge Adjudication]
        CU --> P_Branch & D_Branch
        P_Branch & D_Branch --> EvNode --> ConfNode --> LiveHearing --> JudgeNode
    end

    subgraph LegalRAG [ChromaDB Statutory Store]
        BNS[Bharatiya Nyaya Sanhita - 2023]
        BSA[Bharatiya Sakshya Adhiniyam - 2023]
        Const[Constitution of India]
        IT[Information Technology Act - 2000]
        Rerank[Cross-Encoder Legal Reranker]
    end

    subgraph AuditEngine [Phase 5 Comparative Audit Engine]
        Comparator[JudgmentComparator]
        Scorer[8-Category Weighted Scoring Engine]
        Report[Report Generator: Markdown / JSON / PDF]
    end

    Upload --> CRoutes --> Engine
    P_Branch & D_Branch -.-> LegalRAG
    JudgeNode -.-> LegalRAG
    Engine --> LiveStream
    JudgeNode --> SavedArtifacts[backend/data/cases/{id}/output/]
    SavedArtifacts --> AuditEngine
    RealVerdict[Real Judgment / Ground Truth PDF] --> AuditRoutes --> AuditEngine
    AuditEngine --> AuditView
```

### Core Architectural Invariants:
1. **Strict Blind Evaluation (Security Isolation)**:
   - Trial materials (`case_packet.pdf`) include only pre-trial records (FIR, chargesheets, witness statements, seizure memos, forensic reports).
   - Real judgments / Ground Truth files are strictly forbidden during trial simulation. `backend/app/graph/validation.py` enforces regex and token checks (`validate_no_ground_truth_text`).
   - Real verdicts are only ever introduced post-judgment in **Phase 5** comparison.
2. **Dual Legal Era Transition (IPC/IEA vs BNS/BSA)**:
   - Incident date prior to **July 1, 2024**: Governed by IPC and IEA.
   - Incident date on or after **July 1, 2024**: Governed by BNS and BSA.
   - Transition mapped dynamically in `backend/app/services/legal_transition.py`.
3. **Multi-Model LLM Gateway**:
   - `backend/app/core/llm_provider.py` provides unified client abstraction across NVIDIA NIM, Ollama, OpenRouter, Google Gemini, and Mock clients with secure health diagnostics.

---

## 2. High-Level Quick Lookup Table

| Task / Component | Target File | Key Methods / Entities |
|---|---|---|
| **Final Judicial Verdict Logic** | `backend/app/agents/judge_agent.py` | `JudgeAgent.adjudicate()` |
| **Courtroom Graph Orchestrator** | `backend/app/graph/workflow.py` | `create_court_graph()`, `CourtWorkflow.run()`, `stream_trial()` |
| **Prosecution Case Presentation** | `backend/app/agents/prosecutor_agent.py` | `ProsecutorAgent.present_case()` |
| **Defense Case & Rights Defense** | `backend/app/agents/defense_agent.py` | `DefenseAgent.present_defense()` |
| **Live Multi-Turn Courtroom Debate** | `backend/app/agents/live_hearing_agents.py` | `LiveJudgeAgent`, `LiveProsecutorAgent`, `LiveDefenseAgent` |
| **Evidence & Chain of Custody** | `backend/app/agents/evidence_agent.py` | `EvidenceAnalysisAgent.analyze()` |
| **Contradiction & Conflict Detection**| `backend/app/agents/conflict_agent.py` | `ConflictDetectionAgent.detect_conflicts()` |
| **Statutory & Legal Research** | `backend/app/agents/legal_research_agent.py` | `LegalResearchAgent.research()` |
| **Precedent & Web Research** | `backend/app/agents/web_research_agent.py` | `WebResearchAgent.research()` |
| **FastAPI Court Routes (SSE/Upload)** | `backend/app/api/court_routes.py` | `stream_court_proceedings()`, `upload_case_packet()`, `download_judgment_artifact()` |
| **FastAPI Comparison Routes** | `backend/app/api/comparison_routes.py` | `post_trial_compare()`, `download_comparison_pdf()` |
| **Phase 5 Comparison Service** | `backend/app/comparison/service.py` | `ComparisonService.run_comparison()` |
| **8-Category Scoring Engine** | `backend/app/comparison/scoring.py` | `ScoringEngine.calculate_scores()`, `ComparisonScoringConfig` |
| **Judgment Normalization** | `backend/app/comparison/extractor.py` | `JudgmentNormalizer.normalize_real_judgment()` |
| **Legal RAG Retriever & Search** | `backend/rag/retriever.py` | `LegalRetriever.retrieve()` |
| **Legal-Aware Chunker** | `backend/rag/chunker.py` | `LegalAwareChunker.chunk()`, `chunk_legal_document()` |
| **LLM Provider Factory** | `backend/app/core/llm_provider.py` | `LLMProvider.get_client()`, `LLMConfig` |
| **Frontend Court Stream & Feed** | `frontend/src/components/CourtroomStream.tsx` | `CourtroomStream`, `CourtroomChat` |
| **Frontend Agent Speech Bubbles** | `frontend/src/components/renderers/` | `JudgeRenderer`, `ProsecutorRenderer`, `DefenseRenderer` |
| **Frontend Comparison Modal** | `frontend/src/components/ComparisonModal.tsx` | `ComparisonModal` |
| **Frontend Types Definition** | `frontend/src/types/court.ts` | `AgentMessage`, `Judgment`, `ComparisonReport` |

---

## 3. Directory Structure Tree

```text
AI-Court-of-India/
├── backend/
│   ├── app/
│   │   ├── main.py                         # FastAPI App root, CORS, router mounting, health checks
│   │   ├── agents/                         # Autonomous courtroom agents
│   │   │   ├── case_agent.py               # CaseUnderstandingAgent
│   │   │   ├── prosecutor_agent.py         # ProsecutorAgent
│   │   │   ├── defense_agent.py            # DefenseAgent
│   │   │   ├── legal_research_agent.py     # LegalResearchAgent (Statutory queries)
│   │   │   ├── web_research_agent.py       # WebResearchAgent (Precedents / online research)
│   │   │   ├── evidence_agent.py           # EvidenceAnalysisAgent (Forensics & chain of custody)
│   │   │   ├── conflict_agent.py           # ConflictDetectionAgent (Contradiction mapping)
│   │   │   ├── live_hearing_agents.py      # Real-time multi-agent courtroom debate
│   │   │   └── judge_agent.py              # Final JudgeAgent (Synthesis & verdict)
│   │   ├── api/
│   │   │   ├── court_routes.py             # Upload case packet, SSE stream, run trial, download artifacts
│   │   │   └── comparison_routes.py        # Post-trial comparison, report export (TXT, JSON, PDF)
│   │   ├── comparison/                     # Phase 5 Comparative Audit & Scoring Engine
│   │   │   ├── comparator.py               # Deep structural comparator (AI vs Human Judge)
│   │   │   ├── errors.py                   # Exception taxonomy for comparison
│   │   │   ├── extractor.py                # JudgmentNormalizer for diverse judgment formats
│   │   │   ├── loaders.py                  # ComparisonDocumentLoader (Safe PDF/JSON loading)
│   │   │   ├── report_generator.py         # Formatted text, markdown, and PDF reporting
│   │   │   ├── schemas.py                  # Pydantic comparison models & score metrics
│   │   │   ├── scoring.py                  # 8-dimensional weighted scoring engine
│   │   │   └── service.py                  # ComparisonService facade
│   │   ├── core/
│   │   │   └── llm_provider.py             # Multi-provider client abstraction (NVIDIA/Ollama/Gemini)
│   │   ├── graph/
│   │   │   ├── nodes.py                    # LangGraph node execution handlers
│   │   │   ├── state.py                    # CourtState TypedDict, ExecutionLogEntry, JudgeInput
│   │   │   ├── validation.py               # Blind evaluation validators and ground-truth shields
│   │   │   └── workflow.py                 # CourtWorkflow LangGraph definition
│   │   ├── ingestion/
│   │   │   ├── evidence_extractor.py       # Structured evidence extractor
│   │   │   └── evidence_loader.py          # EvidencePDFLoader with security validation
│   │   ├── models/                         # Pydantic schemas for court entities
│   │   │   ├── case_models.py              # StructuredCase, Party, Charge, WitnessStatement
│   │   │   ├── conflict_models.py          # ConflictReport, Conflict, ConflictSeverity
│   │   │   ├── evidence_models.py          # EvidenceAnalysisReport, EvidenceItemAnalysis
│   │   │   ├── evidence_package_models.py  # EvidencePackage comprehensive case packet
│   │   │   ├── execution_models.py         # ExecutionReport stage timings & token tracking
│   │   │   ├── judgment_models.py          # Judgment, JudicialIssueAnalysis, ArgumentComponent
│   │   │   └── legal_models.py             # LegalResearchResult, WebResearchResult
│   │   ├── rag/                            # Forwarders to backend/rag for backward compatibility
│   │   └── services/
│   │       ├── judgment_writer.py          # Persists JSON and Markdown judgment artifacts
│   │       ├── legal_transition.py         # IPC <-> BNS era transition service
│   │       ├── llm_service.py              # Standard LLM prompt execution helper
│   │       └── web_search_service.py       # External search service
│   ├── rag/                                # Core Legal RAG implementation
│   │   ├── chunker.py                      # LegalAwareChunker (Sections, Subsections, Provisos)
│   │   ├── cleaner.py                      # Legal text normalization and artifact cleaner
│   │   ├── config.py                       # RAG configuration parameters and root discovery
│   │   ├── embeddings.py                   # EmbeddingModel (SentenceTransformers)
│   │   ├── ingest.py                       # Batch ingestion pipeline for statutory corpora
│   │   ├── loader.py                       # PDFLoader for Indian legal statutes
│   │   ├── query.py                        # Standalone query utility
│   │   ├── query_processor.py              # Legal query expansion & acronym detection
│   │   ├── reranker.py                     # CrossEncoder legal relevance reranker
│   │   ├── retriever.py                    # LegalRetriever (dense hybrid search)
│   │   └── vector_store.py                 # LegalVectorStore ChromaDB wrapper
│   ├── requirements.txt                    # Python dependencies
│   └── scripts/                            # Ingestion and test runner scripts
├── frontend/                               # React + Vite + Tailwind/Modern CSS UI
│   ├── src/
│   │   ├── App.tsx                         # Main UI hub & state coordinator
│   │   ├── types/court.ts                  # TypeScript types matching backend schemas
│   │   ├── components/
│   │   │   ├── CaseUpload.tsx              # Drag-and-drop PDF Case Packet uploader
│   │   │   ├── CourtroomStream.tsx         # SSE live feed & state orchestrator
│   │   │   ├── CourtroomTimeline.tsx       # Interactive step progress tracker
│   │   │   ├── CourtroomChat.tsx           # Multi-agent courtroom conversation feed
│   │   │   ├── CourtroomChatBubble.tsx     # Message bubble with badges and renderers
│   │   │   ├── JudgmentModal.tsx           # Formal judgment document view & export
│   │   │   ├── ComparisonModal.tsx         # AI vs Real Judge comparison report modal
│   │   │   ├── ResearchChamber.tsx         # Legal RAG & web search inspect tab
│   │   │   ├── Header.tsx                  # App bar with active LLM status indicator
│   │   │   └── renderers/                  # Agent-specific speech card renderers
│   │   │       ├── CaseUnderstandingRenderer.tsx
│   │   │       ├── ProsecutorRenderer.tsx
│   │   │       ├── DefenseRenderer.tsx
│   │   │       ├── LegalResearchRenderer.tsx
│   │   │       ├── WebResearchRenderer.tsx
│   │   │       ├── EvidenceAnalysisRenderer.tsx
│   │   │       ├── ConflictDetectionRenderer.tsx
│   │   │       ├── JudgeRenderer.tsx
│   │   │       └── RawDataCollapsible.tsx
│   │   └── utils/
│   │       ├── courtroomChatFormatters.ts  # Extracts snippet previews from payloads
│   │       └── exportCourtRecord.ts        # Exports trial record as JSON / Markdown
├── data/                                   # File storage
│   ├── cases/                              # Uploaded case packets and saved verdicts
│   ├── legal_corpus/                       # Raw source statutory PDFs
│   └── vectorstore/                        # ChromaDB persistent vector storage
├── legal_documents/                        # Benchmark real cases & condensed transcripts
├── export_engine/                          # Pre-compiled judicial reasoning corpus & embeddings
├── scripts/                                # Utility and benchmark scripts
└── tests/                                  # Pytest suites categorized by Phase 1-5
```

---

## 4. Backend Core & Server (`backend/app/`)

### 4.1 API Endpoints (`backend/app/api/`)

#### `backend/app/api/court_routes.py`
- **Prefix**: `/api/court`
- **Endpoints**:
  - `POST /api/court/upload` -> `upload_case_packet(file: UploadFile, background_tasks: BackgroundTasks)`: Accepts and validates pre-trial Case Packet PDF; generates unique `upload_id` and prepares workspace.
  - `POST /api/court/stream` -> `stream_court_proceedings(request: StreamCourtRequest)`: Server-Sent Events (SSE) streaming endpoint executing the LangGraph courtroom workflow in real time.
  - `POST /api/court/run` -> `run_court_synchronous(request: StreamCourtRequest)`: Executes trial synchronously and returns full `CourtState` once completed.
  - `GET /api/court/cases/{case_id}/download/{format_type}` -> `download_judgment_artifact(case_id: str, format_type: str)`: Downloads generated judicial decision in Markdown, JSON, or PDF format.
  - `GET /api/court/cases/{case_id}/judgment` -> `get_persisted_judgment(case_id: str)`: Fetches saved JSON judgment object for a completed case.

#### `backend/app/api/comparison_routes.py`
- **Prefix**: `/api/court` and `/api`
- **Endpoints**:
  - `POST /api/court/cases/{case_id}/compare` -> `post_trial_compare(case_id: str, file: UploadFile, ...)`: Post-trial comparison of generated AI Judgment against uploaded real High Court / Supreme Court judgment.
  - `POST /api/comparison/manual` -> `manual_standalone_compare(ai_judgment_file: UploadFile, real_judgment_file: UploadFile)`: Standalone comparative audit between two arbitrary judgment files.
  - `GET /api/court/cases/{case_id}/comparison/download/txt` -> `download_comparison_txt(case_id: str)`: Exports comparison report in text format.
  - `GET /api/court/cases/{case_id}/comparison/download/json` -> `download_comparison_json(case_id: str)`: Exports comparison report in structured JSON format.
  - `GET /api/court/cases/{case_id}/comparison/download/pdf` -> `download_comparison_pdf(case_id: str)`: Exports comparison report in styled PDF format.

#### `backend/app/main.py`
- **Purpose**: FastAPI application factory, CORS configuration, and server health check diagnostics.
- **Endpoints**:
  - `GET /api/health` -> `health_check()`: Basic service uptime check.
  - `GET /api/health/llm` -> `llm_health_check()`: Verifies connection to the active LLM brain without leaking credentials.

---

### 4.2 Courtroom Multi-Agent System (`backend/app/agents/`)

#### `backend/app/agents/case_agent.py`
*Case Understanding Agent for AI Court of India.*

- **Class `CaseUnderstandingAgent`** (*Ingests and parses Case_Packet.pdf into a strongly-typed StructuredCase object.*)
  - `__init__(llm_service)`
  - `_validate_case_file(file_path)`: Enforce strict isolation: prevent loading verdict or judgment files.
  - `process_case_packet(case_packet_path)`: Extract and structure the contents of a Case_Packet.pdf file.
  - `parse_case_text(case_text, source_filename)`: Parse raw case packet text into a StructuredCase model.
  - `_heuristic_parse(text, source_filename)`: Heuristic extractor providing robust fallback data for deterministic offline execution.

#### `backend/app/agents/prosecutor_agent.py`
*Prosecutor Agent for AI Court of India.*

- **Class `ProsecutorAgent`** (*Simulates the State / Prosecution counsel.*)
  - `__init__(llm_service)`
  - `build_case(case, evidence_report, legal_research, web_research)`: Synthesize the complete adversarial prosecution submission.

#### `backend/app/agents/defense_agent.py`
*Defense Agent for AI Court of India.*

- **Class `DefenseAgent`** (*Simulates the Defense Counsel for the accused.*)
  - `__init__(llm_service)`
  - `build_defense(case, prosecution, evidence_report, legal_research, web_research)`: Synthesize the complete adversarial defense submission.

#### `backend/app/agents/legal_research_agent.py`
*Source-faithful, date-aware legal research over the persistent legal corpus.*

- **Class `LegalResearchAgent`** (*Retrieve only legal sources compatible with the case's applicable regime.*)
  - `__init__(side, retriever)`
  - `research(question, top_k, act_filter, is_historical, case, regime)`: Return traceable provisions without relabelling one statute as another.
  - `_to_provision(result, question, regime)`
  - `_empty_result(question, regime, limitation)`
  - `_derive_relevance(act_name, provision, question)`
  - `_extract_legal_ingredients(text)`
  - `_synthesize_findings(question, provisions)`

#### `backend/app/agents/web_research_agent.py`
*Web Research Agent for AI Court of India.*

- **Class `WebResearchAgent`** (*Conducts external legal research on judicial precedents, recent amendments,*)
  - `__init__(side, search_service)`
  - `validate_query(query)`: Validate that a web query complies with blind evaluation rules.
  - `research(question, max_sources, force_search)`: Research external legal authorities relevant to the case.

#### `backend/app/agents/evidence_agent.py`
*Evidence Analysis Agent for AI Court of India.*

- **Class `EvidenceAnalysisAgent`** (*Evaluates evidence contained in the case packet or standardized EvidencePackage.*)
  - `__init__(llm_service)`
  - `analyze_evidence(case, evidence_package)`: Analyze all exhibits and witness testimony in the case packet and/or EvidencePackage.
  - `analyze_evidence_package(package, case)`: Perform deep objective evidentiary evaluation on a standardized EvidencePackage.
  - `_map_evidence_type(raw_type)`

#### `backend/app/agents/conflict_agent.py`
*Conflict Detection Agent for AI Court of India.*

- **Class `ConflictDetectionAgent`** (*Identifies factual, evidentiary, and testimonial contradictions across the case record.*)
  - `__init__(llm_service)`
  - `detect_conflicts(case, evidence_report)`: Scan case facts and evidence to detect all irreconcilable inconsistencies.

#### `backend/app/agents/live_hearing_agents.py`
*Live Hearing Agents for AI Court of India.*

- **Class `JudgeAction`**
- **Class `LawyerAction`**
- **Class `LiveJudgeAgent`**
  - `__init__(llm_service)`
  - `orchestrate(case, prosecution, defense, transcript, active_issue, turn_in_issue, issue_index, concluded_issues)`
- **Class `LiveProsecutorAgent`**
  - `__init__(llm_service)`
  - `argue(case, prosecution, transcript, active_issue, turn_in_issue, previous_speaker, previous_message, unresolved_argument)`
- **Class `LiveDefenseAgent`**
  - `__init__(llm_service)`
  - `argue(case, defense, transcript, active_issue, turn_in_issue, previous_speaker, previous_message, unresolved_argument)`
- **Class `LiveEvidenceAgent`**
  - `__init__(llm_service)`
  - `clarify(evidence_analysis, transcript, active_issue)`
- **Class `LiveConflictAgent`**
  - `__init__(llm_service)`
  - `clarify(conflict_report, transcript, active_issue)`
- **Function `extract_grounded_case_context(case, prosecution, defense)`**: Extracts factual matrix and strict evidentiary bounds directly from case materials.
- **Function `get_case_issues(case)`**: Returns clean, case-grounded issues, strictly filtering out ungrounded electronic records.
- **Function `validate_clean_message(msg, fallback)`**: Ensures response is never empty, never 'Proceed.', and never contains newborn child hallucinations.

#### `backend/app/agents/judge_agent.py`
*DeepSeek-backed judicial reasoning for AI Court of India.*

- **Class `JudgeAgent`** (*Render an independent, evidence-grounded judgment using configured OpenRouter DeepSeek.*)
  - `__init__(llm_service)`
  - `_validate_blindness(case, prosecution_case, defense_case)`: Reject explicit evaluation labels before any case data reaches the provider.
  - `_collect_sources(prosecution_legal_research, defense_legal_research, web_researches, case)`
  - `_validate_output(judgment, case, dossier)`: Apply deterministic consistency, evidence-reference, and citation guardrails.
  - `adjudicate(case, prosecution_case, defense_case, evidence_report, conflict_report, evidence_package, prosecution_legal_research, defense_legal_research, web_research, prosecution_web_research, defense_web_research)`: Ask the configured DeepSeek model for one validated 12-section judgment.

---

### 4.3 LangGraph Orchestrator & State (`backend/app/graph/`)

#### `backend/app/graph/workflow.py`
*LangGraph Courtroom Workflow Compilation and Execution Engine.*

- **Class `CourtWorkflow`** (*High-level orchestrator wrapping the compiled LangGraph courtroom graph.*)
  - `__init__()`
  - `run(case_packet, output_dir)`: Execute the full trial proceeding, persist artifacts, and return complete state.
  - `stream_trial(case_packet, output_dir)`: Execute the courtroom proceeding progressively, yielding real-time SSE events
- **Function `create_court_graph()`**: Build the uncompiled StateGraph for the courtroom proceedings.
- **Function `_format_agent_payload(node_name, update)`**
- **Function `_workflow_case_id(case_packet, case_analysis)`**: Keep uploaded-case IDs stable across persistence, SSE, and API lookups.
- **Function `run_court(case_packet, config, output_dir)`**: Clean entry point to execute the complete AI Court of India courtroom proceedings.

#### `backend/app/graph/state.py`
*CourtState definition and schemas for AI Court of India LangGraph Orchestration.*

- **Class `CourtError`** (*Represents an explicit error that occurred in a workflow node.*)
- **Class `ExecutionLogEntry`** (*Audit log item tracking the execution of each node in the courtroom graph.*)
- **Class `JudgeInput`** (*Sanitized, structured dossier provided to the Judge Agent.*)
  - `validate_security(cls, data)`
- **Class `CourtState`** (*Strongly typed courtroom state for LangGraph orchestration.*)
  - `enforce_blind_evaluation(cls, data)`
  - `case_id()`
  - `status()`
  - `ai_judgment()`
  - `agent_statuses()`
  - `output_dir()`
  - `execution_time_seconds()`

#### `backend/app/graph/nodes.py`
*LangGraph Nodes for AI Court of India Courtroom Workflow.*

- **Function `case_understanding_node(state)`**: Node 1: Parses Case_Packet.pdf into a StructuredCase model.
- **Function `prosecutor_node(state)`**: Node 2: Constructs adversarial prosecution theory and argument categorization.
- **Function `prosecutor_legal_research_node(state)`**: Node 3: Conducts local statutory RAG research for prosecution using ChromaDB.
- **Function `prosecutor_web_research_node(state)`**: Node 4: Conducts external judicial precedent search for prosecution if required.
- **Function `defense_node(state)`**: Node 5: Formulates adversarial defense theory, grounds of reasonable doubt, and infirmities.
- **Function `defense_legal_research_node(state)`**: Node 6: Conducts local statutory RAG research for defense standards of proof.
- **Function `defense_web_research_node(state)`**: Node 7: Conducts external judicial precedent research for defense reasonable doubt.
- **Function `evidence_node(state)`**: Node 8: Evaluates evidentiary value, chain of custody, and corroborations.
- **Function `conflict_node(state)`**: Node 9: Detects contradictions between witness testimonies, exhibits, and competing facts.
- **Function `live_judge_node(state)`**: Node: Orchestrates the live turn-by-turn courtroom conversation.
- **Function `live_prosecutor_node(state)`**: Node: Prosecutor participates in the live turn-by-turn conversation.
- **Function `live_defense_node(state)`**: Node: Defense participates in the live turn-by-turn conversation.
- **Function `live_evidence_node(state)`**: Node: Evidence agent participates in the live turn-by-turn conversation.
- **Function `live_conflict_node(state)`**: Node: Conflict agent participates in the live turn-by-turn conversation.
- **Function `judge_node(state)`**: Node 10: Compiles sanitized JudgeInput and renders 12-section judicial verdict.

#### `backend/app/graph/validation.py`
*Validation and Security Guardrails for AI Court of India LangGraph Orchestration.*

- **Class `BlindEvaluationViolation`** (*Raised when ground truth or real verdict data is detected in the courtroom graph.*)
- **Function `_is_ground_truth_document(text)`**: Context-aware Ground Truth document detector.
- **Function `validate_case_packet_path(path_or_text)`**: Validate that a case packet path does not point to a Ground Truth Verdict file.
- **Function `validate_no_forbidden_keys(data)`**: Ensure a dictionary does not contain any forbidden ground truth keys.
- **Function `validate_no_ground_truth_text(text)`**: Ensure raw text does not contain forbidden ground truth verdict signatures.

---

### 4.4 Data Models & Schemas (`backend/app/models/`)

#### `backend/app/models/case_models.py`
*Pydantic data models for structured case representation extracted from Case_Packet.pdf.*

**Pydantic Models / Enums**:
- `Party` (BaseModel): Represents a party in the legal proceeding.
- `Charge` (BaseModel): Represents a statutory charge or allegation framed against an accused.
- `WitnessStatement` (BaseModel): Represents testimony provided by a witness during investigation or trial.
- `Exhibit` (BaseModel): Represents an evidentiary item or document marked as an exhibit in the case packet.
- `StructuredCase` (BaseModel): Complete, structured representation of a case extracted strictly from Case_Packet.pdf.

#### `backend/app/models/conflict_models.py`
*Pydantic data models for Conflict Detection in AI Court of India.*

**Pydantic Models / Enums**:
- `ConflictCategory` (str, Enum)
- `ConflictSeverity` (str, Enum)
- `Conflict` (BaseModel): Represents an unresolved contradiction or inconsistency discovered in the courtroom record.
- `ConflictReport` (BaseModel): Complete report generated by the Conflict Detection Agent.

#### `backend/app/models/evidence_models.py`
*Pydantic data models for Evidence Analysis in AI Court of India.*

**Pydantic Models / Enums**:
- `EvidenceType` (str, Enum)
- `EvidenceItemAnalysis` (BaseModel): Deep analytical evaluation of an individual piece of evidence.
- `CorroborationLink` (BaseModel): Represents mutual corroboration between two pieces of evidence or testimonies.
- `EvidenceAnalysisReport` (BaseModel): Complete analytical report generated by the Evidence Analysis Agent.

#### `backend/app/models/evidence_package_models.py`
*Standardized Evidence Representation and Schema Models for AI Court of India.*

**Pydantic Models / Enums**:
- `ClaimType` (str, Enum): Allowed categorical types for atomic testimony claims.
- `SourceReference` (BaseModel): Provenance tracking an evidentiary item back to its origin in the Evidence PDF.
- `CaseIdentification` (BaseModel): Case identification data. Missing fields are represented as None/empty, never invented.
- `ChargeAllegation` (BaseModel): Statutory charge or allegation. Does NOT determine whether charge is proved.
- `Witness` (BaseModel): Witness examined in the proceedings. Preserves exact name, role, side, and testimony facts.
- `EvidenceItem` (BaseModel): Documentary or material exhibit marked in evidence. Preserves exhibit number exactly.
- `PhysicalEvidenceItem` (BaseModel): Physical or material object seized, recovered, or produced in trial.
- `RecoveryRecord` (BaseModel): Alleged recovery under investigation. Keeps prosecution claim separate from established fact.
- `IdentificationRecord` (BaseModel): Identification proceedings (TIP, in-court, vehicle, or document). Does NOT decide reliability.
- `TestimonyClaim` (BaseModel): Atomic factual claim made in witness testimony. Strictly separates claims from facts.
- `StatementRecord` (BaseModel): Recorded statement or disclosure under investigation or inquiry.
- `ProceduralRecord` (BaseModel): Investigative or procedural action. Does NOT decide legal validity.
- `EvidenceLink` (BaseModel): Explicit relational link connecting different evidentiary nodes by their IDs.
- `ContradictionRecord` (BaseModel): Objectively detectable contradiction between two sources on record. Does NOT decide truth.
- `MissingEvidenceRecord` (BaseModel): Evidence explicitly noted on record as missing, unproduced, unproved, or unavailable.
- `EvidencePackage` (BaseModel): Complete Standardized Evidence Representation Package for AI-Court-of-India.

#### `backend/app/models/execution_models.py`
*Pydantic data models for execution reporting and trial audit in AI Court of India.*

**Pydantic Models / Enums**:
- `ExecutionReport` (BaseModel): Exhaustive execution summary of the AI Courtroom trial.

#### `backend/app/models/judgment_models.py`
*Pydantic data models for Prosecution Arguments, Defense Arguments, and the 12-section Judicial Verdict.*

**Pydantic Models / Enums**:
- `StatementType` (str, Enum): Rigorous epistemic classification required of all courtroom arguments.
- `ArgumentComponent` (BaseModel): An individual constituent proposition of a legal submission.
- `ProsecutionCase` (BaseModel): Complete adversarial case submitted by the Prosecutor Agent.
- `DefenseCase` (BaseModel): Complete adversarial defense submitted by the Defense Agent.
- `JudicialIssueAnalysis` (BaseModel): Independent analysis by the Judge of a specific issue in controversy.
- `Judgment` (BaseModel): Formal, exhaustive judicial verdict rendered by the Judge Agent.

#### `backend/app/models/legal_models.py`
*Pydantic data models for Legal Research and Web Research results in AI Court of India.*

**Pydantic Models / Enums**:
- `ApplicableProvision` (BaseModel): Represents a specific statutory provision retrieved from the local legal corpus.
- `LegalResearchResult` (BaseModel): Structured output of the Legal Research Agent (prosecution or defense side).
- `WebResearchItem` (BaseModel): Represents a single external legal source retrieved via web research.
- `WebResearchResult` (BaseModel): Structured output of the Web Research Agent.

---

### 4.5 Services & Utilities (`backend/app/services/`)

#### `backend/app/services/judgment_writer.py`
*Output persistence and document generator for AI Court of India.*

- **Class `JudgmentWriter`** (*Persists AI Courtroom judgments and execution reports to disk.*)
  - `__init__(base_output_dir)`
  - `get_case_output_dir(case_id)`: Derive case-specific output directory: data/cases/<case_id>/output/.
  - `format_judgment_text(judgment)`: Render a readable judicial judgment text containing all 12 framework sections.
  - `write_judgment_pdf(judgment_text, output_path)`: Render judgment text into a multi-page PDF document using PyMuPDF.
  - `persist_judgment(case_id, judgment, custom_output_dir)`: Persist judgment in JSON, TXT, and PDF formats.
  - `persist_execution_report(case_id, report_data, custom_output_dir)`: Save execution_report.json to disk.

#### `backend/app/services/legal_transition.py`
*Legal Transition and Historical Statute Selection Service.*

- **Function `detect_case_legal_regime(case, case_text)`**: Determine whether a case is governed by historical legislation (IPC, IEA, CrPC)
- **Function `_extract_relevant_legal_date(text)`**: Return a date tied to the offence/incident/FIR, never a judgment date.
- **Function `_parse_indian_date(raw)`**
- **Function `get_defense_legal_research_query(case)`**: Generate statute-aware defense research query respecting historical transition.
- **Function `get_prosecutor_legal_research_query(case)`**: Generate statute-aware prosecution research query respecting historical transition.
- **Function `map_provision_to_historical(act_name, section_or_article)`**: Map modern BNS/BSA provision to corresponding historical IPC/IEA provision

#### `backend/app/services/llm_service.py`
*Configurable LLM Service for AI Court of India.*

- **Class `LLMService`** (*Unified LLM Service wrapper utilized by courtroom agents and Judicial Bench.*)
  - `__init__(provider, model_name, api_key)`
  - `get_client()`: Obtain underlying client from LLMProvider.
  - `generate_text(prompt, system_prompt)`: Generate unstructured text completion via configured LLM provider.
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`: Generate structured output adhering to a Pydantic schema via configured LLM provider.
  - `_generate_mock_instance(schema)`

#### `backend/app/services/web_search_service.py`
*Web search service with strict blind-evaluation guardrails for AI Court of India.*

- **Class `WebSearchService`** (*Search service for external legal authorities and amendments.*)
  - `__init__(provider)`
  - `validate_query_blindness(query)`: Enforce strict blind evaluation: prevent searching for the real-world verdict.
  - `search_legal(query, max_results, side)`: Perform a guarded legal web search.
  - `_get_authoritative_mock_results(query, side, max_results)`

---

### 4.6 Phase 5 Comparative Audit Engine (`backend/app/comparison/`)

#### `backend/app/comparison/service.py`
*Comparison Service for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `ComparisonService`** (*Central service for evaluating AI Court judgments against authoritative Real Court decisions.*)
  - `__init__(base_cases_dir, scoring_weights)`
  - `_identity_tokens(value)`: Normalize identifiers while removing generic caption and court words.
  - `_validate_case_identity(cls, ai, real)`: Reject only a conflict in a reliable shared case identifier.
  - `_normalise_identifier(value)`
  - `_run_comparison(ai_input, real_input, packet_text, case_id, mode, case_title, presiding_court, date_of_decision)`: Shared comparison logic for both modes — purely in-memory.
  - `compare_post_trial(case_id, real_judgment_source, ai_judgment_source, case_packet_source)`: Post-Trial Comparison mode.
  - `compare_manual(ai_judgment_source, real_judgment_source, case_packet_source, case_id)`: Manual/standalone comparison mode.

#### `backend/app/comparison/comparator.py`
*Comprehensive Judgment Comparator for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `JudgmentComparator`** (*Substantive legal and reasoning comparator.*)
  - `__init__(case_packet_context)`
  - `compare(ai_norm, real_norm)`
  - `_normalize_legal_concept_text(text)`: Normalize legal phrases, OCR currency artifacts, and inflected word forms.
  - `_extract_concept_tokens(cls, text)`: Extract stemmed legal conceptual roots from a proposition.
  - `_compare_verdict(ai, real, errors)`
  - `_compare_issues(ai, real, errors, missing, unrelated)`
  - `_compare_facts(ai, real, errors, missing, unrelated)`
  - `_fact_tokens(text)`
  - `_fact_similarity(cls, first, second)`
  - `_extract_section_number(statute_text)`: Extract section number from statute text, excluding enactment years (e.g. 1860, 2023).
  - `_compare_charges(ai, real, errors, missing, unrelated)`
  - `_same_person(first, second)`
  - `_compare_witnesses(ai, real, errors, missing)`
  - `_compare_evidence(ai, real, errors, missing, unrelated)`
  - `_evidence_assessment_polarity(text)`
  - `_compare_legal_provisions(ai, real, errors, missing, unrelated)`
  - `_compare_reasoning(ai, real, errors, missing)`: Compare source-derived reasoning propositions without benchmark-specific templates.
  - `_compare_findings(ai, real, errors)`
  - `_charge_outcome(text)`: Return only an explicit final charge disposition, never an ingredient result.
  - `_compare_final_order(ai, real, errors)`

#### `backend/app/comparison/extractor.py`
*Judgment Extractor and Normalizer for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `JudgmentNormalizer`** (*Transforms heterogeneous judgment representations into a canonical NormalizedJudgment.*)
  - `normalize_ai_judgment(cls, ai_input)`: Normalize an AI Judgment (Pydantic model, dictionary, or formatted string).
  - `normalize_real_judgment(cls, real_input)`: Normalize a Real Court Judgment (structured dictionary or raw text from PDF/TXT).
  - `_clean_text_and_detect_summary(cls, text)`: Separate main substantive judgment from evaluation/comparison controls.
  - `_normalize_from_judgment_model(cls, j)`: Convert an existing AI Judgment Pydantic model into NormalizedJudgment.
  - `_normalize_from_text(cls, text, is_ai)`: Parse raw legal judgment text or ground truth summary into NormalizedJudgment.
  - `_extract_explicit_charge_finding(cls, text, statute)`: Extract a disposition only when it is explicitly attached to a charge reference.
  - `_normalize_from_dict(cls, data)`: Handle loosely structured dictionary representation.
  - `_determine_verdict_with_explanation(cls, text)`: Classify operative verdict from judicial outcome string and document the normalization rationale.
  - `_determine_verdict(cls, text)`: Classify operative verdict from judicial outcome string.
  - `_classify_statute_era(cls, text)`: Detect whether statutory reference belongs to historical IPC/CrPC or modern BNS/BNSS.
  - `_extract_case_title(cls, text)`: Extract case title from heading or header lines.
  - `_extract_case_number(cls, text)`: Extract court appeal or case number.
  - `_extract_court_name(cls, text)`: Extract court name from standard header formulas or pipe banners.
  - `_extract_date(cls, text)`: Extract judgment decision date.
  - `_extract_parties_from_title(cls, title)`: Parse party names from formal caption.
  - `_is_footer_or_metadata(cls, text_block)`: Check whether candidate text is actually footer/comparison metadata rather than an operative order.
  - `_extract_verdict_and_order(cls, text)`: Extract operative outcome, original source snippet, final order text, and normalization explanation.
  - `_extract_charges(cls, text)`: Extract statutory charges and distinguish procedural history & accused applicability.
  - `_extract_issues(cls, text, eval_block)`: Extract legal issues and points for determination.
  - `_extract_witnesses_from_text(cls, text)`: Extract witnesses (PW-1, DW-1, etc.) and their substantive testimonies.
  - `_extract_evidence_from_text(cls, text)`: Extract exhibits and documentary/physical evidence items.
  - `_is_non_fact_header_or_order(cls, text_line)`: Filter out titles, section headers, legal provisions, and operative verdict/order statements from facts.
  - `_extract_facts_from_text(cls, text)`: Extract factual propositions and classify their epistemic type.
  - `_classify_epistemic_statement(cls, stmt)`: Classify a legal proposition into FACT, EVIDENCE, CLAIM, INFERENCE, or LEGAL_CONCLUSION.
  - `_extract_provisions(cls, text)`: Extract legal acts and sections cited.
  - `_extract_chains_of_reasoning(cls, reasons_text)`: Extract logical inference steps and distinct proposition chains.
  - `_extract_reasoning_structure(cls, text, eval_block)`: Extract ratio decidendi and assessment capabilities.
  - `_extract_arguments(cls, text, side)`: Extract submissions by prosecution or defense.

#### `backend/app/comparison/loaders.py`
*Document and artifact loaders for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `ComparisonDocumentLoader`** (*Safely loads documents for comparison from filesystem paths, raw text,*)
  - `extract_text_from_pdf_bytes(cls, pdf_bytes)`: Extract all textual content from a PDF byte array using PyMuPDF.
  - `extract_text_from_pdf_path(cls, pdf_path)`: Extract all textual content from a PDF file on disk.
  - `load_ai_judgment(cls, source)`: Load an AI Judgment.
  - `load_real_judgment(cls, source)`: Load a Real Court Judgment / Ground Truth.
  - `load_case_packet(cls, source)`: Load optional supporting Case Packet context (PDF or TXT).

#### `backend/app/comparison/scoring.py`
*Configurable Scoring Engine for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `ComparisonScoringConfig`** (*Fixed Phase 5 core benchmark weights; diagnostic scores are not weighted.*)
  - `get_weights(cls, custom_weights)`: Return the exact benchmark weights; caller overrides cannot change the rubric.
- **Class `ScoringEngine`** (*Calculates dimension scores and computes balanced, non-verdict-dominated overall score.*)
  - `__init__(custom_weights)`
  - `calculate_scores(verdict_alignment, issue_alignment, factual_accuracy, charge_alignment, witness_alignment, evidence_alignment, legal_alignment, reasoning_alignment, finding_alignment, final_order_alignment, assessability)`: Compute weighted overall score, separating pure verdict from substantive legal quality.

#### `backend/app/comparison/report_generator.py`
*Comparison Report Generator for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `ComparisonReportGenerator`** (*Renders structured comparison reports across JSON, TXT, and PDF formats.*)
  - `build_report(cls, comparison_id, case_id, case_title, mode, timestamp, case_information, verdict_comp, issue_comp, fact_comp, charge_comp, witness_comp, evidence_comp, legal_comp, reasoning_comp, finding_comp, order_comp, scores, major_errors, missing_points, unrelated_points)`: Construct the complete 17-section ComparisonReport instance.
  - `_format_status(status)`
  - `format_report_text(cls, report)`: Render the 17-section comparison report into structured plain text.
  - `write_report_pdf(cls, report_text, output_path)`: Render comparison report text into a multi-page PDF document using PyMuPDF.

#### `backend/app/comparison/schemas.py`
*Pydantic data models for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `EpistemicType`** (*Rigorous categorization of assertions into distinct epistemic levels.*)
- **Class `StatuteEra`** (*Distinguishes between historical and modern Indian criminal codifications.*)
- **Class `OperativeVerdict`** (*Standardized classification of operative judicial verdicts.*)
- **Class `ComparisonCategoryStatus`** (*Standardized statuses for individual comparison categories.*)
- **Class `NormalizedParty`** (*Case parties identification.*)
- **Class `NormalizedWitness`** (*Witness deposition and credibility profile.*)
- **Class `NormalizedEvidenceItem`** (*Exhibits and evidentiary articles considered by the court.*)
- **Class `NormalizedCharge`** (*Alleged offence and statutory provisions.*)
- **Class `NormalizedFact`** (*Material fact evaluated in the judgment.*)
- **Class `NormalizedIssue`** (*Point or question framed for judicial determination.*)
- **Class `NormalizedReasoning`** (*Detailed structure of judicial ratio decidendi and chains of reasoning.*)
- **Class `NormalizedJudgment`** (*Common normalized intermediate representation capturing all 18 required elements:*)
- **Class `ComparisonErrorDetail`** (*Specific detected discrepancy or hallucination in the AI judgment.*)
- **Class `VerdictComparisonResult`** (*Evaluation of operative outcome alignment.*)
- **Class `IssueComparisonResult`** (*Evaluation of issues framed and addressed.*)
- **Class `FactualComparisonResult`** (*Evaluation of factual accuracy and epistemic classification.*)
- **Class `ChargeComparisonResult`** (*Evaluation of statutory charge alignment and historical applicability.*)
- **Class `WitnessComparisonResult`** (*Evaluation of witness appreciation and substance of testimony.*)
- **Class `EvidenceComparisonResult`** (*Evaluation of documentary, physical, and recovery evidence.*)
- **Class `LegalProvisionComparisonResult`** (*Evaluation of statutory provisions, Acts, and rules cited.*)
- **Class `ReasoningThemeComparison`** (*Evaluation of an individual judicial reasoning theme.*)
- **Class `LegalReasoningComparisonResult`** (*Evaluation of ratio decidendi and chains of logical inference.*)
- **Class `FindingComparisonResult`** (*Evaluation of findings on each charge and major issue.*)
- **Class `FinalOrderComparisonResult`** (*Evaluation of final operative order independently from reasoning.*)
- **Class `ComparisonScores`** (*Comprehensive score breakdown and weighted overall calculation.*)
- **Class `ComparisonReport`** (*Formal structured 17-section report comparing AI Court Judgment vs Real Court Judgment.*)

#### `backend/app/comparison/errors.py`
*Error definitions for Phase 5 — AI Court Judgment Comparison Engine.*

- **Class `ComparisonError`** (*Base exception for all comparison engine errors.*)
- **Class `AIJudgmentNotFoundError`** (*Raised when an AI Judgment file or object is missing for a case.*)
- **Class `RealJudgmentNotFoundError`** (*Raised when an authoritative Real Court Judgment is missing.*)
- **Class `InvalidJudgmentFormatError`** (*Raised when an uploaded document cannot be parsed into a judgment representation.*)
- **Class `CaseIdentityMismatchError`** (*Raised when the two submitted judgments contain conflicting case identifiers.*)
- **Class `GroundTruthSecurityViolation`** (*Raised when Ground Truth / Real Court Judgment is illegally injected into the courtroom graph.*)

---

### 4.7 Ingestion & PDF Parsers (`backend/app/ingestion/`)

#### `backend/app/ingestion/evidence_loader.py`
*Standardized Evidence PDF Loader for AI Court of India.*

- **Class `MalformedEvidencePDFError`** (*Raised when an Evidence PDF cannot be read or contains no extractable text.*)
- **Class `GroundTruthLeakageError`** (*Raised when an evaluation Ground Truth or Real Verdict document is detected.*)
- **Class `EvidencePDFLoader`** (*Loads and validates Standardized Evidence PDFs page by page.*)
  - `validate_document_security(path_or_name, full_text)`: Validate that the document is not an evaluation Ground Truth verdict.
  - `load_pdf(pdf_path)`: Extract pages from an Evidence PDF.
  - `load_text(text, source_filename)`: Parse raw text into PDFPage representations (for text-based or test fixtures).

#### `backend/app/ingestion/evidence_extractor.py`
*Standardized Evidence Extractor for AI Court of India.*

- **Class `EvidenceExtractor`** (*Modular, flexible extractor that parses PDF pages into an EvidencePackage.*)
  - `extract(pages, source_filename)`: Extract complete EvidencePackage from loaded pages.
  - `_extract_case_identification(pages, source_file)`
  - `_extract_charges(pages, source_file)`
  - `_extract_witnesses(pages, source_file)`
  - `_extract_exhibits(pages, source_file)`
  - `_classify_evidence_type(desc)`
  - `_extract_physical_evidence(pages, exhibits, source_file)`
  - `_extract_recoveries(pages, exhibits, source_file)`
  - `_extract_identifications(pages, exhibits, source_file)`
  - `_extract_testimony_claims(pages, pros_witnesses, def_witnesses, source_file)`
  - `_extract_statements(pages, exhibits, source_file)`
  - `_extract_procedural_evidence(pages, source_file)`
  - `_build_evidence_linkages(pros_witnesses, def_witnesses, exhibits, recoveries, identifications, charges)`
  - `_extract_contradictions(pages, exhibits, witnesses, source_file)`
  - `_extract_missing_evidence(pages, source_file)`

### 4.8 Core LLM Providers (`backend/app/core/`)

#### `backend/app/core/llm_provider.py`
*Centralized LLM Provider Architecture for AI Court of India.*

- **Class `LLMConfig`** (*Centralized configuration resolved from environment variables.*)
  - `provider(cls)`
  - `ollama_base_url(cls)`
  - `ollama_model(cls)`
  - `nvidia_api_key(cls)`
  - `nvidia_base_url(cls)`
  - `nvidia_model(cls)`
  - `gemini_api_key(cls)`
  - `gemini_model(cls)`
  - `openrouter_api_key(cls)`
  - `openrouter_base_url(cls)`
  - `openrouter_model(cls)`
- **Class `BaseLLMClient`** (*Interface implemented by concrete LLM providers.*)
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
  - `health_check()`
- **Class `OllamaLLMClient`** (*Ollama Local LLM Provider.*)
  - `__init__(base_url, model)`
  - `health_check()`: Check Ollama daemon connectivity and model availability.
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
- **Class `NvidiaLLMClient`** (*NVIDIA API (NIM) Cloud LLM Provider.*)
  - `__init__(api_key, base_url, model)`
  - `health_check()`: Check NVIDIA NIM API reachability and authentication.
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
- **Class `OpenRouterLLMClient`** (*OpenRouter API Cloud LLM Provider.*)
  - `__init__(api_key, base_url, model)`
  - `_headers()`
  - `get_usage_summary()`: Return audit metrics on requests and token consumption.
  - `_infer_agent_name(system_prompt, prompt)`
  - `_track_request(agent_name, usage)`
  - `health_check()`: Check OpenRouter API reachability and authentication.
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
- **Class `GeminiLLMClient`** (*Google Gemini API LLM Provider.*)
  - `__init__(api_key, model)`
  - `_build_contents(prompt, system_prompt)`: Build contents list; prepend system_prompt as a user/model exchange.
  - `health_check()`
  - `_call_with_retry(contents, max_retries, delay)`: Call Gemini with automatic retry on 503/429 (rate limit / server busy).
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
- **Class `MockLLMClient`** (*Deterministic, zero-network mock client for unit and integration testing.*)
  - `__init__()`
  - `health_check()`
  - `generate_text(prompt, system_prompt)`
  - `generate_structured(prompt, response_schema, system_prompt, fallback_data)`
  - `_generate_mock_instance(schema)`
- **Class `LLMProvider`** (*Centralized factory and registry for AI Court of India LLMs.*)
  - `set_provider(cls, provider)`: Explicitly override active provider ('ollama', 'nvidia', 'openrouter', 'gemini', 'mock').
  - `get(cls, provider)`: Get the configured LLM client.
  - `check_health(cls, provider)`: Run health check on configured LLM provider.
- **Function `get_llm(provider)`**: Convenience accessor to obtain the centralized LLM client.

---

## 5. Legal RAG & Retrieval Subsystem (`backend/rag/` & `rag/`)

> Note: `rag/` in project root and `backend/rag/` share the core retrieval engine. `backend/app/rag/` provides backward compatibility forwarders.

#### `backend/rag/retriever.py`
*Reusable Legal Retriever for future AI Court Agents.*

- **Class `RetrievalResult`** (*A grounded legal search result with statutory citation and relevance scoring.*)
  - `citation()`: Format an authoritative legal citation for court proceedings.
  - `to_dict()`: Convert to dictionary matching conceptual specification.
- **Class `LegalRetriever`** (*High-level, reusable retriever service. Future AI Court agents (Prosecutor, Defense, Judge)*)
  - `__init__(vector_store, embedding_model, top_k)`
  - `retrieve(query, top_k, act_filter)`: Retrieve the most relevant legal provisions for a given query.
  - `format_context_for_llm(results)`: Helper method to format retrieved results into a structured prompt context

#### `backend/rag/reranker.py`
*Lightweight Cross-Encoder Reranker for Legal RAG.*

- **Class `LegalReranker`** (*Uses a Cross-Encoder to re-score candidate provisions for higher semantic precision.*)
  - `__init__(model_name)`
  - `model()`
  - `rerank(query, results)`: Rerank a list of RetrievalResult objects.

#### `backend/rag/vector_store.py`
*Vector store implementation using ChromaDB for persistent legal corpus indexing.*

- **Class `LegalVectorStore`** (*ChromaDB-backed persistent vector store for the Indian Legal Corpus.*)
  - `__init__(persist_directory, collection_name)`
  - `add_chunks(chunks, embeddings, batch_size)`: Idempotently insert or update legal chunks into ChromaDB.
  - `add_documents(documents, embeddings, ids, metadatas)`: Backward-compatible raw insertion method supporting metadatas.
  - `search(query_embedding, n_results, where)`: Perform vector similarity search.
  - `count()`: Return total number of chunks currently stored in the collection.
  - `clear()`: Delete all documents in the collection by deleting and recreating it.
  - `get_by_id(chunk_id)`: Retrieve a specific chunk by its deterministic ID.

#### `backend/rag/chunker.py`
*Legal-aware chunking engine for Indian legal documents and the Constitution of India.*

- **Class `LegalChunk`** (*A semantic, legally-grounded chunk of text with complete statutory metadata.*)
  - `to_metadata()`: Convert metadata to a ChromaDB-compliant dictionary (str, int, float, bool only).
- **Class `LegalAwareChunker`** (*Intelligent legal chunker that splits acts and constitution into meaningful*)
  - `__init__(max_chunk_size, chunk_overlap)`
  - `chunk_document(document)`: Main entrypoint: split a LegalDocument into structured legal chunks.
  - `_chunk_constitution(doc)`: Chunk the Constitution of India into Articles, Parts, and Preamble.
  - `_chunk_act(doc)`: Chunk an Act (BNS, BSA, IT Act) into Sections, Sub-sections, Chapters, and Parts.
  - `_subchunk_legal_provision(act_name, short_name, provision_label, section_num, article_num, title, part, chapter, text, parent_id, page_start, page_end, source_file, year, default_type)`: If a section or article fits comfortably in max_chunk_size, return it as a single chunk.
  - `_extract_clean_lines_with_page(pages)`: Clean each page text and associate every line with its source page number.
- **Function `chunk_legal_document(text, act_name, year, source_file)`**: Backward-compatible helper returning list of dicts.

#### `backend/rag/cleaner.py`
*Text cleaning and normalization utilities for Indian legal documents.*

- **Function `clean_unicode_artifacts(text)`**: Remove unprintable characters, null bytes, and normalize unicode punctuation.
- **Function `remove_running_headers_and_footers(text)`**: Remove repetitive gazette headers, footers, and isolated page numbers.
- **Function `clean_legal_text(text)`**: Full cleaning pipeline for legal documents while preserving
- **Function `is_footnote_line(line)`**: Detect if a line is an amendment footnote or legislative citation note.

#### `backend/rag/loader.py`
*PDF loading and text extraction module for Indian legal documents.*

- **Class `PDFPage`** (*Represents a single page extracted from a PDF document.*)
- **Class `LegalDocument`** (*Represents a loaded legal document containing page-level texts and metadata.*)
  - `total_pages()`
  - `full_text()`
- **Class `PDFLoader`** (*Loads and extracts text from legal PDF documents with page-level tracking.*)
  - `_validate_security(path)`: Enforce strict isolation: never load verdict or judgment files into legal corpus.
  - `load_pdf(pdf_path)`: Extract text from a PDF page by page.
  - `load_document(pdf_path, act_name, year)`: Load a single PDF and construct a LegalDocument with metadata.
  - `load_corpus(corpus_dir)`: Load all legal documents from the legal corpus directory.
  - `_infer_metadata(path, act_name, year)`
- **Function `extract_pdf_pages(pdf_path)`**: Extract pages as list of dicts: [{'page': 1, 'text': '...'}]
- **Function `extract_pdf_text(pdf_path)`**: Extract complete text of PDF as single string.

#### `backend/rag/query_processor.py`
*Query processing for Legal RAG to extract semantic concepts and suggest acts.*

- **Class `ProcessedQuery`**
- **Class `QueryProcessor`** (*Heuristic query processor to suggest act filters based on query content.*)
  - `__init__()`
  - `process(query)`

#### `backend/rag/embeddings.py`
*Embedding model wrapper for Indian Legal RAG.*

- **Class `EmbeddingModel`** (*SentenceTransformer embedding wrapper with lazy loading, batching,*)
  - `__init__(model_name, device)`
  - `model()`: Thread-safe, shared cached SentenceTransformer model instance.
  - `clear_cache(cls)`: Clear cached model instances (primarily for testing).
  - `encode(texts, batch_size, normalize_embeddings, show_progress_bar)`: Encode list of texts into dense vectors.
  - `dimension()`: Return the embedding vector dimensionality.

#### `backend/rag/config.py`
*Configuration settings for the Legal RAG pipeline of AI Court of India.*

- **Class `RAGConfig`** (*Central configuration for Legal RAG.*)
  - `__post_init__()`
- **Function `_find_project_root()`**

#### `backend/rag/ingest.py`
*Corpus ingestion script for Indian Legal RAG.*

- **Function `run_ingestion(corpus_dir, rebuild, batch_size)`**: Execute full legal corpus ingestion.
- **Function `main()`**

#### `backend/rag/query.py`
*CLI query tool for Indian Legal RAG.*

- **Function `query_corpus(query_text, top_k, act_filter, output_json)`**: Execute a legal query and format results for display.
- **Function `main()`**

---

## 6. Frontend Web Application (`frontend/`)

The frontend is built with React 18, Vite, and TypeScript. It implements a multi-agent courtroom observation interface with SSE streaming.

### 6.1 Main Views & Modals (`frontend/src/components/`)

- **`App.tsx`** (`frontend/src/App.tsx`): Root React component managing trial state, current step, SSE stream listener, and modal triggers.
- **`CaseUpload.tsx`** (`frontend/src/components/CaseUpload.tsx`): Case Packet PDF upload component with drag-and-drop, validation check, and upload status feedback.
- **`CourtroomStream.tsx`** (`frontend/src/components/CourtroomStream.tsx`): Live courtroom proceeding view managing SSE connection, timeline status, and active speech cards.
- **`CourtroomTimeline.tsx`** (`frontend/src/components/CourtroomTimeline.tsx`): Visual step-by-step trial stage tracker (Upload -> Understanding -> Arguments -> Debate -> Verdict -> Comparison).
- **`CourtroomChat.tsx`** (`frontend/src/components/CourtroomChat.tsx`): Scrollable transcript stream displaying multi-agent interactions and arguments with chronological ordering.
- **`CourtroomChatBubble.tsx`** (`frontend/src/components/CourtroomChatBubble.tsx`): Interactive chat bubble with avatar, party badges (Prosecution/Defense/Judicial), and payload renderers.
- **`JudgmentModal.tsx`** (`frontend/src/components/JudgmentModal.tsx`): Full-screen modal displaying the formal AI Judgment, ratio decidendi, sentence/order, and download triggers.
- **`ComparisonModal.tsx`** (`frontend/src/components/ComparisonModal.tsx`): Modal displaying Phase 5 audit results, comparing AI Judgment against Real Judgment across 8 dimensions.
- **`ResearchChamber.tsx`** (`frontend/src/components/ResearchChamber.tsx`): Inspectable research drawer displaying legal statutory citations, BNS/IPC transitions, and web precedent results.
- **`Header.tsx`** (`frontend/src/components/Header.tsx`): Top navigation bar displaying active LLM Brain status badge, connection indicator, and project branding.

### 6.2 Specialized Agent Speech Renderers (`frontend/src/components/renderers/`)

- **`CaseUnderstandingRenderer.tsx`**: Renders parsed case overview, accused parties, charges, witness lists, and exhibits.
- **`ProsecutorRenderer.tsx`**: Renders prosecution claims, evidence citations, legal theories, and requested penalties.
- **`DefenseRenderer.tsx`**: Renders defense objections, cross-examination themes, reasonable doubts, and constitutional defenses.
- **`LegalResearchRenderer.tsx`**: Renders statutory sections retrieved from BNS, BSA, Constitution, or IT Act.
- **`WebResearchRenderer.tsx`**: Renders external judicial precedents, case citations, and doctrine searches.
- **`EvidenceAnalysisRenderer.tsx`**: Renders forensic analysis, exhibit corroboration matrix, and chain of custody evaluation.
- **`ConflictDetectionRenderer.tsx`**: Renders contradiction matrix with severity indicators (High/Medium/Low) across testimonies.
- **`JudgeRenderer.tsx`**: Renders the judicial summary, issue-by-issue findings, and operative decision.
- **`RawDataCollapsible.tsx`**: Collapsible utility component providing raw JSON inspection for debugging agent outputs.

### 6.3 Frontend Types & Utilities (`frontend/src/types/`, `frontend/src/utils/`)

- **`frontend/src/types/court.ts`**:
  - `AgentSide`: `'prosecution' | 'defense' | 'neutral' | 'judicial'`
  - `AgentMetadata`: Title, role, avatar, and side
  - `AgentMessage`: Message ID, agent name, payload, timestamp, status
  - `LLMBrainStatus`: Active provider, model, availability, and error details
  - `UploadedCaseInfo`: Upload ID, filename, page count, and validity
  - `JudicialIssueAnalysis`: Issue number, statement, law, submissions, and judicial finding
  - `Judgment`: Case title, court name, bench, operative verdict, reasoning, and final order
- **`frontend/src/utils/courtroomChatFormatters.ts`**:
  - `formatAgentMessage()`: Converts raw LangGraph payloads into readable human-friendly text summaries.
- **`frontend/src/utils/exportCourtRecord.ts`**:
  - `exportToMarkdown()` & `exportToJSON()`: Client-side exporters saving courtroom trial records.

---

## 7. Test Suites & Quality Assurance (`tests/` & `backend/tests/`)

The project uses `pytest` with extensive unit, integration, and security regression suites:

### Root `tests/` Directory:
- **Phase 1 RAG Tests**:
  - `tests/test_loader.py`: PDF loader extraction and page-splitting.
  - `tests/test_cleaner.py`: Legal cleaner artifact and header stripping.
  - `tests/test_chunker.py`: Legal-aware chunker preserving section numbering.
  - `tests/test_embeddings.py`: Vector embeddings generation.
  - `tests/test_vector_store.py`: ChromaDB indexing and vector query.
  - `tests/test_retriever.py`: Retriever query and hybrid scoring.
  - `tests/test_security_separation.py`: Security checks verifying zero case packet leakage into RAG corpus.
- **Phase 2 Agent Tests (`tests/phase2/`)**:
  - `test_case_agent.py`: Structured case extraction tests.
  - `test_prosecutor_and_defense.py`: Adversarial argument generation tests.
  - `test_evidence_and_conflict.py`: Chain of custody and contradiction detection tests.
  - `test_research_agents.py`: Statutory retrieval and web research agents.
  - `test_judge_agent.py`: Judicial synthesis and decision generation.
- **Phase 3 LangGraph Workflow Tests (`tests/phase3/`)**:
  - `test_workflow.py`: End-to-end LangGraph state machine execution.
  - `test_nodes.py`: Individual node execution and state mutation.
  - `test_state.py`: CourtState schema compliance and immutability.
  - `test_parallel_branches.py`: Concurrent execution of Prosecutor and Defense branches.
  - `test_error_handling.py`: Graceful agent failure fallback tests.
  - `test_ground_truth_isolation.py`: Verifies real verdict text never passes through trial nodes.
- **Phase 4 Judgment Generation & Security Tests (`tests/phase4/`)**:
  - `test_ai_judgment_generation.py`: Format, structure, and legal doctrine adherence of final AI judgment.
  - `test_case_packet_validation.py`: Case packet schema and file format validation.
  - `test_output_persistence.py`: Artifact saving in `backend/data/cases/{id}/output/`.
  - `test_pipeline_isolation.py`: Security validation forbidding ground-truth keys.
  - `test_end_to_end_smoke.py`: Complete simulated pipeline smoke test.
- **Phase 5 Comparison Engine Tests (`tests/phase5/`)**:
  - `test_comparison_api.py`: FastAPI endpoints for post-trial and manual comparison.
  - `test_comparison_service_and_security.py`: ComparisonService orchestration and security barriers.
  - `test_loaders_and_normalization.py`: Loading real High Court judgments and standardizing formats.
  - `test_comparisons_and_error_detection.py`: Structural comparison logic (issues, charges, evidence, verdict).
  - `test_scoring_and_report_generation.py`: 8-category scoring formulas and report exports (TXT/JSON/PDF).
  - `test_phase5_fixes_regression.py`: Regression test suite for Phase 5 audit fixes.

---

## 8. Scripts, Datasets & Export Engine

### 8.1 Utility Scripts (`scripts/` & `backend/scripts/`)
- `scripts/evaluate_retrieval.py`: Measures RAG recall and precision against Indian legal queries.
- `scripts/generate_evidence_pdf.py`: Synthetic pre-trial case packet PDF generator for testing.
- `backend/scripts/ingest_legal_documents.py`: Ingests BNS, BSA, Constitution, and IT Act into ChromaDB.
- `backend/scripts/test_retrieval.py`: Command-line statutory query tester.
- `backend/scripts/test_pdf.py`: Quick PDF text extractor tester.

### 8.2 Datasets & Benchmark Cases
- `data/legal_corpus/`: Source PDF legal statutes (BNS, BSA, Constitution of India, IT Act).
- `legal_documents/`: Real case benchmarks and transcripts (State of Maharashtra v. Benchmark cases).
- `export_engine/AI_Court_Judicial_Reasoning_Engine_v1_FINAL/`:
  - Pre-compiled judicial reasoning corpus, patterns, and embedding matrices for advanced reasoning analysis.

---

*(Generated automatically for instant project structure and function reference)*