"""
Pydantic data models for Legal Research and Web Research results in AI Court of India.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ApplicableProvision(BaseModel):
    """Represents a specific statutory provision retrieved from the local legal corpus."""

    act_name: str = Field(description="Full name of the statute (e.g. 'Bharatiya Nyaya Sanhita, 2023').")
    short_name: str = Field(description="Statutory acronym (e.g. 'BNS', 'BSA', 'IT_Act', 'Constitution').")
    section_or_article: str = Field(description="Section or Article designation (e.g. 'Section 317', 'Article 21').")
    title: Optional[str] = Field(default=None, description="Heading or title of the provision.")
    page: int = Field(description="Official page number in the gazette source PDF.")
    source_file: str = Field(description="Source PDF filename.")
    chunk_id: str = Field(description="Unique deterministic chunk ID in ChromaDB.")
    citation: str = Field(description="Authoritative legal citation string.")
    text: str = Field(description="Text extract of the legal provision.")
    relevance_reasoning: str = Field(
        description="Legal reasoning explaining why this provision applies to the specific issue."
    )
    applicable_version: Optional[str] = Field(
        default=None, description="The statutory framework selected for the case, such as IPC/IEA/CrPC or BNS/BSA/BNSS."
    )
    legal_ingredients: list[str] = Field(
        default_factory=list, description="Elements, foundational requirements, exceptions, or proof rules stated in the retrieved text."
    )
    applicability_confidence: str = Field(
        default="high", description="high, medium, or uncertain depending on date, statute, and source traceability."
    )
    applicability_uncertainty: Optional[str] = Field(
        default=None, description="Why applicability could not be resolved from the packet or corpus."
    )


class LegalResearchResult(BaseModel):
    """Structured output of the Legal Research Agent (prosecution or defense side)."""

    research_id: str = Field(description="Unique research identifier.")
    side: Literal["prosecution", "defense", "judicial"] = Field(
        description="Courtroom perspective conducting the research."
    )
    question: str = Field(description="The legal question researched.")
    findings: str = Field(description="Synthesized legal conclusion grounded in statutory law.")
    applicable_provisions: list[ApplicableProvision] = Field(
        default_factory=list,
        description="List of retrieved and verified statutory provisions.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="List of formal legal citations to be used in arguments.",
    )
    source_pages: list[int] = Field(
        default_factory=list,
        description="All gazette pages grounded by this research.",
    )
    reasoning_relevance: str = Field(
        description="Substantive analysis of how the retrieved provisions govern the case."
    )


class WebResearchItem(BaseModel):
    """Represents a single external legal source retrieved via web research."""

    title: str = Field(description="Title of the article, judicial precedent, or gazette notification.")
    url: str = Field(description="Source URL.")
    publication_or_judgment_date: Optional[str] = Field(
        default=None,
        description="Date of judgment or notification if available.",
    )
    passage_summary: str = Field(description="Key legal rule, ratio decidendi, or statutory change summary.")
    why_source_matters: str = Field(description="Relevance to the prosecution or defense contention.")
    source_reliability: str = Field(
        default="authoritative_legal_source",
        description="Assessment: 'supreme_court_precedent', 'high_court_precedent', 'official_gazette', 'legal_database'.",
    )
    is_current: bool = Field(default=True, description="Whether the legal principle represents currently valid law.")


class WebResearchResult(BaseModel):
    """Structured output of the Web Research Agent."""

    research_id: str = Field(description="Unique web research identifier.")
    side: Literal["prosecution", "defense", "judicial"] = Field(
        description="Courtroom perspective conducting web research."
    )
    research_question: str = Field(description="The specific external legal question investigated.")
    finding: str = Field(description="Core finding from external legal research.")
    sources: list[WebResearchItem] = Field(
        default_factory=list,
        description="Authoritative external sources supporting the finding.",
    )
    why_it_matters: str = Field(description="Impact of external research on the party's legal position.")
