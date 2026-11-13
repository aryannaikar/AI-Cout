"""
PDF loading and text extraction module for Indian legal documents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pymupdf

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Represents a single page extracted from a PDF document."""

    page_number: int
    text: str
    source_file: str


@dataclass
class LegalDocument:
    """Represents a loaded legal document containing page-level texts and metadata."""

    act_name: str
    short_name: str
    year: int
    document_type: str  # "constitution" or "act"
    source_file: str
    file_path: Path
    pages: list[PDFPage]

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


# Known legal documents registry for canonical names and metadata
KNOWN_DOCUMENTS_META = {
    "constitution": {
        "act_name": "Constitution of India",
        "short_name": "Constitution",
        "year": 1950,
        "document_type": "constitution",
    },
    "bns": {
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "short_name": "BNS",
        "year": 2023,
        "document_type": "act",
    },
    "bsa": {
        "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "short_name": "BSA",
        "year": 2023,
        "document_type": "act",
    },
    "it_act": {
        "act_name": "Information Technology Act, 2000",
        "short_name": "IT_Act",
        "year": 2000,
        "document_type": "act",
    },
}


class PDFLoader:
    """Loads and extracts text from legal PDF documents with page-level tracking."""

    @staticmethod
    def _validate_security(path: Path) -> None:
        """Enforce strict isolation: never load verdict or judgment files into legal corpus."""
        name_lower = path.name.lower()
        if "verdict" in name_lower or "ground_truth" in name_lower or "judgment" in name_lower:
            raise PermissionError(
                f"SECURITY VIOLATION: '{path.name}' is a verdict/evaluation file and "
                f"MUST NOT be loaded into the legal RAG pipeline."
            )

    def load_pdf(self, pdf_path: str | Path) -> list[PDFPage]:
        """
        Extract text from a PDF page by page.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of PDFPage instances.
        """
        path = Path(pdf_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF document not found: {path}")

        self._validate_security(path)

        pages: list[PDFPage] = []
        try:
            doc = pymupdf.open(str(path))
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append(
                        PDFPage(
                            page_number=page_idx,
                            text=text,
                            source_file=path.name,
                        )
                    )
            doc.close()
        except Exception as e:
            logger.error("Failed to load PDF '%s': %s", path, e)
            raise

        if not pages:
            logger.warning("PDF '%s' produced zero text pages (scanned/empty?).", path.name)

        return pages

    def load_document(self, pdf_path: str | Path, act_name: Optional[str] = None, year: Optional[int] = None) -> LegalDocument:
        """
        Load a single PDF and construct a LegalDocument with metadata.
        """
        path = Path(pdf_path).resolve()
        self._validate_security(path)
        pages = self.load_pdf(path)

        # Detect canonical metadata from filename or directory
        meta = self._infer_metadata(path, act_name, year)

        return LegalDocument(
            act_name=meta["act_name"],
            short_name=meta["short_name"],
            year=meta["year"],
            document_type=meta["document_type"],
            source_file=path.name,
            file_path=path,
            pages=pages,
        )

    def load_corpus(self, corpus_dir: str | Path) -> list[LegalDocument]:
        """
        Load all legal documents from the legal corpus directory.
        """
        corpus_path = Path(corpus_dir).resolve()
        if not corpus_path.exists():
            raise FileNotFoundError(f"Legal corpus directory not found: {corpus_path}")

        documents: list[LegalDocument] = []
        pdf_files = sorted(corpus_path.glob("**/*.pdf"))

        for pdf_file in pdf_files:
            # Skip verdict files if any are mistakenly placed
            try:
                self._validate_security(pdf_file)
            except PermissionError as e:
                logger.warning("Skipping prohibited file: %s", e)
                continue

            doc = self.load_document(pdf_file)
            documents.append(doc)
            logger.info("Loaded '%s' with %d pages", doc.act_name, doc.total_pages)

        return documents

    @staticmethod
    def _infer_metadata(path: Path, act_name: Optional[str] = None, year: Optional[int] = None) -> dict:
        filename_lower = path.name.lower()
        parent_lower = path.parent.name.lower()

        # Check against known registry
        for key, meta in KNOWN_DOCUMENTS_META.items():
            if key in filename_lower or key in parent_lower:
                return meta.copy()

        # Specific heuristics for common names
        if "sakshya" in filename_lower or "bsa" in filename_lower:
            return KNOWN_DOCUMENTS_META["bsa"].copy()
        if "nyaya" in filename_lower or "bns" in filename_lower:
            return KNOWN_DOCUMENTS_META["bns"].copy()
        if "constitution" in filename_lower:
            return KNOWN_DOCUMENTS_META["constitution"].copy()
        if "technology" in filename_lower or "it_act" in filename_lower:
            return KNOWN_DOCUMENTS_META["it_act"].copy()

        # Fallback metadata
        inferred_name = act_name or path.stem.replace("_", " ").title()
        is_const = "constitution" in inferred_name.lower()
        return {
            "act_name": inferred_name,
            "short_name": inferred_name[:10].strip(),
            "year": year or 2023,
            "document_type": "constitution" if is_const else "act",
        }


# Backward-compatible functional helpers
def extract_pdf_pages(pdf_path: str) -> list[dict]:
    """Extract pages as list of dicts: [{'page': 1, 'text': '...'}]"""
    loader = PDFLoader()
    pages = loader.load_pdf(pdf_path)
    return [{"page": p.page_number, "text": p.text} for p in pages]


def extract_pdf_text(pdf_path: str) -> str:
    """Extract complete text of PDF as single string."""
    loader = PDFLoader()
    pages = loader.load_pdf(pdf_path)
    return "\n\n".join(p.text for p in pages)
