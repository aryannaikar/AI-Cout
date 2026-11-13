"""
Legal-aware chunking engine for Indian legal documents and the Constitution of India.
Preserves Part, Chapter, Section, Article, Sub-section, Clause, Proviso, and Explanation structures.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from rag.cleaner import clean_legal_text, is_footnote_line
from rag.loader import LegalDocument, PDFPage

logger = logging.getLogger(__name__)


@dataclass
class LegalChunk:
    """A semantic, legally-grounded chunk of text with complete statutory metadata."""

    chunk_id: str
    text: str
    act_name: str
    short_name: str
    section: Optional[str]
    article: Optional[str]
    title: Optional[str]
    chapter: Optional[str]
    part: Optional[str]
    page: int
    page_end: int
    chunk_type: str  # "section", "article", "sub_section", "proviso", "explanation", "preamble"
    parent_chunk_id: Optional[str]
    source_file: str
    year: int
    jurisdiction: str = "India"

    def to_metadata(self) -> dict[str, str | int | float | bool]:
        """Convert metadata to a ChromaDB-compliant dictionary (str, int, float, bool only)."""
        return {
            "act_name": self.act_name,
            "short_name": self.short_name,
            "section": self.section or "",
            "article": self.article or "",
            "title": self.title or "",
            "chapter": self.chapter or "",
            "part": self.part or "",
            "page": self.page,
            "page_end": self.page_end,
            "chunk_type": self.chunk_type,
            "parent_chunk_id": self.parent_chunk_id or "",
            "source_file": self.source_file,
            "year": self.year,
            "jurisdiction": self.jurisdiction,
        }


class LegalAwareChunker:
    """
    Intelligent legal chunker that splits acts and constitution into meaningful
    statutory units rather than arbitrary character windows.
    """

    def __init__(self, max_chunk_size: int = 1500, chunk_overlap: int = 150):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: LegalDocument) -> list[LegalChunk]:
        """
        Main entrypoint: split a LegalDocument into structured legal chunks.
        Guarantees 100% unique chunk IDs for safe ChromaDB indexing.
        """
        if not document.pages:
            return []

        if document.document_type == "constitution":
            raw_chunks = self._chunk_constitution(document)
        else:
            raw_chunks = self._chunk_act(document)

        # Enforce unique chunk IDs across document
        seen_ids: dict[str, int] = {}
        unique_chunks: list[LegalChunk] = []
        for c in raw_chunks:
            if c.chunk_id not in seen_ids:
                seen_ids[c.chunk_id] = 1
                unique_chunks.append(c)
            else:
                seen_ids[c.chunk_id] += 1
                c.chunk_id = f"{c.chunk_id}_v{seen_ids[c.chunk_id]}"
                unique_chunks.append(c)

        return unique_chunks

    # -------------------------------------------------------------------------
    # Constitution Chunking
    # -------------------------------------------------------------------------

    def _chunk_constitution(self, doc: LegalDocument) -> list[LegalChunk]:
        """
        Chunk the Constitution of India into Articles, Parts, and Preamble.
        """
        chunks: list[LegalChunk] = []

        # Tag pages and lines
        lines_with_page = self._extract_clean_lines_with_page(doc.pages)

        # Detect Preamble (typically page 32)
        preamble_lines: list[str] = []
        preamble_page = 1
        in_preamble = False

        for page_no, line in lines_with_page:
            if "WE, THE PEOPLE OF INDIA" in line:
                in_preamble = True
                preamble_page = page_no
            if in_preamble:
                preamble_lines.append(line)
                if "DO HEREBY ADOPT, ENACT AND GIVE TO OURSELVES THIS CONSTITUTION" in line:
                    break

        if preamble_lines:
            preamble_text = " ".join(preamble_lines)
            chunks.append(
                LegalChunk(
                    chunk_id="const_preamble",
                    text=f"[Constitution of India | Preamble]\n{preamble_text}",
                    act_name=doc.act_name,
                    short_name=doc.short_name,
                    section=None,
                    article=None,
                    title="Preamble",
                    chapter=None,
                    part="Preamble",
                    page=preamble_page,
                    page_end=preamble_page,
                    chunk_type="preamble",
                    parent_chunk_id=None,
                    source_file=doc.source_file,
                    year=doc.year,
                )
            )

        # Extract articles from body (skip Table of Contents before page 32)
        body_lines = [
            (page_no, line)
            for page_no, line in lines_with_page
            if page_no >= 32 and not is_footnote_line(line)
        ]

        current_part = "PART I - THE UNION AND ITS TERRITORY"
        current_chapter: Optional[str] = None

        # Regex to detect Constitution Article header:
        # e.g.: "21. Protection of life and personal liberty.—"
        # or "Article 21. ..."
        art_regex = re.compile(
            r"^(?:(?:Article|ARTICLE)\s+(\d+[A-Z]?)|(\d+[A-Z]?)\.\s+([A-Z][^\n—–-]{2,80}))(?:[—–-](.*))?$"
        )

        current_art_num: Optional[str] = None
        current_art_title: Optional[str] = None
        current_art_lines: list[str] = []
        current_art_start_page = 1
        current_art_end_page = 1

        def flush_current_article():
            if not current_art_num or not current_art_lines:
                return
            art_text = "\n".join(current_art_lines).strip()
            if not art_text:
                return

            parent_id = f"const_art_{current_art_num.lower()}"
            sub_chunks = self._subchunk_legal_provision(
                act_name=doc.act_name,
                short_name=doc.short_name,
                provision_label=f"Article {current_art_num}",
                section_num=None,
                article_num=f"Article {current_art_num}",
                title=current_art_title or f"Article {current_art_num}",
                part=current_part,
                chapter=current_chapter,
                text=art_text,
                parent_id=parent_id,
                page_start=current_art_start_page,
                page_end=current_art_end_page,
                source_file=doc.source_file,
                year=doc.year,
                default_type="article",
            )
            chunks.extend(sub_chunks)

        for page_no, line in body_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for PART header
            part_match = re.match(r"^PART\s+([IVXLCDM\d]+[A-Z]?(?:\s*[-–—]\s*[^\n]+)?)$", stripped, re.IGNORECASE)
            if part_match:
                current_part = stripped
                continue

            # Check for CHAPTER header
            chap_match = re.match(r"^CHAPTER\s+([IVXLCDM\d]+[A-Z]?(?:\s*[-–—]\s*[^\n]+)?)$", stripped, re.IGNORECASE)
            if chap_match:
                current_chapter = stripped
                continue

            # Check for Article start
            art_match = art_regex.match(stripped)
            if art_match:
                num = art_match.group(1) or art_match.group(2)
                title = (art_match.group(3) or "").strip()
                trailing = (art_match.group(4) or "").strip()

                combined = f"{title} {trailing}".lower()
                if any(
                    kw in combined
                    for kw in [
                        "amendment",
                        "subs. by",
                        "ins. by",
                        "renumbered",
                        "w.e.f.",
                        "omitted by",
                        "ibid",
                    ]
                ):
                    if current_art_num:
                        current_art_lines.append(stripped)
                    continue

                flush_current_article()

                current_art_num = num
                current_art_title = title
                current_art_start_page = page_no
                current_art_end_page = page_no
                current_art_lines = []

                header_text = f"{num}. {title}." if title else f"Article {num}."
                if trailing:
                    header_text += f"—{trailing}"
                current_art_lines.append(header_text)
            else:
                if current_art_num:
                    current_art_lines.append(stripped)
                    current_art_end_page = page_no

        flush_current_article()
        logger.info("Generated %d chunks for Constitution of India", len(chunks))
        return chunks

    # -------------------------------------------------------------------------
    # Ordinary Act Chunking (BNS, BSA, IT Act)
    # -------------------------------------------------------------------------

    def _chunk_act(self, doc: LegalDocument) -> list[LegalChunk]:
        """
        Chunk an Act (BNS, BSA, IT Act) into Sections, Sub-sections, Chapters, and Parts.
        """
        chunks: list[LegalChunk] = []
        lines_with_page = self._extract_clean_lines_with_page(doc.pages)

        current_part: Optional[str] = None
        current_chapter: Optional[str] = None

        # Filter out footnote lines and index lines
        # For IT Act, body starts after section index (around page 4)
        start_page = 1
        if doc.short_name == "IT_Act":
            for p_no, line in lines_with_page:
                if "CHAPTER I" in line and p_no >= 4:
                    start_page = p_no
                    break

        valid_lines = [
            (page_no, line)
            for page_no, line in lines_with_page
            if page_no >= start_page and not is_footnote_line(line)
        ]

        # Regex for Section headers:
        # e.g.: "317. (1) Property, the possession..." or "65. Tampering with..."
        # or explicit "Section 65..."
        sec_regex = re.compile(
            r"^(?:(?:Section|SECTION)\s+(\d+[A-Z]?)|(\d+[A-Z]?)\.\s+([A-Z(][^\n]{2,100}))$"
        )

        current_sec_num: Optional[str] = None
        current_sec_title: Optional[str] = None
        current_sec_lines: list[str] = []
        current_sec_start_page = 1
        current_sec_end_page = 1

        def flush_current_section():
            if not current_sec_num or not current_sec_lines:
                return
            sec_text = "\n".join(current_sec_lines).strip()
            if not sec_text:
                return

            prefix_id = doc.short_name.lower().replace(" ", "_")
            parent_id = f"{prefix_id}_sec_{current_sec_num.lower()}"

            sub_chunks = self._subchunk_legal_provision(
                act_name=doc.act_name,
                short_name=doc.short_name,
                provision_label=f"Section {current_sec_num}",
                section_num=f"Section {current_sec_num}",
                article_num=None,
                title=current_sec_title or f"Section {current_sec_num}",
                part=current_part,
                chapter=current_chapter,
                text=sec_text,
                parent_id=parent_id,
                page_start=current_sec_start_page,
                page_end=current_sec_end_page,
                source_file=doc.source_file,
                year=doc.year,
                default_type="section",
            )
            chunks.extend(sub_chunks)

        for page_no, line in valid_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Detect PART header
            part_match = re.match(r"^PART\s+([IVXLCDM\d]+[A-Z]?(?:\s*[-–—]\s*[^\n]+)?)$", stripped, re.IGNORECASE)
            if part_match:
                current_part = stripped
                continue

            # Detect CHAPTER header
            chap_match = re.match(r"^CHAPTER\s+([IVXLCDM\d]+[A-Z]?(?:\s*[-–—]\s*[^\n]+)?)$", stripped, re.IGNORECASE)
            if chap_match:
                current_chapter = stripped
                continue

            # Detect Section header
            sec_match = sec_regex.match(stripped)
            if sec_match:
                num = sec_match.group(1) or sec_match.group(2)
                initial_content = (sec_match.group(3) or "").strip()

                combined = initial_content.lower()
                if any(
                    kw in combined
                    for kw in [
                        "amendment",
                        "subs. by",
                        "ins. by",
                        "renumbered",
                        "w.e.f.",
                        "omitted by",
                        "ibid",
                    ]
                ):
                    if current_sec_num:
                        current_sec_lines.append(stripped)
                    continue

                flush_current_section()

                # Extract title if present before em-dash or period
                title = f"Section {num}"
                if initial_content and not initial_content.startswith("("):
                    title_split = re.split(r"[—–-]", initial_content, maxsplit=1)
                    title = title_split[0].strip()

                current_sec_num = num
                current_sec_title = title
                current_sec_start_page = page_no
                current_sec_end_page = page_no
                current_sec_lines = [stripped]
            else:
                if current_sec_num:
                    current_sec_lines.append(stripped)
                    current_sec_end_page = page_no

        flush_current_section()
        logger.info("Generated %d chunks for '%s'", len(chunks), doc.act_name)
        return chunks

    # -------------------------------------------------------------------------
    # Sub-provision hierarchical chunking (Provisos, Sub-sections, Explanations)
    # -------------------------------------------------------------------------

    def _subchunk_legal_provision(
        self,
        act_name: str,
        short_name: str,
        provision_label: str,
        section_num: Optional[str],
        article_num: Optional[str],
        title: Optional[str],
        part: Optional[str],
        chapter: Optional[str],
        text: str,
        parent_id: str,
        page_start: int,
        page_end: int,
        source_file: str,
        year: int,
        default_type: str,
    ) -> list[LegalChunk]:
        """
        If a section or article fits comfortably in max_chunk_size, return it as a single chunk.
        Otherwise, split intelligently along sub-sections (1), (2), Provisos, and Explanations,
        prepended with parent statutory context.
        """
        # Context header added to ensure LLM / dense retrieval retains complete grounding
        context_header = f"[{act_name} | {provision_label}"
        if title and title != provision_label:
            context_header += f": {title}"
        context_header += "]\n"

        # If full text fits within chunk size, return single clean chunk
        if len(text) <= self.max_chunk_size:
            return [
                LegalChunk(
                    chunk_id=parent_id,
                    text=f"{context_header}{text}",
                    act_name=act_name,
                    short_name=short_name,
                    section=section_num,
                    article=article_num,
                    title=title,
                    chapter=chapter,
                    part=part,
                    page=page_start,
                    page_end=page_end,
                    chunk_type=default_type,
                    parent_chunk_id=None,
                    source_file=source_file,
                    year=year,
                )
            ]

        # Split along legal structural dividers:
        # - Sub-sections: \n(\d+)\s+
        # - Provisos: \nProvided that / Provided further that
        # - Explanations: \nExplanation / Explanation 1
        split_pattern = (
            r"(?=(?:\n\s*\(\d+\)\s+|\n\s*Provided\s+(?:that|further)|\n\s*Explanation(?:\s+\d+)?\.?[—–-]))"
        )
        sub_units = re.split(split_pattern, text)
        sub_units = [u.strip() for u in sub_units if u.strip()]

        # If unable to split cleanly into structural units, fall back to paragraph split
        if len(sub_units) <= 1:
            sub_units = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks: list[LegalChunk] = []
        for idx, unit in enumerate(sub_units, start=1):
            unit_type = default_type
            if re.match(r"^\(\d+\)", unit):
                unit_type = "sub_section"
            elif unit.lower().startswith("provided"):
                unit_type = "proviso"
            elif unit.lower().startswith("explanation"):
                unit_type = "explanation"

            sub_id = f"{parent_id}_p{idx}" if idx > 1 else parent_id
            full_chunk_text = f"{context_header}{unit}"

            chunks.append(
                LegalChunk(
                    chunk_id=sub_id,
                    text=full_chunk_text,
                    act_name=act_name,
                    short_name=short_name,
                    section=section_num,
                    article=article_num,
                    title=title,
                    chapter=chapter,
                    part=part,
                    page=page_start,
                    page_end=page_end,
                    chunk_type=unit_type,
                    parent_chunk_id=parent_id if idx > 1 else None,
                    source_file=source_file,
                    year=year,
                )
            )

        return chunks

    def _extract_clean_lines_with_page(self, pages: list[PDFPage]) -> list[tuple[int, str]]:
        """Clean each page text and associate every line with its source page number."""
        lines_with_page: list[tuple[int, str]] = []
        for page in pages:
            cleaned_page = clean_legal_text(page.text)
            for line in cleaned_page.splitlines():
                stripped = line.strip()
                if stripped:
                    lines_with_page.append((page.page_number, stripped))
        return lines_with_page


# Functional helper for quick chunking
def chunk_legal_document(text: str, act_name: str, year: int, source_file: str = "document.pdf") -> list[dict]:
    """Backward-compatible helper returning list of dicts."""
    is_const = "constitution" in act_name.lower()
    page = PDFPage(page_number=1, text=text, source_file=source_file)
    doc = LegalDocument(
        act_name=act_name,
        short_name=act_name[:10].strip(),
        year=year,
        document_type="constitution" if is_const else "act",
        source_file=source_file,
        file_path=None,
        pages=[page],
    )
    chunker = LegalAwareChunker()
    chunks = chunker.chunk_document(doc)
    return [{"text": c.text, "metadata": c.to_metadata()} for c in chunks]
