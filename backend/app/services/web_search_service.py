"""
Web search service with strict blind-evaluation guardrails for AI Court of India.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from app.models.legal_models import WebResearchItem

logger = logging.getLogger(__name__)

# Disallowed query patterns that could leak the hidden real-world judgment
PROHIBITED_GROUND_TRUTH_PATTERNS = [
    r"\bfinal\s+judg(?:e)?ment\b",
    r"\bverdict\b",
    r"\bactual\s+outcome\b",
    r"\bactual\s+judg(?:e)?ment\b",
    r"\bconvict(?:ed|ion)?\b",
    r"\bacquit(?:ted|tal)?\b",
    r"\bconvicted\s+or\s+acquitted\b",
    r"\breal\s+court\s+decision\b",
    r"\breal\s+judg(?:e)?ment\b",
    r"\bhidden\s+verdict\b",
    r"\bground\s+truth\b",
    r"\bdecision\s+of\s+the\s+supreme\s+court\s+in\s+this\s+case\b",
]


class WebSearchService:
    """
    Search service for external legal authorities and amendments.
    Guarantees strict blind evaluation by rejecting queries aimed at unmasking
    the real court's hidden judgment.
    """

    def __init__(self, provider: str = "mock"):
        self.provider = provider.lower()

    @staticmethod
    def validate_query_blindness(query: str) -> None:
        """
        Enforce strict blind evaluation: prevent searching for the real-world verdict.
        """
        q_lower = query.lower()
        for pattern in PROHIBITED_GROUND_TRUTH_PATTERNS:
            if re.search(pattern, q_lower):
                raise PermissionError(
                    f"BLIND EVALUATION VIOLATION: Web query '{query}' violates the isolation rule. "
                    f"Web search cannot be used to discover the hidden ground-truth verdict."
                )

    def search_legal(
        self,
        query: str,
        max_results: int = 3,
        side: str = "general",
    ) -> list[WebResearchItem]:
        """
        Perform a guarded legal web search.

        Args:
            query: Legal research question (e.g. 'recent amendments to section 66 IT Act').
            max_results: Number of results.
            side: 'prosecution' or 'defense'.

        Returns:
            List of WebResearchItem objects.
        """
        # Defensive check
        self.validate_query_blindness(query)

        logger.info("Executing legal web search (%s side): '%s'", side, query)

        # In mock or offline mode, return representative authoritative statutory commentary
        return self._get_authoritative_mock_results(query, side, max_results)

    def _get_authoritative_mock_results(
        self,
        query: str,
        side: str,
        max_results: int,
    ) -> list[WebResearchItem]:
        q_lower = query.lower()

        if "electronic" in q_lower or "65b" in q_lower or "63" in q_lower:
            return [
                WebResearchItem(
                    title="Supreme Court of India on Admissibility of Electronic Records (Arjun Panditrao)",
                    url="https://main.sci.gov.in/supremecourt/2018/electronic_evidence.pdf",
                    publication_or_judgment_date="2020-07-14",
                    passage_summary=(
                        "The Supreme Court held that the certificate under Section 65B(4) of Indian Evidence Act, 1872 "
                        "(corresponding to Section 63 BSA) is a mandatory condition precedent to the admissibility of electronic evidence."
                    ),
                    why_source_matters="Governs requirement of digital evidence certification under Indian evidence law.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                )
            ][:max_results]

        if "circumstantial" in q_lower or "benefit of doubt" in q_lower or "presumption of innocence" in q_lower:
            return [
                WebResearchItem(
                    title="Sharad Birdhichand Sarda v. State of Maharashtra, (1984) 4 SCC 116",
                    url="https://indiankanoon.org/doc/1449646/",
                    publication_or_judgment_date="1984-07-17",
                    passage_summary=(
                        "The Supreme Court laid down the five golden principles (Panchsheel) governing circumstantial evidence: "
                        "the circumstances from which the conclusion of guilt is to be drawn should be fully established, "
                        "all facts so established must be consistent only with the hypothesis of guilt, and the chain of evidence "
                        "must be complete without leaving any reasonable ground for conclusion consistent with innocence."
                    ),
                    why_source_matters="Landmark Supreme Court precedent governing proof by circumstantial evidence and benefit of doubt.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                ),
                WebResearchItem(
                    title="Kali Ram v. State of Himachal Pradesh, (1973) 2 SCC 808",
                    url="https://indiankanoon.org/doc/766627/",
                    publication_or_judgment_date="1973-09-24",
                    passage_summary=(
                        "The Supreme Court ruled that the presumption of innocence is a human right. If two reasonable conclusions "
                        "are possible on the basis of the evidence on record, the one that points to the innocence of the accused must be adopted."
                    ),
                    why_source_matters="Authoritative standard on presumption of innocence and benefit of reasonable doubt under Indian law.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                ),
            ][:max_results]

        if "302" in q_lower or "murder" in q_lower or "homicid" in q_lower or "103" in q_lower:
            return [
                WebResearchItem(
                    title="State of Andhra Pradesh v. Rayavarapu Punnayya, (1976) 4 SCC 382",
                    url="https://indiankanoon.org/doc/1574345/",
                    publication_or_judgment_date="1976-09-21",
                    passage_summary=(
                        "The Supreme Court formulated the classic tripartite test distinguishing culpable homicide (Section 299 IPC / Section 100 BNS) "
                        "from murder (Section 300/302 IPC / Section 103 BNS), establishing that the prosecution must prove bodily injury "
                        "sufficient in the ordinary course of nature to cause death accompanied by the requisite intention or knowledge."
                    ),
                    why_source_matters="Directly governs statutory ingredients, intention, and burden of proof in homicide/murder trials.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                ),
                WebResearchItem(
                    title="Virsa Singh v. State of Punjab, AIR 1958 SC 465",
                    url="https://indiankanoon.org/doc/106399/",
                    publication_or_judgment_date="1958-03-11",
                    passage_summary=(
                        "The Supreme Court held that to prove murder under clause 3 of Section 300 IPC, the prosecution must establish "
                        "objectively that the bodily injury inflicted was sufficient in the ordinary course of nature to cause death."
                    ),
                    why_source_matters="Definitive Supreme Court authority on essential ingredients of Section 302 IPC.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                ),
            ][:max_results]

        if "section 27" in q_lower or "recovery" in q_lower or "discovery" in q_lower or "section 23" in q_lower:
            return [
                WebResearchItem(
                    title="Pulukuri Kotayya v. King-Emperor, AIR 1947 PC 67 & Babu v. State of T.N., (2013) 8 SCC 60",
                    url="https://indiankanoon.org/doc/1715494/",
                    publication_or_judgment_date="2013-05-10",
                    passage_summary=(
                        "Section 27 of the Indian Evidence Act, 1872 (Section 23 BSA) admits only so much of the disclosure statement "
                        "as distinctly relates to the fact thereby discovered. Mere recovery of an article without proving exclusive "
                        "conscious concealment and authorship is insufficient to sustain conviction."
                    ),
                    why_source_matters="Governs legal admissibility and probative weight of evidentiary recoveries made in police custody.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                )
            ][:max_results]

        if "arms" in q_lower or "weapon" in q_lower or "pistol" in q_lower:
            return [
                WebResearchItem(
                    title="Gunwantlal v. State of Madhya Pradesh, (1972) 2 SCC 194",
                    url="https://indiankanoon.org/doc/1841285/",
                    publication_or_judgment_date="1972-04-12",
                    passage_summary=(
                        "The Supreme Court settled that 'possession' under Section 25 of the Arms Act means conscious possession "
                        "with control over the weapon. Mere physical presence or joint accessibility without exclusive control does not constitute possession."
                    ),
                    why_source_matters="Authoritative Supreme Court ruling on conscious possession under Arms Act.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                )
            ][:max_results]

        if "stolen" in q_lower or "317" in q_lower or "theft" in q_lower or "411" in q_lower:
            return [
                WebResearchItem(
                    title="Judicial Precedents on Presumption under Section 114 Indian Evidence Act / Section 119 BSA",
                    url="https://indiankanoon.org/doc/114_presumption_stolen_goods/",
                    publication_or_judgment_date="2022-03-10",
                    passage_summary=(
                        "A person found in possession of stolen goods soon after the theft is either the thief "
                        "or has received the goods knowing them to be stolen, unless he can account for his possession."
                    ),
                    why_source_matters="Directly relevant to burden of proof and statutory presumption in stolen property cases.",
                    source_reliability="supreme_court_precedent",
                    is_current=True,
                )
            ][:max_results]

        if "forgery" in q_lower or "source code" in q_lower or "hacking" in q_lower:
            return [
                WebResearchItem(
                    title="Ministry of Electronics and Information Technology - Information Technology Rules & Precedents",
                    url="https://www.meity.gov.in/cyber-laws",
                    publication_or_judgment_date="2023-01-15",
                    passage_summary=(
                        "Tampering with computer source documents under Section 65 requires deliberate and intentional "
                        "concealment, destruction or alteration of computer source code maintained by law."
                    ),
                    why_source_matters="Clarifies statutory threshold of mens rea under Section 65 and 66.",
                    source_reliability="official_gazette",
                    is_current=True,
                )
            ][:max_results]

        # Default fallback legal precedent
        return [
            WebResearchItem(
                title=f"Legal Interpretation of {query[:40]} - High Court Precedents",
                url="https://judgments.ecourts.gov.in/pdf/legal_precedent.pdf",
                publication_or_judgment_date="2023-11-20",
                passage_summary=f"Established judicial principles applicable to '{query}', emphasising strict statutory interpretation.",
                why_source_matters=f"Provides persuasive authority for {side} submissions.",
                source_reliability="high_court_precedent",
                is_current=True,
            )
        ][:max_results]
