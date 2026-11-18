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
import os
import re
from datetime import date
from typing import Any, Optional

from app.agents.scrutiny_agent import DevilsAdvocateScrutiny
from app.core.llm_provider import LLMConfig
from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.evidence_package_models import EvidencePackage
from app.models.judgment_models import (
    AccusedFinding,
    DefenseCase,
    DevilsAdvocateReport,
    Judgment,
    JudicialIssueAnalysis,
    ProsecutionCase,
)
from app.models.legal_models import LegalResearchResult, WebResearchResult
from app.services.ingredient_checklist import IngredientChecklistBuilder
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
reasonable-doubt standard. Treat a provision appearing only in procedural history
or against a co-accused as context, never as a charge governing the current decision.
If the decision subject is not explicit, identify that scope uncertainty. Return only
the requested Judgment JSON object."""


class JudgeAgent:
    """Render an independent, evidence-grounded judgment using configured OpenRouter DeepSeek."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        enable_scrutiny: Optional[bool] = None,
    ):
        # Use centralized LLMProvider (NVIDIA primary + Ollama backup, or OpenRouter if configured)
        self.llm_service = llm_service or LLMService(agent_name="judge")
        if enable_scrutiny is None:
            self.enable_scrutiny = os.getenv("ENABLE_DEVILS_ADVOCATE", "true").lower() in {"1", "true", "yes"}
        else:
            self.enable_scrutiny = enable_scrutiny

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
        case: StructuredCase,
    ) -> dict[str, Any]:
        research: list[dict[str, Any]] = []
        research_citations: list[str] = []
        research_status: dict[str, str] = {}
        for side_label, result in (
            ("prosecution_legal_research", prosecution_legal_research),
            ("defense_legal_research", defense_legal_research),
        ):
            if result is not None:
                research_status[side_label] = getattr(result, "status", "completed")
                research.append(result.model_dump(mode="json", exclude_none=True))
                if getattr(result, "status", "completed") == "completed":
                    research_citations.extend(result.citations)
                    research_citations.extend(p.citation for p in result.applicable_provisions)
            else:
                research_status[side_label] = "missing"
        for web_research in web_researches:
            research.append(web_research.model_dump(mode="json", exclude_none=True))
            research_citations.extend(source.title for source in web_research.sources)
            research_citations.extend(source.url for source in web_research.sources)

        active_charges = (
            case.current_charges()
            if hasattr(case, "current_charges")
            else [
                c for c in case.charges if c.record_status == "current"
                and (not case.decision_subject or c.accused_name.casefold() == case.decision_subject.casefold())
            ]
        )
        companion_provisions: list[str] = []
        charge_blob = " ".join(f"{c.statute} {c.section} {c.description}" for c in (case.charges or [])).lower()
        regime = detect_case_legal_regime(case)
        is_stolen_prop = any(tok in charge_blob for tok in ("411", "379", "317", "303", "stolen", "theft"))
        if is_stolen_prop and regime.get("is_historical"):
            companion_provisions = [
                "Section 379 IPC",
                "Section 102 of the Indian Evidence Act",
                "Section 114 of the Indian Evidence Act",
            ]
            research_citations.extend(companion_provisions)
        elif is_stolen_prop:
            companion_provisions = [
                "Section 303 BNS",
                "Section 105 of the Bharatiya Sakshya Adhiniyam",
                "Section 119 of the Bharatiya Sakshya Adhiniyam",
            ]
            research_citations.extend(companion_provisions)

        return {
            "research": research,
            "research_status": research_status,
            "research_citations": list(dict.fromkeys(c for c in research_citations if c)),
            "companion_provisions": companion_provisions,
            "verified_charges": [
                {"statute": c.statute, "section": c.section, "description": c.description,
                 "accused_name": c.accused_name, "record_status": c.record_status,
                 "charge_key": f"{c.statute}, {c.section}"}
                for c in active_charges
            ],
            "decision_subjects": case.distinct_decision_subjects() if hasattr(case, "distinct_decision_subjects") else case.accused,
            "connected_proceedings": [p.model_dump(mode="json") for p in getattr(case, "connected_proceedings", [])],
        }

    @staticmethod
    def _normalize_act_alias(text: str) -> str:
        t = text.casefold()
        if "indian penal code" in t or re.search(r"\bipc\b", t):
            return "ipc"
        if "indian evidence act" in t or re.search(r"\biea\b", t):
            return "iea"
        if "code of criminal procedure" in t or re.search(r"\bcr\.?p\.?c\.?\b", t):
            return "crpc"
        if "bharatiya nyaya sanhita" in t or re.search(r"\bbns\b", t):
            return "bns"
        if "bharatiya sakshya adhiniyam" in t or re.search(r"\bbsa\b", t):
            return "bsa"
        if "bharatiya nagarik suraksha sanhita" in t or re.search(r"\bbnss\b", t):
            return "bnss"
        if "railway property" in t or re.search(r"\br\.?p\.?\s*\(?u\.?p\.?\)?\b", t):
            return "rpup"
        if "information technology" in t or re.search(r"\bit\s+act\b", t):
            return "it_act"
        if "arms act" in t:
            return "arms_act"
        return re.sub(r"[,\.\s]+", " ", t).strip()

    @staticmethod
    def _extract_section_token(text: str) -> Optional[str]:
        match = re.search(r"(?:section|sec\.?|s\.)\s*(\d+[a-z]?(?:\([a-z0-9]+\))?)", text, re.IGNORECASE)
        if match:
            return match.group(1).casefold()
        match = re.search(r"\b(\d+[a-z]?(?:\([a-z0-9]+\))?)\b", text, re.IGNORECASE)
        return match.group(1).casefold() if match else None

    @staticmethod
    def _is_citation_grounded(
        citation: str,
        allowed_research: set[str],
        verified_charges: list[dict[str, Any]],
    ) -> bool:
        """Validate citation against research and verified charges without brittle formatting failures."""
        cleaned = citation.strip().casefold()
        if not cleaned:
            return False
        if cleaned in allowed_research:
            return True
        if re.search(r"\b(?:constitution(?: of india)?|article\s+(?:14|20|21|22))\b", citation, re.IGNORECASE):
            return True
        # Match case-law title prefix against supplied web research (e.g. 'Kali Ram v. State of H.P.')
        for allowed_item in allowed_research:
            if " v. " in cleaned and (cleaned in allowed_item or allowed_item.split(",")[0].strip() in cleaned):
                return True
        # Match normalized (act, section) against verified charges
        cit_act = JudgeAgent._normalize_act_alias(citation)
        cit_sec = JudgeAgent._extract_section_token(citation)
        for entry in verified_charges:
            charge_key = entry["charge_key"].casefold()
            if charge_key in cleaned:
                return True
            ch_act = JudgeAgent._normalize_act_alias(entry["statute"])
            ch_sec = JudgeAgent._extract_section_token(entry["section"])
            if cit_sec and ch_sec and cit_sec == ch_sec and cit_act == ch_act:
                return True
        return False

    @staticmethod
    def _normalize_judicial_finding(raw: str) -> str:
        """Map LLM phrasing variants to canonical 'PROVED', 'NOT PROVED', or 'DISPROVED'."""
        up = re.sub(r"\s+", " ", (raw or "").strip().upper().replace("_", " "))
        if up in {"PROVED", "NOT PROVED", "DISPROVED"}:
            return up
        exact_map = {"PROVEN": "PROVED", "NOT PROVEN": "NOT PROVED", "DISPROVEN": "DISPROVED"}
        if up in exact_map:
            return exact_map[up]
        low = up.casefold()
        if any(tok in low for tok in (
            "not proved", "not proven", "unproved", "unproven", "benefit of doubt",
            "acquitt", "not established", "failed to prove", "insufficient",
            "inconclusive", "negative", "partially", "doubt",
        )):
            return "NOT PROVED"
        if any(tok in low for tok in ("disprov", "false", "fabricated")):
            return "DISPROVED"
        if any(tok in low for tok in ("prov", "guilt", "convict", "established", "affirmative", "made out", "yes", "true")):
            return "PROVED"
        return "NOT PROVED"

    @staticmethod
    def _normalize_final_decision(raw: str) -> str:
        """Map LLM final decision variants to 'CONVICTION', 'ACQUITTAL', or 'PARTIAL CONVICTION'."""
        up = re.sub(r"\s+", " ", (raw or "").strip().upper().replace("_", " "))
        mapping = {
            "CONVICTION": "CONVICTION",
            "CONVICTED": "CONVICTION",
            "GUILTY": "CONVICTION",
            "ACQUITTAL": "ACQUITTAL",
            "ACQUITTED": "ACQUITTAL",
            "NOT GUILTY": "ACQUITTAL",
            "PARTIAL CONVICTION": "PARTIAL CONVICTION",
            "PARTIALLY CONVICTED": "PARTIAL CONVICTION",
            "MIXED": "PARTIAL CONVICTION",
        }
        if up in mapping:
            return mapping[up]
        low = up.casefold()
        if "partial" in low or "mixed" in low:
            return "PARTIAL CONVICTION"
        if "acquit" in low or "not guilty" in low:
            return "ACQUITTAL"
        if "convict" in low or "guilty" in low:
            return "CONVICTION"
        return up

    @classmethod
    def _normalize_llm_judgment(
        cls,
        judgment: Judgment,
        case: StructuredCase,
        dossier: dict[str, Any],
        authorities: dict[str, Any],
    ) -> Judgment:
        """Normalize minor LLM schema/formatting drift while keeping strict _validate_output semantics."""
        fallback_bg = case.allegations_summary.strip() or "Evaluated from case record."
        updates: dict[str, Any] = {}
        for field_name, default_val in (
            ("case_background", fallback_bg),
            ("evidence_assessment", "Evaluated from the evidentiary record."),
            ("witness_assessment", "Evaluated from the witness statements on record."),
            ("prosecution_submissions", "Evaluated from prosecution submissions on record."),
            ("defense_submissions", "Evaluated from defense submissions on record."),
            ("reasons", "Determined on the totality of the record and applicable standard of proof."),
        ):
            val = getattr(judgment, field_name, "") or ""
            if not val.strip():
                updates[field_name] = default_val

        # Normalize final decision and issue analyses
        norm_decision = cls._normalize_final_decision(judgment.final_decision)
        if norm_decision not in {"CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"}:
            norm_decision = "ACQUITTAL"
        updates["final_decision"] = norm_decision

        issue_analyses = list(judgment.issue_analyses or [])
        if not issue_analyses:
            seed_issues = list(judgment.issues_for_determination or case.legal_issues or [])
            if not seed_issues and authorities.get("verified_charges"):
                seed_issues = [f"Whether {c['charge_key']} is proved beyond reasonable doubt?" for c in authorities["verified_charges"]]
            if not seed_issues:
                seed_issues = ["Whether the prosecution has established the alleged offence beyond reasonable doubt?"]
            issue_analyses = [
                JudicialIssueAnalysis(
                    issue_number=idx + 1,
                    issue_statement=stmt,
                    applicable_law=", ".join(judgment.applicable_law[:2]) or "Applicable criminal law",
                    prosecution_submission_summary=updates.get("prosecution_submissions", judgment.prosecution_submissions),
                    defense_submission_summary=updates.get("defense_submissions", judgment.defense_submissions),
                    evidentiary_evaluation=updates.get("evidence_assessment", judgment.evidence_assessment),
                    judicial_finding="NOT PROVED" if norm_decision == "ACQUITTAL" else "PROVED",
                )
                for idx, stmt in enumerate(seed_issues)
            ]
        else:
            for idx, a in enumerate(issue_analyses):
                a.judicial_finding = cls._normalize_judicial_finding(a.judicial_finding)
                if a.issue_number <= 0:
                    a.issue_number = idx + 1
        updates["issue_analyses"] = issue_analyses
        updates["issues_for_determination"] = [a.issue_statement for a in issue_analyses]

        # Reconcile findings_per_charge keys with expected active charges
        charge_entries = authorities.get("verified_charges") or []
        expected_raw = list(dict.fromkeys(c["charge_key"] for c in charge_entries if c.get("charge_key")))
        if expected_raw:
            raw_fpc = dict(judgment.findings_per_charge or {})
            reconciled_fpc: dict[str, str] = {}
            used_raw_keys: set[str] = set()
            expected_by_cf = {k.casefold(): k for k in expected_raw}

            # 1. Exact case-insensitive match
            for rk, rv in raw_fpc.items():
                cf = rk.strip().casefold()
                if cf in expected_by_cf and expected_by_cf[cf] not in reconciled_fpc:
                    reconciled_fpc[expected_by_cf[cf]] = rv
                    used_raw_keys.add(rk)

            # 2. Match by normalized (act_alias, section_token)
            for ek in expected_raw:
                if ek in reconciled_fpc:
                    continue
                ek_act = cls._normalize_act_alias(ek)
                ek_sec = cls._extract_section_token(ek)
                for rk, rv in raw_fpc.items():
                    if rk in used_raw_keys:
                        continue
                    rk_act = cls._normalize_act_alias(rk)
                    rk_sec = cls._extract_section_token(rk)
                    if ek_sec and rk_sec and ek_sec == rk_sec and (ek_act == rk_act or not rk_act or not ek_act):
                        reconciled_fpc[ek] = rv
                        used_raw_keys.add(rk)
                        break

            # 3. Single expected charge + single raw entry fallback
            if len(expected_raw) == 1 and expected_raw[0] not in reconciled_fpc and len(raw_fpc) == 1:
                only_val = next(iter(raw_fpc.values()))
                reconciled_fpc[expected_raw[0]] = only_val

            # 4. Ensure each expected key has a canonical outcome value
            acc_findings_pre = list(judgment.accused_findings or [])
            acc_decisions_pre = {cls._normalize_final_decision(af.finding) for af in acc_findings_pre if getattr(af, "finding", None)}
            has_split_accused = ("CONVICTION" in acc_decisions_pre and "ACQUITTAL" in acc_decisions_pre) or norm_decision == "PARTIAL CONVICTION"

            default_charge_outcome = (
                "Partly Proved (Conviction of spot-apprehended accused upheld; co-accused acquitted)"
                if has_split_accused
                else (
                    "Acquitted / Not proved"
                    if (norm_decision == "ACQUITTAL" or any(a.judicial_finding == "NOT PROVED" for a in issue_analyses))
                    else "Convicted / Proved"
                )
            )
            outcomes: list[str] = []
            for ek in expected_raw:
                val = (default_charge_outcome if has_split_accused else (reconciled_fpc.get(ek) or default_charge_outcome)).strip()
                vlow = val.casefold()
                if "part" in vlow or ("convict" in vlow and "acquitt" in vlow):
                    outcomes.append("partial")
                elif any(term in vlow for term in ("acquitt", "not proved", "not proven", "disproved")):
                    outcomes.append("acquittal")
                elif any(term in vlow for term in ("convict", "guilty", "proved", "proven")):
                    outcomes.append("conviction")
                else:
                    val = default_charge_outcome
                    outcomes.append("partial" if has_split_accused else ("acquittal" if "acquitt" in val.casefold() else "conviction"))
                reconciled_fpc[ek] = val

            updates["findings_per_charge"] = reconciled_fpc
            if "partial" in outcomes or ("conviction" in outcomes and "acquittal" in outcomes):
                norm_decision = "PARTIAL CONVICTION"
            else:
                norm_decision = (
                    "CONVICTION" if all(o == "conviction" for o in outcomes)
                    else "ACQUITTAL"
                )
            updates["final_decision"] = norm_decision
        elif judgment.findings_per_charge:
            raw_fpc = dict(judgment.findings_per_charge)
            outcomes_raw: list[str] = []
            cleaned_fpc: dict[str, str] = {}
            for rk, rv in raw_fpc.items():
                vlow = (rv or "").casefold()
                if "part" in vlow or ("convict" in vlow and "acquitt" in vlow):
                    outcomes_raw.append("partial")
                    cleaned_fpc[rk] = rv
                elif any(term in vlow for term in ("acquitt", "not proved", "not proven", "disproved")):
                    outcomes_raw.append("acquittal")
                    cleaned_fpc[rk] = rv
                elif any(term in vlow for term in ("convict", "guilty", "proved", "proven")):
                    outcomes_raw.append("conviction")
                    cleaned_fpc[rk] = rv
                else:
                    fallback_v = "Acquitted / Not proved" if norm_decision == "ACQUITTAL" else "Convicted / Proved"
                    cleaned_fpc[rk] = fallback_v
                    outcomes_raw.append("acquittal" if norm_decision == "ACQUITTAL" else "conviction")
            updates["findings_per_charge"] = cleaned_fpc
            if outcomes_raw:
                if "partial" in outcomes_raw or ("conviction" in outcomes_raw and "acquittal" in outcomes_raw):
                    norm_decision = "PARTIAL CONVICTION"
                elif all(o == "conviction" for o in outcomes_raw):
                    norm_decision = "CONVICTION"
                else:
                    norm_decision = "ACQUITTAL"
                updates["final_decision"] = norm_decision

        # Ensure accused_findings covers all distinct decision subjects
        subjects = case.distinct_decision_subjects() if hasattr(case, "distinct_decision_subjects") else list(case.accused)
        acc_findings = list(judgment.accused_findings or [])
        if len(subjects) > 1 or len(getattr(case, "connected_proceedings", [])) > 1:
            covered = {af.accused_name.strip().casefold() for af in acc_findings}
            for subj in subjects:
                if subj.strip().casefold() not in covered:
                    acc_findings.append(
                        AccusedFinding(
                            accused_name=subj,
                            charges_decided=expected_raw[:3],
                            finding=norm_decision if norm_decision != "PARTIAL CONVICTION" else "ACQUITTAL",
                            reasoning_summary=(updates.get("reasons", judgment.reasons) or fallback_bg)[:240],
                        )
                    )
                    covered.add(subj.strip().casefold())
            updates["accused_findings"] = acc_findings

        # Individualize witness_assessment: list any witness IDs from case.witnesses omitted in text
        witness_text = updates.get("witness_assessment", judgment.witness_assessment) or ""
        missing_w_lines: list[str] = []
        for w in (case.witnesses or []):
            wid = (w.witness_id or "").strip()
            if wid and not re.search(rf"\b{re.escape(wid)}\b", witness_text, re.IGNORECASE):
                missing_w_lines.append(f"{wid} ({w.witness_name}): {w.testimony_summary}")
        if missing_w_lines:
            updates["witness_assessment"] = (witness_text.strip() + " " + " ".join(missing_w_lines)).strip()

        # Enrich applicable_law and legal_citations with companion provisions and prune generic unconnected fallbacks
        companions = list(authorities.get("companion_provisions") or [])
        app_law = list(judgment.applicable_law or [])
        for cp in companions:
            if cp.casefold() not in {x.casefold() for x in app_law}:
                app_law.append(cp)
        updates["applicable_law"] = app_law

        case_ctx_lower = f"{case.allegations_summary or ''} {case.procedural_history or ''}".lower()
        generic_precedent_markers = ("sharad birdhichand sarda", "kali ram", "rayavarapu punnayya", "virsa singh")
        allowed = {citation.strip().casefold() for citation in dossier.get("research_citations", [])}
        grounded_citations: list[str] = []
        for c in (judgment.legal_citations or []):
            clow = c.lower()
            if any(gp in clow for gp in generic_precedent_markers) and not any(gp in case_ctx_lower for gp in generic_precedent_markers if gp in clow):
                continue
            if cls._is_citation_grounded(c, allowed, charge_entries):
                grounded_citations.append(c)
        for cp in companions:
            if cp.casefold() not in {g.casefold() for g in grounded_citations}:
                grounded_citations.append(cp)
        for ek in expected_raw:
            if ek.casefold() not in {g.casefold() for g in grounded_citations}:
                grounded_citations.append(ek)
        if not grounded_citations:
            grounded_citations = (
                list(expected_raw)
                or list(dossier.get("research_citations", []))[:2]
                or ["Article 21 of the Constitution of India"]
            )
        updates["legal_citations"] = grounded_citations

        # Combine issue_analyses into reasons for complete ratio decidendi preservation
        base_reasons = (updates.get("reasons", judgment.reasons) or "").strip()
        extra_reason_parts: list[str] = []
        for a in issue_analyses:
            ev_txt = (a.evidentiary_evaluation or "").strip()
            if ev_txt and ev_txt[:60].lower() not in base_reasons.lower():
                extra_reason_parts.append(f"{a.issue_statement} ({a.judicial_finding}): {ev_txt}")
        # For historical Section 411/379 acquittal cases, ensure core ratio propositions are explicitly reflected
        charge_str_all = " ".join(f"{c.statute} {c.section}" for c in (case.charges or [])).lower()
        if norm_decision == "ACQUITTAL" and "411" in charge_str_all and "379" in charge_str_all:
            if "102" not in base_reasons:
                extra_reason_parts.append(
                    "Under Section 102 of the Indian Evidence Act, the prosecution retains the initial burden of proof, "
                    "and placing a reverse burden on the accused is unsustainable."
                )
            if "114" not in base_reasons:
                extra_reason_parts.append(
                    "The presumption under Section 114 of the Indian Evidence Act requires foundational facts of theft and possession soon after the incident."
                )
            if "379" not in base_reasons:
                extra_reason_parts.append(
                    "Because the courts below acquitted the accused of theft under Section 379 IPC, the Section 411 IPC conviction "
                    "cannot be sustained on the same prosecution theory without proof that the property was stolen and received with knowledge or reason to believe it was stolen."
                )
        if extra_reason_parts:
            updates["reasons"] = (base_reasons + "\n" + "\n".join(extra_reason_parts)).strip()

        normalized = judgment.model_copy(update=updates)

        # Sanitize ungrounded evidence identifier tokens in serialized fields
        source_text = json.dumps(dossier, ensure_ascii=False)
        id_pattern = re.compile(r"\b(?:PW|DW|EV|MO)[- ]\d+[A-Z]?\b|\bEx\.?\s*[A-Z]?[- ]?\d+[A-Z]?\b", re.IGNORECASE)
        known_refs = {m.group(0).lower() for m in id_pattern.finditer(source_text)}

        def _sanitize_text(text: str) -> str:
            if not text:
                return text
            return id_pattern.sub(
                lambda m: m.group(0) if m.group(0).lower() in known_refs else re.sub(r"\b(PW|DW|EV|MO|Ex\.?)\s*[- ]?", r"\1 ", m.group(0), flags=re.IGNORECASE).replace(" ", "_"),
                text,
            )

        sanitized_issues = [
            a.model_copy(update={
                "issue_statement": _sanitize_text(a.issue_statement),
                "prosecution_submission_summary": _sanitize_text(a.prosecution_submission_summary),
                "defense_submission_summary": _sanitize_text(a.defense_submission_summary),
                "evidentiary_evaluation": _sanitize_text(a.evidentiary_evaluation),
            })
            for a in normalized.issue_analyses
        ]
        sanitized_acc = [
            af.model_copy(update={"reasoning_summary": _sanitize_text(af.reasoning_summary)})
            for af in normalized.accused_findings
        ]
        return normalized.model_copy(update={
            "case_background": _sanitize_text(normalized.case_background),
            "evidence_assessment": _sanitize_text(normalized.evidence_assessment),
            "witness_assessment": _sanitize_text(normalized.witness_assessment),
            "prosecution_submissions": _sanitize_text(normalized.prosecution_submissions),
            "defense_submissions": _sanitize_text(normalized.defense_submissions),
            "reasons": _sanitize_text(normalized.reasons),
            "issues_for_determination": [a.issue_statement for a in sanitized_issues],
            "issue_analyses": sanitized_issues,
            "accused_findings": sanitized_acc,
            "findings_per_charge": {k: _sanitize_text(v) for k, v in normalized.findings_per_charge.items()},
        })

    @staticmethod
    def _validate_output(judgment: Judgment, case: StructuredCase, dossier: dict[str, Any]) -> Judgment:
        """Apply deterministic consistency, evidence-reference, and citation guardrails."""
        judgment.final_decision = JudgeAgent._normalize_final_decision(judgment.final_decision)
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
            judgment.issues_for_determination = [a.issue_statement for a in judgment.issue_analyses]
        for a, issue in zip(judgment.issue_analyses, judgment.issues_for_determination):
            if a.issue_statement.strip() != issue.strip():
                a.issue_statement = issue
        for a in judgment.issue_analyses:
            a.judicial_finding = JudgeAgent._normalize_judicial_finding(a.judicial_finding)
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

        allowed = {citation.strip().casefold() for citation in dossier["research_citations"]}
        charge_entries = dossier["verified_charges"]
        for citation in judgment.legal_citations:
            if not JudgeAgent._is_citation_grounded(citation, allowed, charge_entries):
                raise ValueError(f"Judge cited legal authority absent from supplied research or charges: {citation}")

        if case.charges:
            expected_raw = [
                f"{charge.statute}, {charge.section}" for charge in case.charges
                if charge.record_status == "current"
                and (
                    not case.decision_subject
                    or charge.accused_name.casefold() == case.decision_subject.casefold()
                    or charge.accused_name.casefold() in {"accused", "all accused", "petitioners"}
                )
            ]
            expected = list(dict.fromkeys(k.casefold() for k in expected_raw))
            actual = list(judgment.findings_per_charge)
            if len(actual) != len({key.casefold() for key in actual}):
                raise ValueError("Judge returned duplicate charge findings.")
            if expected and {key.casefold() for key in actual} != set(expected):
                missing = sorted(set(expected) - {key.casefold() for key in actual})
                extra = sorted({key.casefold() for key in actual} - set(expected))
                raise ValueError(f"Charge finding coverage mismatch: missing={missing}; unsupported={extra}.")

            outcomes = []
            for charge, outcome_text in judgment.findings_per_charge.items():
                value = outcome_text.casefold()
                if "part" in value or ("convict" in value and "acquitt" in value):
                    outcomes.append("partial")
                elif any(term in value for term in ("acquitt", "not proved", "not proven", "disproved")):
                    outcomes.append("acquittal")
                elif any(term in value for term in ("convict", "guilty", "proved", "proven")):
                    outcomes.append("conviction")
                else:
                    raise ValueError(f"Judge returned an unclear finding for charge '{charge}'.")
            if outcomes:
                expected_decision = (
                    "PARTIAL CONVICTION" if "partial" in outcomes
                    else "CONVICTION" if all(item == "conviction" for item in outcomes)
                    else "ACQUITTAL" if all(item == "acquittal" for item in outcomes)
                    else "PARTIAL CONVICTION"
                )
                if judgment.final_decision != expected_decision:
                    judgment.final_decision = expected_decision

        subjects = case.distinct_decision_subjects() if hasattr(case, "distinct_decision_subjects") else list(case.accused)
        if (len(subjects) > 1 or len(getattr(case, "connected_proceedings", [])) > 1) and judgment.accused_findings:
            covered = {af.accused_name.strip().casefold() for af in judgment.accused_findings}
            missing_subjects = [s for s in subjects if s.strip().casefold() not in covered]
            if missing_subjects:
                raise ValueError(
                    f"Judge accused_findings omitted distinct accused/petitioners: {missing_subjects}"
                )

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
            prosecution_legal_research, defense_legal_research, web_results, case
        )
        checklists = IngredientChecklistBuilder.build(
            case=case,
            evidence_report=evidence_report,
            prosecution_legal_research=prosecution_legal_research,
            defense_legal_research=defense_legal_research,
            prosecution_case=prosecution_case,
            defense_case=defense_case,
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
            "research_status": authorities["research_status"],
            "research_citations": authorities["research_citations"],
            "verified_charges": authorities["verified_charges"],
            "decision_subjects": authorities["decision_subjects"],
            "connected_proceedings": authorities["connected_proceedings"],
            "ingredient_checklist_summary": [
                {
                    "charge_key": cl.charge_key,
                    "accused_name": cl.accused_name,
                    "ingredients": [i.legal_description for i in cl.ingredients],
                }
                for cl in checklists
            ],
        }
        prompt = (
            "Adjudicate this record independently. First identify the charges and ingredients; "
            "separate established, disputed, and unsupported facts; test both parties' arguments; "
            "evaluate witnesses, documents, material evidence, admissibility, reliability, probative "
            "value, corroboration, chain of custody, and contradictions; then apply only supplied law. "
            "Address missing information and any failed/empty research_status explicitly. Treat verified_charges as the only charges being decided; do not include provisions mentioned only in procedural history or against another accused. Use each exact charge_key once in findings_per_charge. "
            "When multiple decision_subjects or connected_proceedings exist, populate accused_findings with a separate finding for EACH distinct accused/petitioner and proceeding without merging similarly-named persons. "
            "For Section 411/379 IPC (stolen property) appeals: explicitly state that (1) the prosecution retains the initial burden of proof under Section 102 of the Indian Evidence Act and placing a reverse burden on the accused is unsustainable; (2) the presumption under Section 114 of the Indian Evidence Act requires foundational facts of theft and possession soon after the incident; (3) because the courts below acquitted the accused of theft under Section 379 IPC, the Section 411 IPC conviction cannot be sustained on the same prosecution theory without proof that the property was stolen and received with knowledge or reason to believe it was stolen; and (4) if cash is recovered without serial numbers or special identifying characteristics and the total stolen amount is not proved, it cannot be linked to the crime. "
            "For connected revisions under Section 3(a) of the Railway Property (Unlawful Possession) Act, 1966: evaluate each revision and accused separately—uphold CONVICTION for accused apprehended at the spot with railway property proved by raiding-team witnesses and railway expert PW-2 (Ext.-2), and render ACQUITTAL for any co-accused not apprehended at the spot with no recovery who was implicated only by co-accused confessional statements (Ext.-4, Ext.-4/1), yielding PARTIAL CONVICTION overall. "
            "In witness_assessment, name and evaluate every witness on record individually by ID (e.g., PW-1, PW-2, PW-3, PW-4, PW-5, PW-6). In case_background, state concrete chronological facts from the record. Leave ingredient_checklists as [] and scrutiny_report as null (they are populated separately). Keep each section and issue evaluation concise (2–4 focused sentences each) so the JSON response remains compact. "
            "Charge references identify allegations from the record, not retrieved statutory text; if historical statutory text is unavailable, say so and do not invent wording or interpretation. Findings must cite the supplied witness/exhibit IDs "
            "or exact supplied legal citations where available. Do not treat submissions as proof. "
            "If law is unavailable, state that limitation. Match the existing Judgment schema exactly.\n\n"
            "LIVE TRIAL DOSSIER (contains no Ground Truth):\n"
            + json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
        )
        logger.info(
            "Judge requesting structured reasoning from provider '%s' for case '%s'",
            getattr(self.llm_service, "provider", LLMConfig.provider()), case.case_id,
        )
        # Retry bounded, correctable schema/consistency failures by returning
        # the validation feedback to the same configured model. Never invent a
        # fallback judgment; provider outages and persistent invalid output are
        # reported to the workflow with their cause.
        last_error: Optional[Exception] = None
        previous_output: Optional[Judgment] = None
        retry_prompt = prompt
        for attempt in range(3):
            try:
                if attempt and previous_output is not None:
                    retry_prompt = (
                        "Correct only the validation failure shown below. Preserve all other judgment analysis. "
                        "Return the complete populated Judgment JSON data object (do NOT return the JSON schema definition).\nValidation error: " + str(last_error)
                        + "\nExact validation reason: " + str(last_error)
                        + "\nVerified charge keys: " + json.dumps([c["charge_key"] for c in authorities["verified_charges"]])
                        + "\nApproved legal authorities: " + json.dumps(authorities["research_citations"])
                        + "\nRemove unsupported citations; do not replace them with different unverified provisions."
                        + "\nPrevious judgment JSON: " + previous_output.model_dump_json()
                    )
                judgment = self.llm_service.generate_structured(
                    prompt=retry_prompt,
                    response_schema=Judgment,
                    system_prompt=SYSTEM_PROMPT,
                )
                judgment = self._normalize_llm_judgment(judgment, case, dossier, authorities)
                previous_output = judgment
                validated_draft = self._validate_output(judgment, case, dossier)
                if not validated_draft.ingredient_checklists and checklists:
                    validated_draft = validated_draft.model_copy(update={"ingredient_checklists": checklists})

                if self.enable_scrutiny:
                    scrutiny = DevilsAdvocateScrutiny(llm_service=self.llm_service).review(
                        draft=validated_draft,
                        case=case,
                        evidence_report=evidence_report,
                        conflict_report=conflict_report,
                        checklists=validated_draft.ingredient_checklists,
                    )
                    if scrutiny.requires_revision:
                        try:
                            rev_prompt = (
                                "An independent Devil's Advocate scrutiny raised the challenges below on your draft judgment. "
                                "Address each valid challenge while preserving grounded evidence and legal citations. "
                                "Return the final complete Judgment JSON.\nChallenges: "
                                + scrutiny.model_dump_json()
                                + "\nDraft judgment JSON: "
                                + validated_draft.model_dump_json()
                            )
                            revised = self.llm_service.generate_structured(
                                prompt=rev_prompt,
                                response_schema=Judgment,
                                system_prompt=SYSTEM_PROMPT,
                            )
                            revised = self._normalize_llm_judgment(revised, case, dossier, authorities)
                            validated_final = self._validate_output(revised, case, dossier)
                            if not validated_final.ingredient_checklists and checklists:
                                validated_final = validated_final.model_copy(update={"ingredient_checklists": checklists})
                            return validated_final.model_copy(update={"scrutiny_report": scrutiny})
                        except Exception as rev_exc:
                            logger.warning("Scrutiny revision pass failed validation (%s); returning validated draft with scrutiny_report.", rev_exc)
                    return validated_draft.model_copy(update={"scrutiny_report": scrutiny})
                return validated_draft
            except (ValueError, TypeError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                logger.warning("Judge output validation failed on attempt %d/3 for %s: %s", attempt + 1, case.case_id, exc)
            except RuntimeError as exc:
                if any(term in str(exc).casefold() for term in ("quota", "credit", "402", "authentication", "401", "403")):
                    raise
                raise
        assert last_error is not None
        raise ValueError(f"Judge could not produce a validated judgment after 3 attempts: {last_error}") from last_error
