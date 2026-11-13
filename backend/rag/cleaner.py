"""
Text cleaning and normalization utilities for Indian legal documents.
"""

from __future__ import annotations

import re


def clean_unicode_artifacts(text: str) -> str:
    """
    Remove unprintable characters, null bytes, and normalize unicode punctuation.
    """
    # Remove null bytes, replacement characters, zero-width spaces
    text = text.replace("\x00", " ")
    text = text.replace("\ufffd", " ")  # Replacement character
    text = text.replace("\u200b", "")   # Zero-width space
    text = text.replace("\xa0", " ")    # Non-breaking space
    text = text.replace("\u2016", " ")  # Double vertical line

    # Normalize smart single/double quotes
    text = re.sub(r"[\u2018\u2019\u201a\u201b]", "'", text)
    text = re.sub(r"[\u201c\u201d\u201e\u201f]", '"', text)

    # Normalize dashes and hyphens
    # Em-dash and horizontal bar
    text = re.sub(r"[\u2014\u2015]", "—", text)
    # En-dash
    text = re.sub(r"[\u2013]", "–", text)
    # Minus or other hyphens
    text = re.sub(r"[\u2212\u2010\u2011\u2012]", "-", text)

    return text


def remove_running_headers_and_footers(text: str) -> str:
    """
    Remove repetitive gazette headers, footers, and isolated page numbers.
    """
    # Remove Gazette of India headers
    text = re.sub(
        r"(?i)THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY[^\n]*",
        "",
        text,
    )
    text = re.sub(
        r"(?i)\[PART\s+II[^\n]*SEC(?:TION)?\.?\s*1\]",
        "",
        text,
    )

    # Remove running headers like "SEC. 1] THE GAZETTE OF INDIA EXTRAORDINARY"
    text = re.sub(
        r"(?i)SEC\.?\s*\d+\]\s*THE\s+GAZETTE[^\n]*",
        "",
        text,
    )

    # Remove isolated page numbers at start or end of lines:
    # e.g., line containing only "23" or "[23]"
    text = re.sub(r"(?m)^\s*\[?\d{1,4}\]?\s*$", "", text)

    return text


def clean_legal_text(text: str) -> str:
    """
    Full cleaning pipeline for legal documents while preserving
    statutory structure (Sections, Articles, Sub-clauses, Provisos).
    """
    if not text:
        return ""

    # Step 1: Clean unicode artifacts and smart punctuation
    text = clean_unicode_artifacts(text)

    # Step 2: Remove running headers/footers
    text = remove_running_headers_and_footers(text)

    # Step 3: Normalize spaces and tabs (preserve newlines)
    text = re.sub(r"[ \t]+", " ", text)

    # Step 4: Fix broken line-wrapped words (e.g. "com-\nputer" -> "computer")
    text = re.sub(r"(\b\w+)-\n(\w+\b)", r"\1\2", text)

    # Step 5: Normalize newlines (max 2 consecutive newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def is_footnote_line(line: str) -> bool:
    """
    Detect if a line is an amendment footnote or legislative citation note.
    """
    trimmed = line.strip()
    if re.match(
        r"^\d+\.?\s*(?:Subs\.|Ins\.|The words|Omitted|Added|Cl\.|Cls\.|Art\.|Arts\.|Part\s+[IVXLCDM\d]|See\s+|w\.e\.f\.|Clause|Certain|The bracket|Explanation\s+\d+|In\s+s\.)",
        trimmed,
        re.IGNORECASE,
    ):
        return True
    if re.search(
        r"(?:by\s+the\s+Constitution\s*\([^)]*Amendment\)|Subs\.\s+by\s+Act|Ins\.\s+by\s+Act|w\.e\.f\.\s+\d+|s\.\s*\d+,\s*ibid\.)",
        trimmed,
        re.IGNORECASE,
    ):
        return True
    return False
