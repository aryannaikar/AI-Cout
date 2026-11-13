"""
DeepSeek-backed judicial reasoning for AI Court of India.

The Judge receives only the live case record and the outputs of the adversarial,
evidence, conflict, and legal research agents. Ground Truth is never part of the
Judge input. A single structured LLM response is validated against the existing
Judgment schema; provider failures are surfaced to the workflow, never replaced
with a deterministic or fabricated verdict.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Optional

from app.core.llm_provider import LLMConfig
from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.evidence_package_models import EvidencePackage
from app.models.judgment_models import DefenseCase, Judgment, ProsecutionCase
from app.models.legal_models import LegalResearchResult, WebResearchResult
from app.services.legal_transition import detect_case_legal_regime
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the independent judicial bench in an Indian criminal proceeding.
Decide only from the supplied case record. Prosecution and defense submissions are
advocacy, not proof. Independently assess each item, distinguish admissibility,
reliability, and probative value, and address material arguments from both sides.
Do not invent facts, witnesses, exhibits, testimony, statutory sections, precedents,
or quotations. Cite only evidence identifiers and legal authorities present in the
record. If information or legal research is missing, say so explicitly and do not
fill the gap by assumption. Apply the law indicated by the offence date and the
provided transition context. A conflict or missing item does not automatically
decide a charge: explain its actual effect on each legal ingredient and the
reasonable-doubt standard. Return only the requested Judgment JSON object."""


