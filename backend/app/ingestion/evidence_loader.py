"""
Standardized Evidence PDF Loader for AI Court of India.

Loads page-by-page text from Evidence PDFs with strict Ground Truth isolation.
Rejects evaluation verdict files while safely preserving legitimate procedural citations.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import pymupdf
from rag.loader import PDFPage

logger = logging.getLogger(__name__)


class MalformedEvidencePDFError(ValueError):
    """Raised when an Evidence PDF cannot be read or contains no extractable text."""
    pass


class GroundTruthLeakageError(PermissionError):
    """Raised when an evaluation Ground Truth or Real Verdict document is detected."""
    pass


class EvidencePDFLoader:
    """
    Loads and validates Standardized Evidence PDFs page by page.
    Guarantees that Ground Truth Verdict documents cannot enter the evidentiary pipeline.
    """

    FORBIDDEN_FILE_PATTERNS = [
        r"ground[-_]?truth",
        r"real[-_]?verdict",
        r"actual[-_]?judgment",
        r"hidden[-_]?verdict",
        r"verdict[-_]?benchmark",
    ]

    FORBIDDEN_TEXT_PATTERNS = [
        r"\bground\s*truth\s*verdict\b",
        r"\breal\s*verdict\b",
        r"\bactual\s*judgment\s*outcome\b",
        r"\bhidden\s*evaluation\s*verdict\b",
        r"\bfinal\s*verdict\s*:\s*(?:guilty|acquitted|convicted)\b",
    ]

    def validate_document_security(self, path_or_name: str | Path, full_text: Optional[str] = None) -> None:
        """
        Validate that the document is not an evaluation Ground Truth verdict.
        Legitimate procedural mentions ('court', 'judgment dated', 'order of release') are permitted.
        """
        filename = Path(path_or_name).name.lower()
        for pat in self.FORBIDDEN_FILE_PATTERNS:
            if re.search(pat, filename):
                raise GroundTruthLeakageError(
                    f"SECURITY VIOLATION: Evidence PDF Loader rejected '{filename}'. "
                    f"Evaluation verdict and Ground Truth documents must never enter the evidentiary pipeline."
                )

        if full_text:
            text_lower = full_text.lower()
            # Flag explicit ground truth / real verdict declaration headers
            for pat in self.FORBIDDEN_TEXT_PATTERNS:
                if re.search(pat, text_lower):
                    raise GroundTruthLeakageError(
                        f"SECURITY VIOLATION: Document contains forbidden evaluation verdict marker: '{pat}'."
                    )

            # Combined check for ground truth verdict leakage
            if "final verdict" in text_lower and "ground truth" in text_lower:
                raise GroundTruthLeakageError(
                    "SECURITY VIOLATION: Document appears to contain evaluation Ground Truth verdict."
                )

    def load_pdf(self, pdf_path: str | Path) -> list[PDFPage]:
        """
        Extract pages from an Evidence PDF.

        Args:
            pdf_path: File path to Evidence PDF.

        Returns:
            List of PDFPage instances with 1-indexed page numbering and text.
        """
        path = Path(pdf_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Evidence PDF not found: {path}")

        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise MalformedEvidencePDFError(f"Target is not a valid PDF file: {path.name}")

        self.validate_document_security(path)

        pages: list[PDFPage] = []
        try:
            doc = pymupdf.open(str(path))
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                pages.append(
                    PDFPage(
                        page_number=page_idx,
                        text=text,
                        source_file=path.name,
                    )
                )
            doc.close()
        except Exception as e:
            if isinstance(e, (GroundTruthLeakageError, FileNotFoundError)):
                raise
            logger.error("Failed to parse PDF '%s': %s", path, e)
            raise MalformedEvidencePDFError(f"Could not parse Evidence PDF '{path.name}': {e}") from e

        # Validate that document contains readable content
        has_text = any(bool(p.text) for p in pages)
        if not pages or not has_text:
            raise MalformedEvidencePDFError(f"Evidence PDF '{path.name}' is empty or contains no extractable text.")

        # Text-level security validation
        full_text = "\n".join(p.text for p in pages)
        self.validate_document_security(path, full_text=full_text)

        logger.info("Successfully loaded Evidence PDF '%s' (%d pages)", path.name, len(pages))
        return pages

    def load_text(self, text: str, source_filename: str = "Evidence_Packet.pdf") -> list[PDFPage]:
        """
        Parse raw text into PDFPage representations (for text-based or test fixtures).
        """
        if not text or not text.strip():
            raise MalformedEvidencePDFError("Evidence text is empty or whitespace.")

        self.validate_document_security(source_filename, full_text=text)

        # Detect any [Page X] demarcations
        page_splits = re.split(r"\[Page\s*(\d+)\]", text, flags=re.IGNORECASE)
        pages: list[PDFPage] = []

        if len(page_splits) > 1:
            # First element might be pre-page header
            curr_page = 1
            for i in range(1, len(page_splits), 2):
                p_num = int(page_splits[i])
                p_text = page_splits[i + 1].strip()
                pages.append(PDFPage(page_number=p_num, text=p_text, source_file=source_filename))
        else:
            pages.append(PDFPage(page_number=1, text=text.strip(), source_file=source_filename))

        return pages
