"""
Legal Transition and Historical Statute Selection Service.
Handles transition provisions between Indian Penal Code 1860 / Indian Evidence Act 1872 / CrPC 1973
and Bharatiya Nyaya Sanhita 2023 / Bharatiya Sakshya Adhiniyam 2023 / BNSS 2023.

Transition cut-off date: July 1, 2024.
Offences registered or committed prior to July 1, 2024 are tried and adjudicated under IPC/IEA/CrPC.
Post-July 1, 2024 offences are tried under BNS/BSA/BNSS.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Optional

from app.models.case_models import StructuredCase

logger = logging.getLogger(__name__)

TRANSITION_DATE = date(2024, 7, 1)

# Corpus short names expected for each framework. The Information Technology Act
# remains applicable across the BNS transition and is therefore intentionally not
# excluded by either set.
HISTORICAL_ACT_FILTERS = ("IPC", "IEA", "CrPC", "IT_Act", "Constitution")
MODERN_ACT_FILTERS = ("BNS", "BSA", "BNSS", "IT_Act", "Constitution")

# Section correspondence maps based on Indian Law repeal & savings
# (BNS s.358, BNSS s.531, BSA repeal clauses)
BNS_TO_IPC_MAP = {
    "103": "302",  # Murder
    "105": "304",  # Culpable homicide not amounting to murder
    "106": "304A", # Causing death by negligence
    "303": "379",  # Theft
    "305": "380",  # Theft in dwelling house
    "309": "392",  # Robbery
    "310": "395",  # Dacoity
    "317": "411",  # Receiving stolen property (also 412)
    "318": "420",  # Cheating
    "324": "425",  # Mischief
    "329": "441",  # Criminal trespass
    "64": "376",   # Rape
    "74": "354",   # Assault on woman with intent to outrage modesty
    "115": "323",  # Voluntarily causing hurt
    "117": "325",  # Voluntarily causing grievous hurt
    "190": "149",  # Unlawful assembly
    "191": "146",  # Rioting
    "61": "120B",  # Criminal conspiracy
}

BSA_TO_IEA_MAP = {
    "104": "101",  # Burden of proof
    "105": "102",  # On whom burden of proof lies
    "108": "105",  # Burden of proving that case comes within exceptions
    "23": "27",    # How much of information received from accused may be proved
    "24": "25",    # Confession to police officer not to be proved
    "25": "26",    # Confession by accused while in custody of police
    "26": "28",    # Confession made after removal of impression caused by inducement
    "61": "65A",   # Special provisions as to evidence relating to electronic record
    "63": "65B",   # Admissibility of electronic records
    "119": "114",  # Court may presume existence of certain facts
    "137": "134",  # Number of witnesses
    "142": "137",  # Examination-in-chief, cross-examination, re-examination
    "143": "138",  # Order of examinations
    "146": "141",  # Leading questions
}


def detect_case_legal_regime(
    case: Optional[StructuredCase],
    case_text: Optional[str] = None,
) -> dict[str, Any]:
    """
    Determine whether a case is governed by historical legislation (IPC, IEA, CrPC)
    or modern legislation (BNS, BSA, BNSS) based on charges, FIR dates, and procedural history.

    Rules:
    1. If any charge references IPC / Indian Penal Code / CrPC / Indian Evidence Act, regime is historical.
    2. If dates or FIR years in the case record are prior to July 1, 2024, regime is historical.
    3. If charges reference BNS / BSA / BNSS and there are no pre-2024 indicators, regime is modern.
    """
    text_corpus = ""
    charges_mention_ipc = False
    charges_mention_bns = False

    if case:
        text_corpus += f" {case.case_title} {case.court_identifier or ''} {case.allegations_summary} {case.procedural_history or ''}"
        text_corpus += " " + " ".join(case.prosecution_facts)
        text_corpus += " " + " ".join(case.defense_facts)

        for ch in case.charges:
            statute_lower = ch.statute.lower()
            sec_lower = ch.section.lower()
            desc_lower = ch.description.lower()

            if any(term in statute_lower or term in sec_lower or term in desc_lower for term in ["ipc", "indian penal code", "crpc", "evidence act, 1872", "iea"]):
                charges_mention_ipc = True
            if any(term in statute_lower or term in sec_lower or term in desc_lower for term in ["bns", "bharatiya nyaya", "bsa", "bharatiya sakshya", "bnss"]):
                charges_mention_bns = True

    if case_text:
        text_corpus += f" {case_text[:10000]}"

    text_lower = text_corpus.lower()

    # Prefer an explicit alleged-incident/FIR date over a year appearing in
    # procedural history or a citation. A 2024 case needs day-level handling.
    relevant_date = _extract_relevant_legal_date(text_corpus)

    # Check for historical years (e.g., 1900-2023 or 2024 prior to July)
    fir_year_match = re.search(r"(?:fir|crime|case|sessions case)\s*(?:no\.?)?\s*[:\-]?\s*\d+\s*/\s*(19\d\d|20[0-2]\d)", text_lower)
    historical_year_found = False
    detected_year = None

    if fir_year_match:
        year_val = int(fir_year_match.group(1))
        if year_val < 2024:
            historical_year_found = True
            detected_year = year_val

    if not historical_year_found:
        # Search for explicit years in incident descriptions
        all_years = [int(y) for y in re.findall(r"\b(19\d\d|20[0-2]\d)\b", text_corpus)]
        pre_2024_years = [y for y in all_years if y < 2024]
        if len(pre_2024_years) >= 2:
            historical_year_found = True
            detected_year = max(pre_2024_years)

    # General IPC mention in text if no explicit BNS
    explicit_ipc_in_text = bool(re.search(r"\b(ipc|indian penal code|section \d+ ipc)\b", text_lower))

    is_historical = False
    reasoning = ""

    uncertain = False
    if relevant_date is not None:
        is_historical = relevant_date < TRANSITION_DATE
        reasoning = (
            f"Relevant alleged-offence/FIR date is {relevant_date.isoformat()}, "
            f"which is {'before' if is_historical else 'on or after'} the July 1, 2024 transition."
        )
    elif charges_mention_ipc:
        is_historical = True
        reasoning = "Statutory charges explicitly framed under Indian Penal Code / historical legislation."
    elif historical_year_found:
        is_historical = True
        reasoning = f"Case registration / incident occurred in {detected_year} (prior to July 1, 2024 transition cut-off)."
    elif explicit_ipc_in_text and not charges_mention_bns:
        is_historical = True
        reasoning = "Procedural record references Indian Penal Code / pre-transition law."
    elif charges_mention_bns:
        is_historical = False
        reasoning = "Statutory charges framed under Bharatiya Nyaya Sanhita, 2023."
    else:
        # Do not present a guessed contemporary regime as certain.
        is_historical = False
        uncertain = True
        reasoning = "No reliable alleged-offence or FIR date, or explicit statutory charge, was extracted."

    if is_historical:
        return {
            "is_historical": True,
            "regime": "historical",
            "penal_statute": "Indian Penal Code, 1860",
            "penal_short": "IPC",
            "evidence_statute": "Indian Evidence Act, 1872",
            "evidence_short": "IEA",
            "procedure_statute": "Code of Criminal Procedure, 1973",
            "procedure_short": "CrPC",
            "reasoning": reasoning,
            "applicability_confidence": "uncertain" if uncertain else "high",
            "allowed_act_filters": HISTORICAL_ACT_FILTERS,
        }
    else:
        return {
            "is_historical": False,
            "regime": "modern",
            "penal_statute": "Bharatiya Nyaya Sanhita, 2023",
            "penal_short": "BNS",
            "evidence_statute": "Bharatiya Sakshya Adhiniyam, 2023",
            "evidence_short": "BSA",
            "procedure_statute": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "procedure_short": "BNSS",
            "reasoning": reasoning,
            "applicability_confidence": "uncertain" if uncertain else "high",
            "allowed_act_filters": MODERN_ACT_FILTERS,
        }


def _extract_relevant_legal_date(text: str) -> Optional[date]:
    """Return a date tied to the offence/incident/FIR, never a judgment date."""
    labelled = re.compile(
        r"(?:date\s+of\s+)?(?:occurrence|incident|offence|commission|fir|crime)\s*(?:date)?\s*[:\-]?\s*"
        r"(\d{1,2}[./-]\d{1,2}[./-](?:19\d{2}|20\d{2})|(?:19\d{2}|20\d{2})[./-]\d{1,2}[./-]\d{1,2})",
        re.IGNORECASE,
    )
    matches = labelled.findall(text)
    for raw in matches:
        parsed = _parse_indian_date(raw)
        if parsed:
            return parsed
    return None


def _parse_indian_date(raw: str) -> Optional[date]:
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    return None


def get_defense_legal_research_query(case: Optional[StructuredCase]) -> str:
    """Generate statute-aware defense research query respecting historical transition."""
    regime_info = detect_case_legal_regime(case)
    if regime_info["is_historical"]:
        return "burden of proof presumption of innocence and reasonable doubt under Indian Evidence Act 1872 and Indian Penal Code"
    return "burden of proof presumption of innocence and reasonable doubt under Bharatiya Sakshya Adhiniyam and Bharatiya Nyaya Sanhita"


def get_prosecutor_legal_research_query(case: Optional[StructuredCase]) -> str:
    """Generate statute-aware prosecution research query respecting historical transition."""
    regime_info = detect_case_legal_regime(case)
    if case and case.charges:
        active_charges = case.current_charges() if hasattr(case, "current_charges") else [
            c for c in case.charges if c.record_status == "current"
        ]
        target_charges = active_charges or case.charges
        seen_pairs: list[str] = []
        for ch in target_charges:
            statute_name = ch.statute
            if regime_info["is_historical"] and (
                "bns" in statute_name.lower() or "bharatiya nyaya sanhita" in statute_name.lower()
            ):
                statute_name = "Indian Penal Code"
            pair = f"{ch.section} {statute_name}".strip()
            if pair.casefold() not in {p.casefold() for p in seen_pairs}:
                seen_pairs.append(pair)
        if seen_pairs:
            return f"essential ingredients of {'; '.join(seen_pairs)}"

    if regime_info["is_historical"]:
        return "burden of proof beyond reasonable doubt criminal prosecution under Indian Penal Code"
    return "burden of proof beyond reasonable doubt criminal prosecution under Bharatiya Nyaya Sanhita"


def map_provision_to_historical(act_name: str, section_or_article: str) -> tuple[str, str]:
    """
    Map modern BNS/BSA provision to corresponding historical IPC/IEA provision
    under transition saving provisions.
    """
    sec_num_match = re.search(r"\d+[A-Za-z]?", section_or_article)
    sec_num = sec_num_match.group(0) if sec_num_match else ""

    act_lower = act_name.lower()
    if "sakshya" in act_lower or "bsa" in act_lower:
        hist_sec = BSA_TO_IEA_MAP.get(sec_num)
        if hist_sec:
            return "Indian Evidence Act, 1872", f"Section {hist_sec} (corresponding to BSA Section {sec_num})"
        return "Indian Evidence Act, 1872", section_or_article

    if "nyaya" in act_lower or "bns" in act_lower:
        hist_sec = BNS_TO_IPC_MAP.get(sec_num)
        if hist_sec:
            return "Indian Penal Code, 1860", f"Section {hist_sec} (corresponding to BNS Section {sec_num})"
        return "Indian Penal Code, 1860", section_or_article

    return act_name, section_or_article