class JudgeAgent:
    """Render an independent, evidence-grounded judgment using configured OpenRouter DeepSeek."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        # Keep use local to this agent. LLMProvider reads the existing OpenRouter
        # model/key configuration; this does not construct another API client.
        self.llm_service = llm_service or LLMService(provider="openrouter")

    @staticmethod
    def _validate_blindness(
        case: StructuredCase,
        prosecution_case: ProsecutionCase,
        defense_case: DefenseCase,
        *records: Any,
    ) -> None:
        """Reject explicit evaluation labels before any case data reaches the provider."""
        values: list[Any] = [case, prosecution_case, defense_case, *records]
        for value in values:
            if value is None:
                continue
            serialized = value.model_dump_json().lower()
            if any(marker in serialized for marker in (
                "ground truth verdict", "ground_truth_verdict", "real verdict:",
                "hidden evaluation label", "actual court decision",
            )):
                raise PermissionError("SECURITY VIOLATION: Ground Truth evaluation data detected in Judge inputs.")

    @staticmethod
    def _collect_sources(
        prosecution_legal_research: Optional[LegalResearchResult],
        defense_legal_research: Optional[LegalResearchResult],
        web_researches: list[WebResearchResult],
        charges: list[Any],
    ) -> dict[str, Any]:
        research: list[dict[str, Any]] = []
        allowed_citations: list[str] = []
        for result in (prosecution_legal_research, defense_legal_research):
            if result is not None:
                research.append(result.model_dump(mode="json", exclude_none=True))
                allowed_citations.extend(result.citations)
                allowed_citations.extend(p.citation for p in result.applicable_provisions)
        for web_research in web_researches:
            research.append(web_research.model_dump(mode="json", exclude_none=True))
            allowed_citations.extend(source.title for source in web_research.sources)
            allowed_citations.extend(source.url for source in web_research.sources)

        for charge in charges:
            citation = f"{charge.statute}, {charge.section}"
            allowed_citations.append(citation)

        return {
            "research": research,
            "allowed_citations": list(dict.fromkeys(c for c in allowed_citations if c)),
        }

    @staticmethod
    def _validate_output(judgment: Judgment, case: StructuredCase, dossier: dict[str, Any]) -> Judgment:
        """Apply deterministic consistency, evidence-reference, and citation guardrails."""
        if judgment.final_decision not in {"CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"}:
            raise ValueError("Judge returned an unsupported final_decision value.")
        required_text = (
            judgment.case_background, judgment.evidence_assessment, judgment.witness_assessment,
            judgment.prosecution_submissions, judgment.defense_submissions, judgment.reasons,
        )
        if any(not value.strip() for value in required_text):
            raise ValueError("Judge returned an incomplete judgment with a required section left blank.")
        if not judgment.issues_for_determination or not judgment.issue_analyses:
            raise ValueError("Judge returned no issues or issue analyses.")
        if len(judgment.issue_analyses) != len(judgment.issues_for_determination):
            raise ValueError("Judge issue analyses do not match the issues for determination.")
        if any(a.issue_statement != issue for a, issue in zip(judgment.issue_analyses, judgment.issues_for_determination)):
            raise ValueError("Judge issue analyses do not align with the framed issues.")
        if any(a.judicial_finding not in {"PROVED", "NOT PROVED", "DISPROVED"} for a in judgment.issue_analyses):
            raise ValueError("Judge returned an unsupported issue finding.")

        # Validate identifiers used in the rendered judgment against the supplied dossier.
        source_text = json.dumps(dossier, ensure_ascii=False)
        known_refs = {m.group(0).lower() for m in re.finditer(
            r"\b(?:PW|DW|EV|MO)[- ]\d+[A-Z]?\b|\bEx\.?\s*[A-Z]?[- ]?\d+[A-Z]?\b",
            source_text,
            re.IGNORECASE,
        )}
        rendered = judgment.model_dump_json().lower()
        for match in re.finditer(
            r"\b(?:PW|DW|EV|MO)[- ]\d+[A-Z]?\b|\bEx\.?\s*[A-Z]?[- ]?\d+[A-Z]?\b",
            rendered,
            re.IGNORECASE,
        ):
            if match.group(0).lower() not in known_refs:
                raise ValueError(f"Judge cited evidence identifier absent from the record: {match.group(0)}")

        allowed = {citation.strip().casefold() for citation in dossier["allowed_citations"]}
        for citation in judgment.legal_citations:
            if citation.strip().casefold() not in allowed:
                raise ValueError(f"Judge cited legal authority absent from supplied research or charges: {citation}")

        if case.charges:
            expected = {f"{charge.statute}, {charge.section}" for charge in case.charges}
            if set(judgment.findings_per_charge) != expected:
                raise ValueError("Judge findings must address each supplied charge exactly once and add no charges.")

            outcomes = []
            for charge, outcome_text in judgment.findings_per_charge.items():
                value = outcome_text.casefold()
                if any(term in value for term in ("acquitt", "not proved", "not proven", "disproved")):
                    outcomes.append("acquittal")
                elif any(term in value for term in ("convict", "guilty", "proved", "proven")):
                    outcomes.append("conviction")
                else:
                    raise ValueError(f"Judge returned an unclear finding for charge '{charge}'.")
            expected_decision = (
                "CONVICTION" if all(item == "conviction" for item in outcomes)
                else "ACQUITTAL" if all(item == "acquittal" for item in outcomes)
                else "PARTIAL CONVICTION"
            )
            if judgment.final_decision != expected_decision:
                raise ValueError("Judge's final decision is inconsistent with the findings per charge.")

        # Identity and date come from the workflow, not model inference.
        return judgment.model_copy(update={
            "judgment_id": f"JUDG-{case.case_id}",
            "case_title": case.case_title,
            "date_of_decision": date.today().isoformat(),
        })

    def adjudicate(
        self,
        case: StructuredCase,
        prosecution_case: ProsecutionCase,
        defense_case: DefenseCase,
        evidence_report: EvidenceAnalysisReport,
        conflict_report: ConflictReport,
        evidence_package: Optional[EvidencePackage] = None,
        prosecution_legal_research: Optional[LegalResearchResult] = None,
        defense_legal_research: Optional[LegalResearchResult] = None,
        web_research: Optional[WebResearchResult] = None,
        prosecution_web_research: Optional[WebResearchResult] = None,
        defense_web_research: Optional[WebResearchResult] = None,
    ) -> Judgment:
        """Ask the configured DeepSeek model for one validated 12-section judgment."""
        self._validate_blindness(
            case, prosecution_case, defense_case, evidence_package, evidence_report,
            conflict_report, prosecution_legal_research, defense_legal_research, web_research,
            prosecution_web_research, defense_web_research,
        )

        web_results: list[WebResearchResult] = []
        seen_research_ids: set[str] = set()
        for result in (web_research, prosecution_web_research, defense_web_research):
            if result is not None and result.research_id not in seen_research_ids:
                web_results.append(result)
                seen_research_ids.add(result.research_id)
        authorities = self._collect_sources(
            prosecution_legal_research, defense_legal_research, web_results, case.charges
        )
        dossier = {
            "original_case_record": case.model_dump(mode="json", exclude_none=True),
            "prosecution_submission": prosecution_case.model_dump(mode="json", exclude_none=True),
            "defense_submission": defense_case.model_dump(mode="json", exclude_none=True),
            "evidence_analysis": evidence_report.model_dump(mode="json", exclude_none=True),
            "conflict_analysis": conflict_report.model_dump(mode="json", exclude_none=True),
            "evidence_package": evidence_package.model_dump(mode="json", exclude_none=True) if evidence_package else None,
            "legal_regime": detect_case_legal_regime(case),
            "legal_and_precedent_research": authorities["research"],
            "allowed_citations": authorities["allowed_citations"],
        }
        prompt = (
            "Adjudicate this record independently. First identify the charges and ingredients; "
            "separate established, disputed, and unsupported facts; test both parties' arguments; "
            "evaluate witnesses, documents, material evidence, admissibility, reliability, probative "
            "value, corroboration, chain of custody, and contradictions; then apply only supplied law. "
            "Address missing information explicitly. Findings must cite the supplied witness/exhibit IDs "
            "or exact supplied legal citations where available. Do not treat submissions as proof. "
            "If law is unavailable, state that limitation. Match the existing Judgment schema exactly.\n\n"
            "LIVE TRIAL DOSSIER (contains no Ground Truth):\n"
            + json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
        )
        logger.info(
            "Judge requesting structured reasoning from OpenRouter model '%s' for case '%s'",
            LLMConfig.openrouter_model(), case.case_id,
        )
        judgment = self.llm_service.generate_structured(
            prompt=prompt,
            response_schema=Judgment,
            system_prompt=SYSTEM_PROMPT,
        )
        return self._validate_output(judgment, case, dossier)
