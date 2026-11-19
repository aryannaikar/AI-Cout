"""
Judgment Extractor and Normalizer for Phase 5 — AI Court Judgment Comparison Engine.
Normalizes both structured AI judgments and raw/semi-structured Real Court judgments
into a standardized NormalizedJudgment intermediate representation.
Guarantees robust exclusion of footers, page metadata, and boilerplate.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.comparison.schemas import (
    EpistemicType,
    NormalizedCharge,
    NormalizedEvidenceItem,
    NormalizedFact,
    NormalizedIssue,
    NormalizedJudgment,
    NormalizedParty,
    NormalizedReasoning,
    NormalizedWitness,
    OperativeVerdict,
    StatuteEra,
)
from app.models.judgment_models import Judgment

logger = logging.getLogger(__name__)

FOOTER_METADATA_PATTERNS = [
    r"AI Court of India\s*\|\s*Source:[^\n]*",
    r"AI COURT OF INDIA\s*\|\s*Case benchmark:[^\n]*",
    r"CONFIDENTIAL EVALUATION FILE[^\n]*",
    r"CONFIDENTIAL[^\n]*DO NOT UPLOAD[^\n]*",
    r"Keep this file separate from the Case Packet[^\n]*",
    r"Never add it to live CourtState[^\n]*",
    r"Page\s+\d+(\s+of\s+\d+)?",
    r"Comparison Engine Ground Truth",
    r"Source and Evaluation Controls",
]


class JudgmentNormalizer:
    """
    Transforms heterogeneous judgment representations into a canonical NormalizedJudgment.
    Preserves all 18 judicial facets while ensuring strict determinism and reliability.
    """

    @classmethod
    def normalize_ai_judgment(
        cls, ai_input: Union[Judgment, dict, str]
    ) -> NormalizedJudgment:
        """
        Normalize an AI Judgment (Pydantic model, dictionary, or formatted string).
        """
        if isinstance(ai_input, str):
            clean_str = ai_input.strip()
            if clean_str.startswith("{") and clean_str.endswith("}"):
                try:
                    data = json.loads(clean_str)
                    j_obj = Judgment.model_validate(data)
                    return cls._normalize_from_judgment_model(j_obj)
                except Exception:
                    pass
            return cls._normalize_from_text(ai_input, is_ai=True)

        if isinstance(ai_input, dict):
            try:
                judgment_obj = Judgment.model_validate(ai_input)
                return cls._normalize_from_judgment_model(judgment_obj)
            except Exception:
                return cls._normalize_from_dict(ai_input)

        if isinstance(ai_input, Judgment):
            return cls._normalize_from_judgment_model(ai_input)

        raise ValueError(f"Unable to normalize AI Judgment of type: {type(ai_input)}")

    @classmethod
    def normalize_real_judgment(
        cls, real_input: Union[dict, str]
    ) -> NormalizedJudgment:
        """
        Normalize a Real Court Judgment (structured dictionary or raw text from PDF/TXT).
        """
        if isinstance(real_input, dict):
            try:
                return NormalizedJudgment.model_validate(real_input)
            except Exception:
                return cls._normalize_from_dict(real_input)

        if isinstance(real_input, str):
            clean_str = real_input.strip()
            if clean_str.startswith("{") and clean_str.endswith("}"):
                try:
                    data = json.loads(clean_str)
                    if "verdict" in data and "case_title" in data:
                        return NormalizedJudgment.model_validate(data)
                    return cls._normalize_from_dict(data)
                except Exception:
                    pass
            return cls._normalize_from_text(real_input, is_ai=False)

        raise ValueError(f"Unable to normalize Real Judgment of type: {type(real_input)}")

    # --------------------------------------------------------------------------
    # Text Cleaning & Provenance
    # --------------------------------------------------------------------------

    @classmethod
    def _clean_text_and_detect_summary(cls, text: str) -> Tuple[str, Optional[str], bool]:
        """
        Separate main substantive judgment from evaluation/comparison controls.
        Returns: (substantive_text, evaluation_controls_block, is_ground_truth_summary)
        """
        is_summary = bool(
            re.search(r"Ground Truth\s*[\u2013\-]", text, re.IGNORECASE)
            or re.search(r"1\.\s*(?:Operative Verdict|Ground-truth identity)", text, re.IGNORECASE)
            or re.search(r"Comparison Engine Ground Truth", text, re.IGNORECASE)
            or re.search(r"STRICT ISOLATION:\s*This document contains", text, re.IGNORECASE)
            or re.search(r"Case benchmark:", text, re.IGNORECASE)
        )

        # Strip Ground Truth isolation preamble before numbered sections
        cleaned = re.sub(
            r"STRICT ISOLATION:.*?(?=\n\s*(?:1\.|2\.|3\.|4\.|5\.))",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Separate Section 5/6/7/8 Evaluation Controls / Comparison Matrix if present
        eval_match = re.search(
            r"(\n\s*(?:5\.\s*Ground-truth comparison matrix|6\.\s*(?:Comparison Engine Ground Truth|Phase 5|Evaluation)|7\.\s*(?:Source and Evaluation Controls|Important source limitations)|8\.\s*Isolation and evaluation workflow).*)\Z",
            cleaned,
            re.DOTALL | re.IGNORECASE,
        )
        if eval_match:
            substantive = cleaned[: eval_match.start()]
            eval_block = eval_match.group(1).strip()
        else:
            substantive = cleaned
            eval_block = None

        return substantive.strip(), eval_block, is_summary

    # --------------------------------------------------------------------------
    # Structured AI Judgment Model Normalization
    # --------------------------------------------------------------------------

    @classmethod
    def _normalize_from_judgment_model(cls, j: Judgment) -> NormalizedJudgment:
        """Convert an existing AI Judgment Pydantic model into NormalizedJudgment."""
        verdict, explanation = cls._determine_verdict_with_explanation(j.final_decision)

        # Charges & findings
        charges: List[NormalizedCharge] = []
        findings: Dict[str, str] = {}
        for charge_key, finding_val in j.findings_per_charge.items():
            findings[charge_key] = finding_val
            era = cls._classify_statute_era(charge_key)
            charges.append(
                NormalizedCharge(
                    statute=charge_key,
                    era=era,
                    offence=charge_key,
                    finding=finding_val,
                )
            )

        # Also include penal charges referenced in applicable_law when not already represented by section number
        has_railway_fpc = any("railway property" in k.lower() for k in j.findings_per_charge)
        existing_charge_secs = set()
        for ch in charges:
            for m_sec in re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", ch.statute):
                if m_sec not in {"1860", "1872", "1966", "1973", "2023"}:
                    existing_charge_secs.add(m_sec.lower())
        if j.applicable_law:
            for law in j.applicable_law:
                if has_railway_fpc and re.search(r"\b(?:379|411|102|114)\b", law):
                    continue
                if any(k in law for k in ["IPC", "Indian Penal Code", "BNS", "Bharatiya Nyaya", "Arms Act", "Railway Property"]) and not any(ev in law for ev in ["Evidence Act", "BSA", "Sakshya", "CrPC", "BNSS"]):
                    law_secs = [s.lower() for s in re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", law) if s not in {"1860", "1872", "1966", "1973", "2023"}]
                    if law_secs and not any(s in existing_charge_secs for s in law_secs):
                        charges.append(
                            NormalizedCharge(
                                statute=law,
                                era=cls._classify_statute_era(law),
                                offence=law,
                                finding=j.final_decision,
                            )
                        )
                        existing_charge_secs.update(law_secs)

        # Legal issues
        issues: List[NormalizedIssue] = []
        if j.issue_analyses:
            for analysis in j.issue_analyses:
                issues.append(
                    NormalizedIssue(
                        issue_id=f"Issue-{analysis.issue_number}",
                        statement=analysis.issue_statement.strip(),
                        applicable_law=analysis.applicable_law,
                        finding=analysis.judicial_finding,
                        reasoning_summary=analysis.evidentiary_evaluation,
                    )
                )
        else:
            for idx, issue_stmt in enumerate(j.issues_for_determination, start=1):
                issues.append(
                    NormalizedIssue(
                        issue_id=f"Issue-{idx}",
                        statement=issue_stmt.strip(),
                    )
                )

        # Material facts (combine case background with evidentiary/witness narrative)
        fact_source = "\n".join(filter(None, [j.case_background, j.evidence_assessment, j.witness_assessment]))
        facts = cls._extract_facts_from_text(fact_source)

        # Witnesses (scan witness_assessment, evidence_assessment, and case_background)
        witness_source = "\n".join(filter(None, [j.witness_assessment, j.evidence_assessment, j.case_background]))
        witnesses = cls._extract_witnesses_from_text(witness_source)
        pros_witnesses = [w for w in witnesses if not w.witness_id.startswith("DW")]
        def_witnesses = [w for w in witnesses if w.witness_id.startswith("DW")]

        # Evidence items
        evidence_items = cls._extract_evidence_from_text(j.evidence_assessment)

        # Legal provisions
        provisions = list(dict.fromkeys(j.applicable_law + j.legal_citations))
        is_railway_case = any("railway property" in c.statute.lower() for c in charges) and not any(
            re.search(r"\b(?:379|411)\b", c.statute) for c in charges
        )
        if is_railway_case:
            provisions = [p for p in provisions if not re.search(r"\b(?:379|411|102|114)\b", p)]
        if any(c.era == StatuteEra.HISTORICAL_IPC_CRPC for c in charges):
            provisions = [p for p in provisions if not ("119" in p and ("bsa" in p.lower() or "evidence" in p.lower() or "sakshya" in p.lower()))]

        # Reasoning (combine reasons with per-issue analyses)
        reasons_text = j.reasons or ""
        issue_reason_chains = [
            f"{a.issue_statement} {a.judicial_finding} {a.evidentiary_evaluation}".strip()
            for a in (j.issue_analyses or [])
            if (a.issue_statement or a.evidentiary_evaluation)
        ]
        key_chains = list(dict.fromkeys(cls._extract_chains_of_reasoning(reasons_text) + issue_reason_chains))
        reasoning = NormalizedReasoning(
            ratio_decidendi=reasons_text,
            key_chains=key_chains,
            evaluated_credibility=bool("credibility" in j.witness_assessment.lower() or "caution" in j.witness_assessment.lower() or len(witnesses) > 0),
            evaluated_contradictions=bool("contradiction" in reasons_text.lower() or "conflict" in reasons_text.lower() or "inconsisten" in reasons_text.lower()),
            evaluated_missing_evidence=bool("absence" in j.evidence_assessment.lower() or "missing" in j.evidence_assessment.lower() or "gap" in j.evidence_assessment.lower() or "independent" in j.witness_assessment.lower() or "absence" in reasons_text.lower()),
            connected_evidence_to_findings=bool(len(j.issue_analyses) > 0),
        )

        parties = cls._extract_parties_from_title(j.case_title)
        final_order = f"VERDICT: {j.final_decision}. {reasons_text[:800]}".strip()

        return NormalizedJudgment(
            case_title=j.case_title,
            case_number=j.judgment_id,
            presiding_court=j.presiding_court,
            date_of_decision=j.date_of_decision,
            verdict=verdict,
            verdict_raw=j.final_decision,
            verdict_normalization_explanation=explanation,
            final_order=final_order,
            parties=parties,
            charges=charges,
            material_facts=facts,
            legal_issues=issues,
            prosecution_witnesses=pros_witnesses,
            defence_witnesses=def_witnesses,
            evidence_items=evidence_items,
            legal_provisions=provisions,
            prosecution_arguments=[j.prosecution_submissions] if j.prosecution_submissions else [],
            defence_arguments=[j.defense_submissions] if j.defense_submissions else [],
            findings=findings,
            reasoning=reasoning,
            raw_text=reasons_text,
            is_ground_truth_summary=False,
        )

    # --------------------------------------------------------------------------
    # Unstructured / Semi-Structured Text Normalization
    # --------------------------------------------------------------------------

    @classmethod
    def _normalize_from_text(cls, text: str, is_ai: bool = False) -> NormalizedJudgment:
        """Parse raw legal judgment text or ground truth summary into NormalizedJudgment."""
        substantive_text, eval_block, is_summary = cls._clean_text_and_detect_summary(text)

        case_title = cls._extract_case_title(substantive_text)
        case_number = cls._extract_case_number(substantive_text)
        presiding_court = cls._extract_court_name(substantive_text)
        date_of_decision = cls._extract_date(substantive_text)
        parties = cls._extract_parties_from_title(case_title)

        verdict, raw_verdict, final_order, explanation = cls._extract_verdict_and_order(substantive_text)
        charges = cls._extract_charges(substantive_text)
        issues = cls._extract_issues(substantive_text, eval_block=eval_block)
        facts = cls._extract_facts_from_text(substantive_text)

        witnesses = cls._extract_witnesses_from_text(substantive_text)
        pros_witnesses = [w for w in witnesses if not w.witness_id.startswith("DW")]
        def_witnesses = [w for w in witnesses if w.witness_id.startswith("DW")]

        evidence_items = cls._extract_evidence_from_text(substantive_text)
        provisions = cls._extract_provisions(substantive_text)
        reasoning = cls._extract_reasoning_structure(substantive_text, eval_block=eval_block)

        findings: Dict[str, str] = {}
        for ch in charges:
            # Do not copy the global operative verdict onto every section
            # mentioned in a judgment; many may concern procedural history or
            # different accused. Only retain an explicit charge-level finding.
            charge_finding = ch.finding or cls._extract_explicit_charge_finding(substantive_text, ch.statute)
            if charge_finding:
                ch.finding = charge_finding
                findings[ch.statute] = charge_finding

        extraction_warnings: List[str] = []
        if is_summary:
            extraction_warnings.append("Document identified as Ground Truth summary; witness/exhibit rosters may be summarized.")
        if not witnesses and is_summary:
            extraction_warnings.append("No individual witness depositions extractable from summary document.")
        if not evidence_items and is_summary:
            extraction_warnings.append("No exhibit-by-exhibit inventory present in summary document.")

        return NormalizedJudgment(
            case_title=case_title,
            case_number=case_number,
            presiding_court=presiding_court,
            date_of_decision=date_of_decision,
            verdict=verdict,
            verdict_raw=raw_verdict,
            verdict_normalization_explanation=explanation,
            final_order=final_order,
            parties=parties,
            charges=charges,
            material_facts=facts,
            legal_issues=issues,
            prosecution_witnesses=pros_witnesses,
            defence_witnesses=def_witnesses,
            evidence_items=evidence_items,
            legal_provisions=provisions,
            prosecution_arguments=cls._extract_arguments(substantive_text, side="prosecution"),
            defence_arguments=cls._extract_arguments(substantive_text, side="defence"),
            findings=findings,
            reasoning=reasoning,
            raw_text=text,
            is_ground_truth_summary=is_summary,
            extraction_warnings=extraction_warnings,
        )

    @classmethod
    def _extract_explicit_charge_finding(cls, text: str, statute: str) -> Optional[str]:
        """Extract a disposition only when it is explicitly attached to a charge reference."""
        section_match = re.search(r"\b([0-9]{1,4}[A-Za-z]?)\b", statute)
        if not section_match:
            return None
        section = re.escape(section_match.group(1))
        patterns = (
            rf"(?:section|sec\.?|u/s)\s*{section}\s*(?:of\s+the\s+)?(?:ipc|indian penal code|bns)?\s*[:—-]\s*([^\n.;]{{1,100}})",
            rf"(?:section|sec\.?|u/s)\s*{section}\s+(?:was|is|stands?)\s+(acquitted|not guilty|not proved|not proven|convicted|guilty|upheld|affirmed|set aside)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if re.search(r"\b(acquitt|not guilty|not prov(?:ed|en)|convict|guilty|upheld|affirmed|set aside)\b", candidate, re.IGNORECASE):
                    return candidate
        return None

    @classmethod
    def _normalize_from_dict(cls, data: dict[str, Any]) -> NormalizedJudgment:
        """Handle loosely structured dictionary representation."""
        title = data.get("case_title") or data.get("title") or "State v. Accused"
        raw_verdict = data.get("verdict") or data.get("final_decision") or data.get("outcome") or ""
        verdict, explanation = cls._determine_verdict_with_explanation(str(raw_verdict))

        charges: List[NormalizedCharge] = []
        for ch in data.get("charges", []):
            if isinstance(ch, str):
                charges.append(NormalizedCharge(statute=ch, era=cls._classify_statute_era(ch), offence=ch))
            elif isinstance(ch, dict):
                statute = ch.get("statute", "")
                charges.append(
                    NormalizedCharge(
                        statute=statute,
                        era=cls._classify_statute_era(statute),
                        offence=ch.get("offence", statute),
                        finding=ch.get("finding"),
                        accused_name=ch.get("accused_name"),
                    )
                )

        issues: List[NormalizedIssue] = []
        for idx, iss in enumerate(data.get("issues", []) or data.get("issues_for_determination", []), start=1):
            if isinstance(iss, str):
                issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=iss))
            elif isinstance(iss, dict):
                issues.append(NormalizedIssue(**iss))

        provisions = data.get("legal_provisions") or data.get("applicable_law") or []

        return NormalizedJudgment(
            case_title=title,
            case_number=data.get("case_number") or data.get("judgment_id"),
            presiding_court=data.get("presiding_court") or data.get("court"),
            date_of_decision=data.get("date_of_decision") or data.get("date"),
            verdict=verdict,
            verdict_raw=str(raw_verdict),
            verdict_normalization_explanation=explanation,
            final_order=data.get("final_order") or str(raw_verdict),
            parties=cls._extract_parties_from_title(title),
            charges=charges,
            legal_issues=issues,
            legal_provisions=list(provisions) if isinstance(provisions, list) else [str(provisions)],
            findings=data.get("findings") or {},
            reasoning=NormalizedReasoning(ratio_decidendi=data.get("reasons") or data.get("ratio_decidendi") or ""),
            raw_text=json.dumps(data),
        )

    # --------------------------------------------------------------------------
    # Specialized Legal Parsing & Classification Heuristics
    # --------------------------------------------------------------------------

    @classmethod
    def _determine_verdict_with_explanation(cls, text: str) -> Tuple[OperativeVerdict, str]:
        """
        Classify operative verdict from judicial outcome string and document the normalization rationale.
        Normalizes equivalent expressions (e.g. 'acquitted', 'acquittal', 'appellant was acquitted of all charges')
        to canonical outcomes.
        Distinguishes genuine substantive 'OTHER' from failed extraction (EXTRACTION_ERROR) or unrecognized text (UNKNOWN).
        """
        if not text or not text.strip():
            return OperativeVerdict.EXTRACTION_ERROR, "Extraction failed: Operative text is empty or missing."

        raw_trimmed = text.strip()
        t = raw_trimmed.upper()

        # Check for boilerplate indicating missing extraction
        if any(bp in t for bp in [
            "OPERATIVE ORDER NOT EXPLICITLY DETAILED",
            "NO OPERATIVE ORDER",
            "OPERATIVE ORDER NOT FOUND",
            "NOT EXPLICITLY DETAILED IN JUDGMENT TEXT",
            "EXTRACTION ERROR",
            "EXTRACTION_ERROR",
        ]):
            return OperativeVerdict.EXTRACTION_ERROR, "Extraction failed: Judgment text contains no extractable operative order or verdict."

        # 1. ACQUITTAL & CONVICTION-OVERTURNING VARIANTS
        # Explicit acquittal expressions
        is_explicit_acquittal = bool(
            re.search(
                r"\b(?:ACQUITT(?:ED|AL|ING|S)?|HONOUR?ABLY\s+ACQUITTED|ACQUITTAL\s+OF\s+ALL\s+CHARGES|ACQUITTED\s+OF\s+ALL\s+CHARGES|ACQUITTED\s+OF\s+(?:THE\s+)?CHARGES|ACQUITTED\s+UNDER\s+SECTION|BENEFIT\s+OF\s+DOUBT|NOT\s+GUILTY)\b",
                t,
            )
        )

        # Setting aside conviction expressions
        is_conviction_set_aside = bool(
            re.search(
                r"(?:CONVICTION|JUDGMENT\s+(?:UNDER\s+CHALLENGE|OF\s+CONVICTION|IMPUGNED)|FINDING\s+OF\s+GUILT|SENTENCE)[^\n.]*?\b(?:IS|WAS|STANDS|BE)?\s*(?:SET\s+ASIDE|QUASHED|REVERSED)\b|\bSET\s+ASIDE\b[^\n.]*?(?:CONVICTION|JUDGMENT|FINDING|SENTENCE)",
                t,
            )
            or ("SET ASIDE" in t and any(term in t for term in ["APPEAL IS ALLOWED", "APPEAL ALLOWED", "APPELLANT", "ACCUSED", "DISCHARGED", "BAIL BONDS"]))
        )

        if is_explicit_acquittal or is_conviction_set_aside:
            matched_phrase = "acquittal of charges" if is_explicit_acquittal else "setting aside of conviction/judgment"
            return (
                OperativeVerdict.ACQUITTAL,
                f"Normalized to canonical ACQUITTAL: Source text contains {matched_phrase} ('{raw_trimmed[:120]}').",
            )

        # 2. PARTIAL CONVICTION
        if any(term in t for term in ["PARTIAL CONVICTION", "PARTLY ALLOWED", "ALLOWED IN PART", "CONVICTED IN PART"]):
            return (
                OperativeVerdict.PARTIAL_CONVICTION,
                f"Normalized to PARTIAL_CONVICTION: Appellate outcome modified to partial conviction ('{raw_trimmed[:120]}').",
            )

        # 3. APPEAL / PETITION / APPLICATION / BAIL ALLOWED (When not overturning conviction/acquittal)
        is_bail_or_petition_allowed = bool(
            re.search(
                r"\b(?:ENLARGE[D]?\s+(?:THE\s+)?(?:PETITIONER|ACCUSED|APPLICANT)\s+ON\s+(?:ANTICIPATORY\s+)?BAIL|RELEASED\s+ON\s+(?:ANTICIPATORY\s+)?BAIL|(?:ANTICIPATORY\s+)?BAIL\s+(?:APPLICATION\s+)?(?:IS\s+|STANDS\s+)?(?:GRANTED|ALLOWED)|(?:CRIMINAL\s+)?(?:PETITION|APPLICATION)\s+(?:IS\s+|WAS\s+|STANDS\s+)?ALLOWED|SENTENCE\b[^\n.]*\b(?:WAS|IS)\s+SUSPENDED)\b",
                t,
            )
        )
        if "APPEAL IS ALLOWED" in t or "APPEAL ALLOWED" in t or t == "ALLOWED" or is_bail_or_petition_allowed:
            return (
                OperativeVerdict.APPEAL_ALLOWED,
                f"Normalized to APPEAL_ALLOWED: Court allowed the petition / granted bail ('{raw_trimmed[:120]}').",
            )

        # 4. APPEAL / APPLICATION DISMISSED OR BAIL REJECTED
        is_bail_rejected = bool(
            re.search(
                r"\b(?:(?:BAIL\s+)?APPLICATION\s+(?:IS\s+|STANDS\s+)?(?:REJECTED|DISMISSED)|NOT\s+INCLINED\s+TO\s+GRANT\s+(?:ANTICIPATORY\s+)?BAIL)\b",
                t,
            )
        )
        if "APPEAL IS DISMISSED" in t or "APPEAL DISMISSED" in t or "DISMISSED" in t or is_bail_rejected:
            return (
                OperativeVerdict.APPEAL_DISMISSED,
                f"Normalized to APPEAL_DISMISSED: Court dismissed/rejected the appeal or bail application ('{raw_trimmed[:120]}').",
            )

        # 5. CONVICTION
        if bool(re.search(r"\b(?:CONVICT(?:ED|ION|ING)?|FOUND\s+GUILTY|HELD\s+GUILTY|GUILTY)\b", t)):
            return (
                OperativeVerdict.CONVICTION,
                f"Normalized to CONVICTION: Accused found guilty / conviction affirmed ('{raw_trimmed[:120]}').",
            )

        # 6. DISCHARGE
        if "DISCHARGE" in t:
            return (
                OperativeVerdict.DISCHARGE,
                f"Normalized to DISCHARGE: Accused discharged from criminal liability ('{raw_trimmed[:120]}').",
            )

        # 7. REMAND
        if "REMAND" in t:
            return (
                OperativeVerdict.REMAND,
                f"Normalized to REMAND: Matter remanded back to lower court ('{raw_trimmed[:120]}').",
            )

        # 8. SENTENCE MODIFIED
        if "MODIFIED" in t or "REDUCED" in t or "PERIOD ALREADY UNDERGONE" in t:
            return (
                OperativeVerdict.SENTENCE_MODIFIED,
                f"Normalized to SENTENCE_MODIFIED: Sentence altered without altering finding of guilt ('{raw_trimmed[:120]}').",
            )

        # 9. RECOGNIZED SUBSTANTIVE "OTHER" DISPOSITIONS
        if any(sub in t for sub in ["COMPOUNDED", "ABATED", "PROBATION", "SETTLED", "REFERRED TO LARGER BENCH", "QUASHED"]):
            return (
                OperativeVerdict.OTHER,
                f"Normalized to substantive OTHER: Non-standard judicial disposition ('{raw_trimmed[:120]}').",
            )

        # 10. UNRECOGNIZED / EXTRACTION INCOMPLETE
        return (
            OperativeVerdict.UNKNOWN,
            f"Unrecognized verdict text: The extracted string ('{raw_trimmed[:120]}') contains no standard operative disposition terms; recorded as UNKNOWN instead of substantive OTHER.",
        )

    @classmethod
    def _determine_verdict(cls, text: str) -> OperativeVerdict:
        """Classify operative verdict from judicial outcome string."""
        verdict, _ = cls._determine_verdict_with_explanation(text)
        return verdict

    @classmethod
    def _classify_statute_era(cls, text: str) -> StatuteEra:
        """Detect whether statutory reference belongs to historical IPC/CrPC or modern BNS/BNSS."""
        t = text.upper()
        if any(term in t for term in ["IPC", "INDIAN PENAL CODE", "CRPC", "CRIMINAL PROCEDURE CODE", "EVIDENCE ACT, 1872", "IEA", "INDIAN EVIDENCE ACT"]):
            return StatuteEra.HISTORICAL_IPC_CRPC
        if any(term in t for term in ["BNS", "BHARATIYA NYAYA SANHITA", "BNSS", "BHARATIYA NAGARIK", "BSA", "BHARATIYA SAKSHYA"]):
            return StatuteEra.MODERN_BNS_BNSS_BSA
        if any(term in t for term in ["ARMS ACT", "NDPS", "POCSO", "IT ACT", "MOTOR VEHICLES", "PREVENTION OF CORRUPTION", "RAILWAY PROPERTY", "R.P.(U.P.)", "RP(UP)"]):
            return StatuteEra.SPECIAL_ACT
        return StatuteEra.OTHER

    @classmethod
    def _extract_case_title(cls, text: str) -> str:
        """Extract case title from heading or header lines."""
        for line in text.split("\n"):
            line = line.strip()
            # Ignore headers
            if any(term in line.lower() for term in ["ai court of india", "source:", "ground truth", "page "]):
                continue
            m = re.match(
                r"^([A-Z][A-Za-z0-9\s\.\(\)\/]+?\s+(?:v\.|vs\.|versus)\s+[A-Z][A-Za-z0-9\s\.\(\)\/]+?)(?:\s+(?:Date|Crl|Sessions|FIR|No\.|\|)|$)",
                line,
                re.IGNORECASE,
            )
            if m:
                clean = m.group(1).strip()
                if len(clean) < 100:
                    return clean

        m2 = re.search(r"Case:\s*([^\n]+)", text)
        if m2:
            return m2.group(1).strip()

        # Multi-line court caption: "<Party> ... Versus ... <Party>"
        head = re.sub(r"[ \t]+", " ", text[:4000])
        m3 = re.search(
            r"([A-Z][A-Za-z\.\s]{2,60}?)\s*\.{0,}\s*(?:Petitioners?|Appellants?|Applicants?)?\s*[\r\n]+\s*(?:v\.|vs\.?|versus)\s*[\r\n]*\s*([A-Z][A-Za-z\.\s]{2,60}?)\s*(?:\.{2,}|[\r\n]|Respondents?|Opposite)",
            head,
            re.IGNORECASE,
        )
        if m3:
            a = re.sub(r"\s+", " ", m3.group(1)).strip(" .")
            a = re.sub(r"(?i)^in the\s+(?:high|supreme|sessions|district)?\s*court(?:\s+(?:of|at)\s+(?:judicature\s+at\s+)?[A-Za-z]+)?\s+", "", a)
            b = re.sub(r"\s+", " ", m3.group(2)).strip(" .")
            if a and b:
                return f"{a} v. {b}"

        # Fall back to the case number so cases stay distinguishable
        num = cls._extract_case_number(text)
        if num:
            return num.strip()
        return "State v. Accused"

    @classmethod
    def _extract_case_number(cls, text: str) -> Optional[str]:
        """Extract court appeal or case number."""
        m = re.search(r"((?:Criminal Appeal|Crl\.A\.|Sessions Case|Civil Appeal|SLP|W\.P\.)\s*(?:No\.)?\s*[0-9\/\-]+(?:\s*of\s*[0-9]{4})?)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    @classmethod
    def _extract_court_name(cls, text: str) -> Optional[str]:
        """Extract court name from standard header formulas or pipe banners."""
        # 1. Check pipe line format: e.g. "... | Supreme Court of India | 19 August 2025"
        for line in text.split("\n"):
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                for p in parts:
                    if any(term in p.lower() for term in ["supreme court of india", "high court", "court of sessions"]):
                        return p

        # 2. Match standard "IN THE SUPREME COURT OF INDIA" or "SUPREME COURT OF INDIA"
        m = re.search(r"((?:IN THE\s+)?(?:SUPREME COURT OF INDIA|HIGH COURT OF [A-Z\s]+|COURT OF SESSIONS[A-Z\s]*))", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return "Court of Sessions / High Court"

    @classmethod
    def _extract_date(cls, text: str) -> Optional[str]:
        """Extract judgment decision date."""
        # 1. Check pipe line: e.g. "Criminal Appeal No. 3605 of 2025 | Supreme Court of India | 19 August 2025"
        for line in text.split("\n"):
            if "|" in line:
                m_pipe = re.search(r"\|\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})\b", line)
                if m_pipe:
                    return m_pipe.group(1).strip()

        # 2. Standard labeled date
        m = re.search(r"(?:Date of Decision|Decided on|Judgment dated|Date):\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+\d{1,2},\s*\d{4})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # 3. Direct date mention near header
        m_head = re.search(r"\b([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{4})\b", text[:1200], re.IGNORECASE)
        if m_head:
            return m_head.group(1).strip()

        return None

    @classmethod
    def _extract_parties_from_title(cls, title: str) -> NormalizedParty:
        """Parse party names from formal caption."""
        parts = re.split(r"\s+(?:v\.|vs\.|versus)\s+", title, flags=re.IGNORECASE)
        if len(parts) == 2:
            return NormalizedParty(appellant_or_accused=parts[0].strip(), respondent_or_state=parts[1].strip())
        return NormalizedParty()

    @classmethod
    def _is_footer_or_metadata(cls, text_block: str) -> bool:
        """Check whether candidate text is actually footer/comparison metadata rather than an operative order."""
        t_lower = text_block.lower()
        if any(term in t_lower for term in [
            "comparison engine ground truth",
            "source and evaluation controls",
            "keep this file separate from the case packet",
            "never add it to live courtstate",
            "confidential evaluation file",
            "source: supplied supreme court judgment",
            "case benchmark:",
            "source limitations for evaluation",
            "isolation and evaluation workflow",
            "if an ai output does not contain enough information",
            "do not silently supplement",
            "do not calculate an overall percentage",
            "preserve the original ai output",
            "run the live ai court using only",
            "persist the ai judgment and its structured",
            "only after persistence, load this ground truth",
            "compare the ai output against each evaluation dimension",
            "relevant reasoning and final order appear on pages",
        ]):
            return True
        if re.search(
            r"^(?:page\s+\d+|coram\s*:|for the (?:petitioner|state|appellant|respondent)\s*:|order\s+no\.|dated\s*:|in the (?:high|supreme) court\b|versus\b|\.\.\.)",
            text_block.strip(),
            re.IGNORECASE,
        ):
            return True
        if re.search(r"(?:\.{2,}|·\.\.)\s*(?:petitioner|opposite party|appellant|respondent)\s*$", text_block.strip(), re.IGNORECASE):
            return True
        return False

    @classmethod
    def _extract_verdict_and_order(cls, text: str) -> Tuple[OperativeVerdict, str, str, str]:
        """
        Extract operative outcome, original source snippet, final order text, and normalization explanation.
        Guarantees footer and comparison metadata are NEVER returned as final operative order.
        Normalizes equivalent expressions (e.g. 'acquitted', 'acquittal', 'appellant was acquitted of all charges')
        to canonical outcomes.
        Never classifies missing or unrecognized text as substantive OTHER; returns EXTRACTION_ERROR or UNKNOWN instead.
        """
        raw_verdict_candidate = ""
        final_order = ""
        source_snippet = ""
        explanation = ""

        # 1. Look for explicit summary heading (e.g. "1. Operative Verdict", "Verdict:", "FINAL DECISION:")
        m_op_verdict = re.search(
            r"(?:1\.\s*Operative Verdict|(?:\n|^)\s*(?:Operative\s+)?Verdict\s*:|FINAL DECISION|OUTCOME\s*:)[:\s\n]+([^\n]+)(?:\n(.*?)(?=(?:\n\s*2\.|\n\n[A-Z\s]{4,}|\Z)))?",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m_op_verdict:
            raw_verdict_candidate = m_op_verdict.group(1).strip()
            if m_op_verdict.group(2):
                cand2 = m_op_verdict.group(2).strip()
                if cand2 and not cls._is_footer_or_metadata(cand2):
                    final_order = cand2

        # 2. Look for explicit Final Order section (e.g. "5. Final Order" or "Operative Order:")
        m_explicit = re.search(
            r"(?:(?:5\.\s*|SECTION\s*10:\s*)?Final Order|Operative Order|ORDER FOR DISPOSAL|Operative Part|OPERATIVE PORTION)[:\s\n]+(.*?)(?=(?:\n\s*[0-9]\.|\n\n[A-Z\s]{4,}|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m_explicit:
            candidate = m_explicit.group(1).strip()
            # Clean bullet marks, unicode replacement bullets, and page numbers
            cleaned_candidate = "\n".join(
                line.strip(" \t•\u2022\ufffd-*") for line in candidate.split("\n")
                if line.strip() and not cls._is_footer_or_metadata(line)
            ).strip()
            if cleaned_candidate and not cls._is_footer_or_metadata(cleaned_candidate):
                final_order = cleaned_candidate

        # 3. If final_order still not found, search closing paragraphs backwards (skipping footers)
        if not final_order:
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in reversed(paras):
                if cls._is_footer_or_metadata(p):
                    continue
                if any(w in p.lower() for w in ["acquitt", "allowed", "set aside", "dismissed", "rejected", "convict", "discharged", "bail bonds", "benefit of doubt", "anticipatory bail", "released on bail", "enlarge", "not inclined to grant bail"]):
                    final_order = p
                    break

        # 4. If still not found, scan substantive sentences for direct outcome statements
        if not final_order:
            m_sent = re.search(
                r"((?:in the result|consequently|for the reasons|accordingly)[^.\n]*?(?:appeal is allowed|appellant is acquitted|conviction is set aside|acquitted of all charges)[^.\n]*\.)",
                text,
                re.IGNORECASE,
            )
            if m_sent:
                final_order = m_sent.group(1).strip()
            else:
                m_acq = re.search(
                    r"([^\n.]*?\b(?:appellant|accused)\s+(?:is|was)\s+acquitted[^\n.]*\.)",
                    text,
                    re.IGNORECASE,
                )
                if m_acq:
                    final_order = m_acq.group(1).strip()

        # Fallback if still empty
        if not final_order:
            final_order = "Operative order not explicitly detailed in judgment text."

        # Determine verdict and normalization explanation
        verdict = OperativeVerdict.EXTRACTION_ERROR

        # Try evaluating explicit candidate first
        if raw_verdict_candidate:
            v_cand, expl_cand = cls._determine_verdict_with_explanation(raw_verdict_candidate)
            if v_cand not in (OperativeVerdict.EXTRACTION_ERROR, OperativeVerdict.UNKNOWN):
                verdict = v_cand
                explanation = expl_cand
                source_snippet = raw_verdict_candidate

        # If explicit candidate didn't resolve or was missing, evaluate final_order
        if verdict in (OperativeVerdict.EXTRACTION_ERROR, OperativeVerdict.UNKNOWN) and final_order:
            v_order, expl_order = cls._determine_verdict_with_explanation(final_order)
            if v_order not in (OperativeVerdict.EXTRACTION_ERROR, OperativeVerdict.UNKNOWN):
                verdict = v_order
                explanation = expl_order
                # Find specific sentence inside final_order driving the outcome
                sentences = re.split(r"(?<=[.!?])\s+", final_order)
                for s in sentences:
                    v_s, _ = cls._determine_verdict_with_explanation(s)
                    if v_s == verdict:
                        source_snippet = s.strip()
                        break
                if not source_snippet:
                    source_snippet = final_order[:150].strip()
            else:
                # If both explicit candidate and final_order failed, check entire text for definitive acquittal statements
                m_global_acq = re.search(
                    r"([^\n.]*?\b(?:appellant|accused)\s+(?:is|was)\s+acquitted[^\n.]*\.)",
                    text,
                    re.IGNORECASE,
                )
                if m_global_acq:
                    verdict = OperativeVerdict.ACQUITTAL
                    source_snippet = m_global_acq.group(1).strip()
                    explanation = f"Normalized to canonical ACQUITTAL: Found authoritative outcome statement in judgment body ('{source_snippet}')."
                else:
                    verdict = v_order
                    explanation = expl_order
                    source_snippet = raw_verdict_candidate or (final_order if final_order != "Operative order not explicitly detailed in judgment text." else "")

        if not source_snippet:
            source_snippet = raw_verdict_candidate or (final_order if final_order != "Operative order not explicitly detailed in judgment text." else "")

        return verdict, source_snippet, final_order, explanation

    @classmethod
    def _extract_charges(cls, text: str) -> List[NormalizedCharge]:
        """
        Extract statutory charges and distinguish procedural history & accused applicability.
        """
        charges: List[NormalizedCharge] = []
        seen = set()

        # Check for accused-specific charges in procedural text
        # Capture explicit accused-to-charge attribution when source text provides it.
        m_accused_charges = re.findall(
            r"(?:against|framed against)\s+([A-Za-z\s]+?)\s+under\s+(?:Sections?|Sec\.)?\s*([0-9A-Za-z\s,and]+?)\s+(IPC|Indian Penal Code|BNS|Arms Act)",
            text,
            re.IGNORECASE,
        )
        for accused_raw, secs_raw, statute_raw in m_accused_charges:
            accused_name = accused_raw.strip()
            sec_numbers = re.findall(r"\b[0-9]{2,4}[A-Za-z]?\b", secs_raw)
            for sec in sec_numbers:
                key = f"{statute_raw.upper()} Section {sec}"
                if key not in seen:
                    seen.add(key)
                    charges.append(
                        NormalizedCharge(
                            statute=key,
                            era=cls._classify_statute_era(key),
                            offence=key,
                            accused_name=accused_name,
                            procedural_stage="trial_charge",
                        )
                    )

        # Also extract compound mentions like 'Sections 331(4), 305 & 62 of the BNS'
        for nums, statute in re.findall(
            r"Sections?\s+([0-9][0-9A-Za-z\(\)\s,&/]+?)\s*(?:of\s+)?(?:the\s+)?(IPC|Indian Penal Code|BNS|Bharatiya Nyaya Sanhita|BNSS|Bharatiya Nagarik Suraksha Sanhita|CrPC|Arms Act)(?:\s*,\s*\d{4})?",
            text,
            re.IGNORECASE,
        ):
            stat_u = statute.upper()
            stat_norm = "BNS" if ("BHARATIYA NYAYA" in stat_u or stat_u == "BNS") else ("BNSS" if ("NAGARIK SURAKSHA" in stat_u or stat_u == "BNSS") else stat_u)
            for sec in re.findall(r"(?<![A-Za-z0-9])([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?![A-Za-z0-9])", nums):
                if sec == "2023" or sec == "1860":
                    continue
                # Do not add CrPC/BNSS 438/482 procedural bail/quashing sections as substantive penal charges
                if stat_norm in {"BNSS", "CRPC"} and (sec.startswith("482") or sec.startswith("438")):
                    continue
                key = f"{stat_norm} Section {sec}"
                if key not in seen:
                    seen.add(key)
                    charges.append(
                        NormalizedCharge(
                            statute=key,
                            era=cls._classify_statute_era(key),
                            offence=key,
                        )
                    )

        # Also extract 'IPC Sections 353 and 379' (Act before plural Sections)
        for statute, nums in re.findall(
            r"\b(IPC|BNS|BNSS|CrPC|Arms Act)\s+Sections?\s+([0-9][0-9A-Za-z\(\)\s,&/]+?)(?=\.|,|\n|$|\s+The\b|\s+of\b)",
            text,
            re.IGNORECASE,
        ):
            stat_u = statute.upper()
            for sec in re.findall(r"(?<![A-Za-z0-9])([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?![A-Za-z0-9])", nums):
                if sec in {"1860", "1973", "2023"}:
                    continue
                key = f"{stat_u} Section {sec}"
                if key not in seen:
                    seen.add(key)
                    charges.append(
                        NormalizedCharge(
                            statute=key,
                            era=cls._classify_statute_era(key),
                            offence=key,
                        )
                    )

        # Standard patterns matching Indian statutory penal sections
        patterns = [
            r"(?:Section|Sec\.|u/s|U/S)\s+([0-9]+(?:\([a-z0-9]+\)|[A-Za-z])?(?:\s+(?:read with|r/w)\s+[0-9A-Za-z\(\)]+)?)\s+(?:of\s+)?(?:the\s+)?(IPC|Indian Penal Code|BNS|Bharatiya Nyaya Sanhita|Arms Act|NDPS Act|IT Act|Railway Property \(Unlawful Possession\) Act(?:,\s*1966)?|R\.P\.\(U\.P\.\)\s*Act)",
            r"(IPC|BNS|Arms Act|NDPS Act|Railway Property \(Unlawful Possession\) Act(?:,\s*1966)?)\s*(?:,)?\s*(?:Section|Sec\.)\s*([0-9]+(?:\([a-z0-9]+\)|[A-Za-z])?)",
        ]
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                groups = match.groups()
                if len(groups) == 2:
                    g0_u, g1_u = groups[0].upper(), groups[1].upper()
                    if any(act in g1_u for act in ["IPC", "INDIAN PENAL CODE", "BNS", "BHARATIYA NYAYA SANHITA", "ARMS ACT", "NDPS ACT", "IT ACT", "RAILWAY PROPERTY", "R.P.(U.P.)"]):
                        sec, statute = groups[0], groups[1]
                    else:
                        statute, sec = groups[0], groups[1]
                    statute_norm = "Railway Property (Unlawful Possession) Act, 1966" if ("RAILWAY PROPERTY" in statute.upper() or "R.P.(U.P.)" in statute.upper()) else statute.upper()
                    if statute_norm in {"CRPC", "BNSS", "CODE OF CRIMINAL PROCEDURE", "BHARATIYA NAGARIK SURAKSHA SANHITA"} and (sec.startswith("438") or sec.startswith("482")):
                        continue
                    key = f"{statute_norm} Section {sec}"
                    if key not in seen:
                        seen.add(key)
                        charges.append(
                            NormalizedCharge(
                                statute=key,
                                era=cls._classify_statute_era(key),
                                offence=key,
                            )
                        )

        # Section 4. Legal Provisions Discussed / 5. Governing Legal Principles in Ground Truth summary
        m_prov_sec = re.search(
            r"(?:(?:4|5)\.\s*(?:Legal Provisions Discussed|Governing Legal Pri(?:nciples|ovisions))|LEGAL PROVISIONS DISCUSSED|CHARGES:?)(.*?)(?=(?:\n\s*[0-9]\.|\n\n[A-Z\s]{4,}|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m_prov_sec:
            for line in m_prov_sec.group(1).split("\n"):
                line_clean = line.strip(" \t•\u2022-*")
                m_sec = re.search(r"(?:Section|Sec\.)\s+([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)\s+(?:of\s+(?:the\s+)?)?(IPC|Indian Penal Code|BNS|Arms Act|Railway Property \(Unlawful Possession\) Act|R\.P\.\(U\.P\.\)\s*Act)", line_clean, re.IGNORECASE)
                if m_sec:
                    sec, statute = m_sec.group(1), m_sec.group(2)
                    statute_norm = "Railway Property (Unlawful Possession) Act, 1966" if ("RAILWAY" in statute.upper() or "R.P." in statute.upper()) else statute.upper()
                    key = f"{statute_norm} Section {sec}"
                    if key not in seen:
                        seen.add(key)
                        charges.append(
                            NormalizedCharge(
                                statute=key,
                                era=cls._classify_statute_era(key),
                                offence=line_clean[:80],
                            )
                        )

        return charges

    @classmethod
    def _extract_issues(cls, text: str, eval_block: Optional[str] = None) -> List[NormalizedIssue]:
        """
        Extract legal issues and points for determination.
        Supports full court transcripts, '2. Issues Decided', 'Points for determination', and 'Whether...?'.
        """
        issues: List[NormalizedIssue] = []
        seen = set()

        # 1. Look for '2. Issues Decided' in Ground Truth summary
        m_issues_decided = re.search(
            r"(?:2\.\s*Issues Decided|ISSUES DECIDED:?)(.*?)(?=(?:\n\s*[0-9]\.|\n\n[A-Z\s]{4,}|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m_issues_decided:
            block = m_issues_decided.group(1)
            # Find bullet points: • Issue I — ..., • Issue II — ...
            items = re.findall(r"(?:^|\n)\s*[•\u2022\-\*]?\s*(Issue\s+[IVX0-9]+[^\n]+(?:\n[^\n•\u2022\-\*0-9]+)*)", block, re.IGNORECASE)
            for idx, item in enumerate(items, start=1):
                clean = " ".join(item.split()).strip()
                if len(clean) > 15 and clean not in seen:
                    seen.add(clean)
                    issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=clean))

        # 2. Look for 'Points for determination', 'Question before the High Court', or 'SECTION 2: POINTS FOR DETERMINATION'
        if not issues:
            m_pts = re.search(
                r"(?:SECTION 2: POINTS FOR DETERMINATION|POINTS FOR DETERMINATION|ISSUES FOR DETERMINATION|ISSUES:|Question before the (?:High|Supreme) Court)(.*?)(?=(?:\n\s*SECTION\s+\d|\n\s*[0-9]\.|\n(?:Submissions considered|Court[’']s stated basis|Final decision)|$))",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            if m_pts:
                block = m_pts.group(1)
                norm_block = re.sub(r"(?<!\n)\n(?!\s*(?:[0-9]+\.|[•\u2022\-*]|\n))", " ", block)
                items = re.findall(r"(?:^|\n)\s*(?:[0-9]+\.|\([0-9a-z]+\)|[•\u2022\-*]|Issue\s*#?[0-9]+:?)\s*([^\n]+)", norm_block)
                for idx, item in enumerate(items, start=1):
                    clean = " ".join(item.split()).strip()
                    if len(clean) > 15 and clean not in seen and not cls._is_footer_or_metadata(clean):
                        seen.add(clean)
                        issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=clean))

        # 3. Look for "Whether..." questions
        if not issues:
            whether_matches = re.findall(r"(Whether [^\n?]+\?)", text)
            for idx, q in enumerate(whether_matches[:8], start=1):
                clean = " ".join(q.split()).strip()
                if len(clean) > 15 and clean not in seen:
                    seen.add(clean)
                    issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=clean))

        # 3b. Look for revision/proceeding headings when summary uses 'High Court's reasoning — Revision ...'
        if not issues:
            rev_headings = re.findall(r"(?:High Court(?:'s)? reasoning\s*[\u2014\-]\s*|^\s*•?\s*)(Revision\s+[0-9/]+[^\n]+(?:\n[^\n•\u2022]+)?)", text, re.IGNORECASE | re.MULTILINE)
            for idx, r_stmt in enumerate(rev_headings[:6], start=1):
                clean = " ".join(r_stmt.split()).strip()
                if len(clean) > 15 and clean not in seen:
                    seen.add(clean)
                    issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=clean))

        # 4. Fallback: extract reasoning targets from evaluation block if available and issues empty
        if not issues and eval_block:
            m_targets = re.search(r"Reasoning targets:\s*([^\n]+(?:\n[^\n•\u2022\-\*0-9]+)*)", eval_block, re.IGNORECASE)
            if m_targets:
                target_text = m_targets.group(1).replace("\n", " ").strip()
                for idx, sub_issue in enumerate(re.split(r"[;]", target_text), start=1):
                    c = sub_issue.strip()
                    if len(c) > 15 and c not in seen:
                        seen.add(c)
                        issues.append(NormalizedIssue(issue_id=f"Issue-{idx}", statement=c))

        return issues

    @classmethod
    def _extract_witnesses_from_text(cls, text: str) -> List[NormalizedWitness]:
        """Extract witnesses (PW-1, DW-1, etc.), including ranges like 'PW-1 to PW-6'."""
        witnesses: List[NormalizedWitness] = []
        seen = set()

        def _add_witness(wid: str, name: str = "", deposition: str = "") -> None:
            if wid in seen:
                return
            seen.add(wid)
            designation = (
                "Official Witness"
                if any(w in deposition for w in ["Constable", "Inspector", "SI", "Police", "IO", "Engineer"])
                else "Public Witness"
            )
            witnesses.append(
                NormalizedWitness(
                    witness_id=wid,
                    name=name.strip(),
                    designation=designation,
                    testimony_summary=deposition.strip()[:300] or f"Evaluated {wid} testimony.",
                )
            )

        # Expand ranges like 'PW-1 to PW-6' or 'PW-1–PW-6'
        for rm in re.finditer(r"\b(PW|DW)-?(\d+)\s*(?:to|–|-)\s*(?:PW|DW)?-?(\d+)\b([^\n.]*)", text, re.IGNORECASE):
            prefix = rm.group(1).upper()
            start_i, end_i = int(rm.group(2)), int(rm.group(3))
            ctx = (rm.group(4) or "").strip()
            if start_i < end_i <= start_i + 30:
                for idx in range(start_i, end_i + 1):
                    _add_witness(f"{prefix}-{idx}", "", ctx or f"{prefix}-{idx} witness deposition evaluated in record.")

        pattern = re.compile(
            r"\b(PW-?[0-9]+|DW-?[0-9]+|P\.W\.\s*[0-9]+)\s*(?:[:\-\(]|\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*))?\s*([^\n;]*)",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            wid_raw = m.group(1).upper().replace(" ", "").replace(".", "")
            if not wid_raw.startswith("PW-") and wid_raw.startswith("PW"):
                wid = f"PW-{wid_raw[2:]}"
            elif not wid_raw.startswith("DW-") and wid_raw.startswith("DW"):
                wid = f"DW-{wid_raw[2:]}"
            else:
                wid = wid_raw
            _add_witness(wid, m.group(2) or "", m.group(3) or "")

        return witnesses

    @classmethod
    def _extract_evidence_from_text(cls, text: str) -> List[NormalizedEvidenceItem]:
        """Extract exhibits and documentary/physical evidence items."""
        evidence_items: List[NormalizedEvidenceItem] = []
        seen = set()

        pattern = re.compile(
            r"\b(?:Exhibit|Ex\.|Ex|Material Object No\.|MO-?)\s+([A-Z0-9\/\-]+)\s*[:\-\(]?\s*(.*?)(?=(?:\s+(?:and|,)\s+(?:Exhibit|Ex\.|Ex)|\.|\;|\n|\Z))",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            ex_num = m.group(1).strip()
            if not re.search(r"\d", ex_num):
                continue
            ex_id = f"Exhibit {ex_num}"
            desc = m.group(2).strip(" ,;:-")
            if len(desc) < 4:
                continue
            key = f"{ex_id}:{desc[:30]}"
            if key not in seen:
                seen.add(key)
                etype = "DOCUMENTARY"
                desc_lower = desc.lower()
                if any(w in desc_lower for w in ["pistol", "revolver", "cartridge", "weapon", "knife", "vehicle", "scooter", "cash", "rupees"]):
                    etype = "PHYSICAL"
                elif any(w in desc_lower for w in ["recovery memo", "seizure memo"]):
                    etype = "RECOVERY"
                elif any(w in desc_lower for w in ["call record", "call detail", "cdr", "electronic", "cctv"]):
                    etype = "ELECTRONIC"
                elif any(w in desc_lower for w in ["identification", "tip", "parade"]):
                    etype = "IDENTIFICATION"

                evidence_items.append(
                    NormalizedEvidenceItem(
                        exhibit_id=ex_id,
                        description=desc[:200],
                        evidence_type=etype,
                        admitted_or_proved=True,
                    )
                )

        if "test identification parade" in text.lower() or " tip " in text.lower():
            if not any("TIP" in e.exhibit_id for e in evidence_items):
                evidence_items.append(
                    NormalizedEvidenceItem(
                        exhibit_id="TIP-Record",
                        description="Test Identification Parade / Dock Identification",
                        evidence_type="IDENTIFICATION",
                    )
                )

        return evidence_items

    @classmethod
    def _is_non_fact_header_or_order(cls, text_line: str) -> bool:
        """Filter out titles, section headers, legal provisions, and operative verdict/order statements from facts."""
        t_clean = text_line.strip()
        t_lower = t_clean.lower()
        if cls._is_footer_or_metadata(t_clean):
            return True
        if re.search(r"^(?:[0-9]\.|\bSECTION\b|\bIssue\s+[I|V|X|0-9]+|\bWhether\b)", t_clean, re.IGNORECASE):
            return True
        if any(term in t_lower for term in [
            "ground truth", "ai court of india", "criminal appeal", "judgment dated", "decided on",
            "confidential evaluation file", "versus", " v. ", "operative verdict", "final order",
            "core reasoning", "legal provisions discussed", "set aside", "appeal was allowed",
            "acquitted of all charges", "bail bonds stood discharged", "judgment under challenge",
            "reverse burden of proof", "prosecution bore the burden", "circumstantial evidence",
            "presumption under section 114", "reasoning targets:",
            "source case:", "strict isolation:", "phase 5 must evaluate", "single case-level verdict",
            "isolation and evaluation workflow", "important source limitations",
            "real court judgment", "heard learned counsel", "opposes the petitioner",
            "coram:", "opposite party", "for the petitioner", "for the state", "advocate", "a.p.p",
            "ground-truth case identification", "neutral citation:", "order pronounced:",
            "police case:", "underlying conviction:", "question before the high court",
            "final decision / operative order", "phase 5 evaluation metrics",
            "correct interpretation for comparison",
            "furnishing bail bond", "sureties of the like amount", "personal recognizance bond",
            "two consecutive defaults", "to the satisfaction of", "cancellation of bail",
            "subject to the conditions", "enlarge the petitioner", "inclined to grant",
            "privilege of anticipatory bail", "surrender before the", "arrest/surrender within",
            "bailor was to be", "desist from committing", "not to induce, promise",
            "remain present before the trial", "satish/-", "order dated:",
            "criminal application was allowed", "the order imposed conditions",
            "if arrested or if he surrendered", "he was directed not to",
            "the substantive sentence imposed", "the evidentiary record consists of",
            "no other prosecution or defence witnesses", "absence of any deposed witness",
        ]):
            return True
        if re.search(r"^(?:court|proceeding|applicant|respondent|petitioner|judge)\s*:", t_lower):
            return True
        if re.search(r"^\d[\d,]*\s+(?:of\s+\d{4}|with\s+two\s+(?:solvent\s+)?sureties)", t_lower):
            return True
            return True
        return False

    @classmethod
    def _extract_facts_from_text(cls, text: str) -> List[NormalizedFact]:
        """Extract factual propositions and classify their epistemic type."""
        facts: List[NormalizedFact] = []
        m = re.search(
            r"(?:SECTION 1: CASE BACKGROUND|FACTS OF THE CASE|PROSECUTION CASE:?|2\.\s*(?:Background and Prosecution Allegations|Case (?:&|and) Factual Summary)|BRIEF FACTS:?|FACTUAL MATRIX:?|CASE BACKGROUND:?)(.*?)(?=SECTION 2|SECTION|\n\s*[3-9]\.|\n\n[A-Z\s]{4,}|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        # If document is a structured summary with 1. Operative Verdict / 1. Ground-truth identity, etc. and no facts section, do not grab headers
        if not m and re.search(r"(?:1\.\s*(?:Operative Verdict|Ground-truth identity)|Ground-truth case identification|AI COURT GROUND TRUTH|Ground Truth\s*[\-–]|Case benchmark:)", text, re.IGNORECASE):
            source_text = ""
        else:
            source_text = m.group(1) if m else text[:2500]

        if source_text:
            seen_stmts: set[str] = set()
            # Rejoin soft line-wraps within paragraphs before sentence splitting
            normalized_source = re.sub(r"(?<!\n)\n(?!\s*(?:[0-9]+\.|[•\u2022\-*]|\n))", " ", source_text)
            raw_chunks = [line.strip(" \t•\u2022-*") for line in normalized_source.split("\n") if line.strip()]
            candidates: list[str] = []
            for chunk in raw_chunks:
                parts = re.split(r"(?<!\bNo)(?<!\bRs)(?<!\bMr)(?<!\bMs)(?<!\bDr)(?<!\bEx)(?<!\bP\.S)(?<!\bO\.S)(?<!\bC\.C)(?<!\bA\.B\.A)(?<=[.!?])\s+", chunk)
                if len(parts) > 1:
                    candidates.extend(p.strip(" \t•\u2022-*") for p in parts if p.strip())
                else:
                    candidates.append(chunk)

            for cand in candidates:
                if (
                    len(cand) > 25
                    and cand not in seen_stmts
                    and not cand.startswith("SECTION")
                    and not cls._is_non_fact_header_or_order(cand)
                ):
                    seen_stmts.add(cand)
                    etype = cls._classify_epistemic_statement(cand)
                    facts.append(
                        NormalizedFact(
                            statement=cand,
                            epistemic_type=etype,
                            is_material=True,
                        )
                    )

        return facts[:20]

    @classmethod
    def _classify_epistemic_statement(cls, stmt: str) -> EpistemicType:
        """Classify a legal proposition into FACT, EVIDENCE, CLAIM, INFERENCE, or LEGAL_CONCLUSION."""
        s = stmt.lower().strip()
        if any(term in s for term in [
            "held", "guilty", "acquitted", "consequently", "entitled to benefit", "liable to be dismissed", "judgment under challenge",
            "the court considered", "the court noted", "the court also considered", "the court took", "the court was not",
            "on that basis", "on these circumstances", "the court granted", "suspension of sentence",
        ]):
            return EpistemicType.LEGAL_CONCLUSION
        if any(term in s for term in ["infers", "indicates", "suggests", "demonstrates that", "implies", "leads to the conclusion"]):
            return EpistemicType.INFERENCE
        if s.startswith((
            "the prosecution submits", "the prosecution contends", "the prosecution argues",
            "the defense submits", "the defence submits", "the defense argues", "the defence argues",
            "the prosecution alleged", "prosecution case is", "learned counsel", "applicant:", "state:",
        )):
            return EpistemicType.CLAIM
        if any(term in s for term in ["pw-", "ex.", "ext.-", "exhibit", "deposed", "testified", "memo", "fsl report", "recovered vide", "material object"]):
            return EpistemicType.EVIDENCE
        return EpistemicType.FACT

    @classmethod
    def _extract_provisions(cls, text: str) -> List[str]:
        """Extract legal acts and sections cited."""
        provisions = set()
        matches = re.findall(
            r"(?:Section|Sec\.)\s+[0-9A-Za-z\(\)]+\s+(?:of\s+)?(?:the\s+)?(?:IPC|Indian Penal Code|CrPC|Code of Criminal Procedure|BNS|Bharatiya Nyaya Sanhita|BSA|Bharatiya Sakshya Adhiniyam|Arms Act|Evidence Act|Indian Evidence Act|Railway Property \(Unlawful Possession\) Act(?:,\s*1966)?|R\.P\.\(U\.P\.\)\s*Act)",
            text,
            re.IGNORECASE,
        )
        for m in matches:
            provisions.add(re.sub(r"\s+", " ", m.strip()))

        # Also extract mentions like 'Sections 102 and 114, Indian Evidence Act, 1872' or 'Sections 331(4), 305 & 62 of BNSS'
        m_compound = re.findall(
            r"Sections?\s+([0-9][0-9A-Za-z\(\)\s,&]+?)\s*(?:of\s+)?(?:the\s+)?(IPC|Indian Penal Code|Indian Evidence Act|Evidence Act|BNS|Bharatiya Nyaya Sanhita|BSA|Bharatiya Sakshya Adhiniyam|BNSS|Bharatiya Nagarik Suraksha Sanhita|CrPC)",
            text,
            re.IGNORECASE,
        )
        for nums, statute in m_compound:
            for n in re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", nums):
                if n in {"1860", "1872", "1973", "2023"}:
                    continue
                provisions.add(f"Section {n} {statute.upper()}")

        # Also extract 'IPC Sections 353 and 379' (Act before plural Sections)
        for statute, nums in re.findall(
            r"\b(IPC|BNS|BNSS|CrPC|IEA|BSA|Arms Act)\s+Sections?\s+([0-9][0-9A-Za-z\(\)\s,&/]+?)(?=\.|,|\n|$|\s+The\b|\s+of\b)",
            text,
            re.IGNORECASE,
        ):
            for n in re.findall(r"(?<![A-Za-z0-9])([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?![A-Za-z0-9])", nums):
                if n in {"1860", "1872", "1973", "2023"}:
                    continue
                if statute.upper() in {"CRPC", "BNSS"} and (n.startswith("438") or n.startswith("482")):
                    continue
                provisions.add(f"Section {n} {statute.upper()}")

        # Exclude bail-bond procedural condition sub-sections (438(2) CrPC / 482(2) BNSS) from substantive provisions
        provisions = {
            p for p in provisions
            if not re.search(r"(?<!\d)(?:438\(2\)|482\(2\))(?!\d)", p)
        }
        return list(provisions)

    @classmethod
    def _extract_chains_of_reasoning(cls, reasons_text: str) -> List[str]:
        """Extract logical inference steps and distinct proposition chains."""
        # Rejoin soft line-wraps within paragraphs before splitting into reasoning chains
        normalized_reasons = re.sub(r"(?<!\n)\n(?!\s*(?:[0-9]+\.|[•\u2022\-*]|\n))", " ", reasons_text)
        chains: List[str] = []
        for line in normalized_reasons.split("\n"):
            clean = line.strip(" \t•\u2022-*")
            if (
                len(clean) > 25
                and not cls._is_footer_or_metadata(clean)
                and not re.match(r"^(?:\d+\.\s*)?(?:heard learned|learned a\.p\.p opposes|for the (?:petitioner|state)|coram\s*:|order\s+no\.)", clean, re.IGNORECASE)
            ):
                chains.append(clean)

        if not chains:
            sentences = re.split(r"(?<=[.!?])\s+", reasons_text)
            chains = [
                s.strip() for s in sentences
                if len(s.strip()) > 30 and not cls._is_footer_or_metadata(s) and any(
                    w in s.lower() for w in ["because", "therefore", "failed", "doubt", "proved", "burden", "presumption", "stolen", "unsustainable", "held"]
                )
            ]
        return chains

    @classmethod
    def _extract_reasoning_structure(cls, text: str, eval_block: Optional[str] = None) -> NormalizedReasoning:
        """Extract ratio decidendi and assessment capabilities."""
        reasons_text = ""
        # 1. Check for '3. Core Reasoning'
        m_core = re.search(
            r"(?:3\.\s*Core Reasoning|CORE REASONING:?|SECTION 11: RATIO DECIDENDI|RATIO DECIDENDI|REASONS FOR DECISION|REASONS:?)(.*?)(?=(?:\n\s*[0-9]\.|\n\n[A-Z\s]{4,}|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m_core:
            reasons_text = m_core.group(1).strip()
        else:
            cleaned_tail = re.split(r"\n\s*(?:8\.\s*Phase 5|9\.\s*Source limitations|10\.\s*Isolation and evaluation|Correct interpretation for comparison)", text, maxsplit=1, flags=re.IGNORECASE)[0]
            reasons_text = cleaned_tail[-2000:]

        chains = cls._extract_chains_of_reasoning(reasons_text)

        # If summary has explicit reasoning targets in evaluation block, append as recognized chains
        if eval_block:
            m_targets = re.search(r"Reasoning targets:\s*([^\n]+(?:\n[^\n•\u2022\-\*0-9]+)*)", eval_block, re.IGNORECASE)
            if m_targets:
                for target_stmt in m_targets.group(1).split(";"):
                    t_clean = target_stmt.strip()
                    if t_clean and t_clean not in chains:
                        chains.append(t_clean)

        t_lower = text.lower()
        return NormalizedReasoning(
            ratio_decidendi=reasons_text[:2500],
            key_chains=chains,
            evaluated_credibility=bool("credibility" in t_lower or "demeanour" in t_lower or "reliable witness" in t_lower or "interested witness" in t_lower),
            evaluated_contradictions=bool("contradiction" in t_lower or "inconsisten" in t_lower or "discrepanc" in t_lower or "unresolved" in t_lower),
            evaluated_missing_evidence=bool("not joined" in t_lower or "omission" in t_lower or "absence of" in t_lower or "independent witness" in t_lower or "failed to produce" in t_lower or "gaps in" in t_lower),
            connected_evidence_to_findings=bool("proved" in t_lower or "established" in t_lower or "benefit of doubt" in t_lower or "reasonable doubt" in t_lower),
        )

    @classmethod
    def _extract_arguments(cls, text: str, side: str = "prosecution") -> List[str]:
        """Extract submissions by prosecution or defense."""
        keyword = "PROSECUTION" if side == "prosecution" else "DEFEN[CS]E"
        m = re.search(
            rf"(?:(?:SECTION\s*[0-9]+:\s*)?(?:SUBMISSIONS ADVANCED BY THE {keyword}|SUBMISSIONS OF {keyword}|{keyword} (?:CASE AND )?ARGUMENTS):?)(.*?)(?=(?:\n\s*[0-9]\.|\n\n[A-Z\s]{{4,}}|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if m:
            clean = " ".join(m.group(1).split()).strip()
            return [clean[:500]]
        return []
