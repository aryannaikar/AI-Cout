export type AgentSide = "prosecution" | "defense" | "neutral" | "judicial";

export interface AgentMetadata {
  title: string;
  role: string;
  avatar: string;
  side: AgentSide;
}

export interface AgentMessage {
  id: string;
  agent: string;
  metadata: AgentMetadata;
  payload: any;
  timestamp: string;
  status: "thinking" | "completed" | "error";
}

export interface ResearchProvisionRef {
  act: string;
  short_name?: string;
  section: string;
  title?: string;
  page?: number;
  source_file?: string;
  citation?: string;
  reasoning?: string;
}

export interface WebSourceRef {
  title: string;
  url?: string;
  summary?: string;
}

export interface SideResearchContext {
  side: "prosecution" | "defense";
  legalResearchAgent?: string;
  retrievalMethod?: string;
  provisions: ResearchProvisionRef[];
  webResearchAgent?: string;
  webSources: WebSourceRef[];
  casePacketPdf?: string;
}

export interface LLMBrainStatus {
  provider: string;
  model: string;
  available: boolean;
  details?: string;
  error?: string;
}

export interface UploadedCaseInfo {
  upload_id: string;
  filename: string;
  file_size: number;
  page_count: number;
  valid: boolean;
  message: string;
}

export interface JudicialIssueAnalysis {
  issue_number: number;
  issue_statement: string;
  applicable_law: string;
  prosecution_submission_summary: string;
  defense_submission_summary: string;
  evidentiary_evaluation: string;
  judicial_finding: string;
}

export interface Judgment {
  judgment_id: string;
  case_title: string;
  presiding_court: string;
  date_of_decision: string;
  case_background: string;
  issues_for_determination: string[];
  applicable_law: string[];
  evidence_assessment: string;
  witness_assessment: string;
  prosecution_submissions: string;
  defense_submissions: string;
  issue_analyses: JudicialIssueAnalysis[];
  findings_per_charge: Record<string, string>;
  final_decision: "CONVICTION" | "ACQUITTAL" | "PARTIAL CONVICTION" | string;
  reasons: string;
  legal_citations: string[];
}

export interface ExecutionReport {
  case_id: string;
  status: string;
  ai_judgment?: Judgment;
  agent_statuses: Record<string, string>;
  execution_time_seconds: number;
}

export interface ComparisonErrorDetail {
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  ai_claim: string;
  real_court_position: string;
  explanation: string;
}

export interface ComparisonScores {
  verdict_alignment: number;
  issue_alignment: number;
  factual_accuracy: number;
  charge_alignment: number;
  witness_alignment: number;
  evidence_alignment: number;
  legal_alignment: number;
  reasoning_alignment: number;
  finding_alignment: number;
  final_order_alignment: number;
  overall_score: number;
  weights: Record<string, number>;
  substantive_score?: number | null;
  verdict_score?: number | null;
  active_weights?: Record<string, number>;
  active_weight_denominator?: number;
  excluded_categories?: string[];
  scoring_formula?: string;
}

export type DifferenceBasis = "from_judgments" | "ai_analysis" | "information_unavailable";

export interface DifferenceItem {
  category: "evidence" | "witnesses" | "legal_rules" | "investigation" | "missing_information" | "reasoning";
  title: string;
  ai_view: string;
  real_court_view: string;
  why_different: string;
  basis: DifferenceBasis;
}

export interface DifferenceExplanation {
  simple_summary: string;
  main_reasons: string[];
  analogy: string;
  case_id?: string;
  case_title: string;
  verdicts_differ: boolean | null;
  ai_verdict: string;
  real_verdict: string;
  why_judgments_differ: string;
  ai_court_concluded: string;
  real_court_concluded: string;
  key_differences: DifferenceItem[];
  how_it_led_to_different_verdicts: string;
  what_we_can_learn: string;
  legal_terms: { term: string; meaning: string }[];
  unavailable_information: string[];
  generated_by: "llm" | "deterministic_fallback";
  model_note: string;
  disclaimer: string;
}

export interface ComparisonReport {
  comparison_id: string;
  case_id?: string;
  case_title: string;
  mode: "post_trial" | "manual";
  timestamp: string;
  case_information?: Record<string, any>;
  overall_assessment: string;
  overall_conclusion: string;
  scores: ComparisonScores;
  verdict_comparison: {
    ai_verdict: string;
    real_verdict: string;
    alignment: "aligned" | "partially_aligned" | "not_aligned";
    score: number;
    explanation: string;
    status?: string;
    is_assessable?: boolean;
    real_extracted_position?: string;
    ai_extracted_position?: string;
    verdict_normalization_explanation?: string;
  };
  reasoning_comparison: {
    addressed_actual_legal_issue: boolean;
    applied_correct_law: boolean;
    considered_missing_evidence: boolean;
    score: number;
    explanation: string;
    status?: string;
    is_assessable?: boolean;
    matched_themes_count?: number;
    total_real_themes_count?: number;
    theme_evaluations?: {
      theme_id: string;
      theme_name: string;
      real_court_position: string;
      ai_position: string;
      match_status: string;
      source_evidence?: string;
    }[];
  };
  issue_comparison: {
    score: number;
    explanation: string;
    matched_issues: any[];
    ai_missed_issues: string[];
    ai_unrelated_issues: string[];
    status?: string;
    is_assessable?: boolean;
  };
  factual_comparison?: {
    score: number;
    correctness_score?: number;
    completeness_score?: number;
    explanation: string;
    correct_facts?: string[];
    invented_facts?: string[];
    unsupported_facts?: string[];
    omitted_material_facts?: string[];
    status?: string;
    is_assessable?: boolean;
  };
  charge_comparison: {
    score: number;
    explanation: string;
    matched_charges?: any[];
    missing_charges?: string[];
    incorrectly_introduced_charges?: string[];
    historical_law_mismatches: string[];
    procedural_or_coaccused_charges?: string[];
    status?: string;
    is_assessable?: boolean;
  };
  evidence_comparison: {
    score: number;
    explanation: string;
    invented_evidence: string[];
    status?: string;
    is_assessable?: boolean;
  };
  witness_comparison?: {
    score: number;
    explanation: string;
    witness_count_ai?: number;
    witness_count_real?: number;
    status?: string;
    is_assessable?: boolean;
  };
  legal_provision_comparison?: {
    score: number;
    explanation: string;
    correct_provisions?: string[];
    missing_provisions?: string[];
    incorrectly_cited_provisions?: string[];
    historically_inapplicable_provisions?: string[];
    procedural_or_coaccused_provisions?: string[];
    unconnected_provisions?: string[];
    matched_count?: number;
    missing_count?: number;
    incorrect_count?: number;
    inapplicable_count?: number;
    unconnected_count?: number;
    status?: string;
    is_assessable?: boolean;
  };
  finding_comparison?: {
    score: number;
    explanation: string;
    issue_findings?: any[];
    status?: string;
    is_assessable?: boolean;
  };
  final_order_comparison?: {
    score: number;
    explanation: string;
    alignment: string;
    ai_final_order: string;
    real_final_order: string;
    status?: string;
    is_assessable?: boolean;
  };
  major_errors: ComparisonErrorDetail[];
  missing_important_points: string[];
  unrelated_hallucinated_points: string[];
}


