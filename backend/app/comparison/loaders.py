"""
Document and artifact loaders for Phase 5 — AI Court Judgment Comparison Engine.
Supports PDF, TXT, and JSON formats for AI Judgment, Real Court Judgment, and
optional supporting Case Packet.
Maintains absolute isolation: Real Court Judgment is loaded solely for comparison.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

import pymupdf

from app.comparison.errors import (
    AIJudgmentNotFoundError,
    InvalidJudgmentFormatError,
    RealJudgmentNotFoundError,
)
from app.models.judgment_models import Judgment

logger = logging.getLogger(__name__)


class ComparisonDocumentLoader:
    """
    Safely loads documents for comparison from filesystem paths, raw text,
    JSON dicts, or byte streams.
    """

    @classmethod
    def extract_text_from_pdf_bytes(cls, pdf_bytes: bytes) -> str:
        """Extract all textual content from a PDF byte array using PyMuPDF."""
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return full_text.strip()
        except Exception as e:
            raise InvalidJudgmentFormatError(f"Failed to extract text from PDF: {e}") from e

    @classmethod
    def extract_text_from_pdf_path(cls, pdf_path: Union[str, Path]) -> str:
        """Extract all textual content from a PDF file on disk."""
        p = Path(pdf_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        try:
            doc = pymupdf.open(str(p))
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return full_text.strip()
        except Exception as e:
            raise InvalidJudgmentFormatError(f"Failed to extract text from PDF '{p}': {e}") from e

    @classmethod
    def load_ai_judgment(
        cls, source: Union[str, Path, bytes, dict, Judgment]
    ) -> Union[Judgment, dict, str]:
        """
        Load an AI Judgment.
        Accepts:
        - Judgment Pydantic model instance
        - dict matching Judgment schema
        - Path or filename pointing to ai_judgment.json, ai_judgment.txt, or ai_judgment.pdf
        - raw JSON string or plain text
        - bytes of PDF or JSON
        """
        if isinstance(source, Judgment):
            return source

        if isinstance(source, dict):
            try:
                return Judgment.model_validate(source)
            except Exception:
                return source

        if isinstance(source, bytes):
            if source.startswith(b"%PDF-"):
                text = cls.extract_text_from_pdf_bytes(source)
                return text
            # Try parsing as JSON
            try:
                data = json.loads(source.decode("utf-8"))
                return Judgment.model_validate(data)
            except Exception:
                return source.decode("utf-8", errors="replace")

        if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and len(source) < 500):
            p = Path(source)
            if p.is_file():
                suffix = p.suffix.lower()
                if suffix == ".json":
                    try:
                        content = p.read_text(encoding="utf-8")
                        data = json.loads(content)
                        return Judgment.model_validate(data)
                    except Exception as e:
                        raise InvalidJudgmentFormatError(f"Failed to parse AI judgment JSON '{p}': {e}") from e
                elif suffix == ".pdf":
                    return cls.extract_text_from_pdf_path(p)
                elif suffix in [".txt", ".md"]:
                    return p.read_text(encoding="utf-8")
                else:
                    return p.read_text(encoding="utf-8", errors="replace")

        # Assume raw string
        if isinstance(source, str):
            clean = source.strip()
            if clean.startswith("{") and clean.endswith("}"):
                try:
                    data = json.loads(clean)
                    return Judgment.model_validate(data)
                except Exception:
                    pass
            return source

        raise InvalidJudgmentFormatError(f"Unsupported AI Judgment input type: {type(source)}")

    @classmethod
    def load_real_judgment(
        cls, source: Union[str, Path, bytes, dict]
    ) -> Union[dict, str]:
        """
        Load a Real Court Judgment / Ground Truth.
        Accepts:
        - Path to PDF, TXT, or JSON
        - bytes of PDF, TXT, or JSON
        - raw string (plain text or JSON)
        - dict (if pre-structured)
        """
        if source is None:
            raise RealJudgmentNotFoundError("Real Court Judgment input cannot be None.")

        if isinstance(source, dict):
            return source

        if isinstance(source, bytes):
            if source.startswith(b"%PDF-"):
                return cls.extract_text_from_pdf_bytes(source)
            try:
                text = source.decode("utf-8")
                if text.strip().startswith("{") and text.strip().endswith("}"):
                    return json.loads(text)
                return text
            except Exception:
                return source.decode("utf-8", errors="replace")

        if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and len(source) < 500):
            p = Path(source)
            if p.is_file():
                suffix = p.suffix.lower()
                if suffix == ".pdf":
                    return cls.extract_text_from_pdf_path(p)
                elif suffix == ".json":
                    try:
                        return json.loads(p.read_text(encoding="utf-8"))
                    except Exception as e:
                        raise InvalidJudgmentFormatError(f"Failed to parse Real judgment JSON '{p}': {e}") from e
                elif suffix in [".txt", ".md"]:
                    return p.read_text(encoding="utf-8")
                else:
                    return p.read_text(encoding="utf-8", errors="replace")

        if isinstance(source, str):
            clean = source.strip()
            if clean.startswith("{") and clean.endswith("}"):
                try:
                    return json.loads(clean)
                except Exception:
                    pass
            return source

        raise InvalidJudgmentFormatError(f"Unsupported Real Court Judgment input type: {type(source)}")

    @classmethod
    def load_case_packet(
        cls, source: Optional[Union[str, Path, bytes]] = None
    ) -> Optional[str]:
        """
        Load optional supporting Case Packet context (PDF or TXT).
        Returns None if source is not provided.
        """
        if source is None:
            return None

        if isinstance(source, bytes):
            if source.startswith(b"%PDF-"):
                return cls.extract_text_from_pdf_bytes(source)
            return source.decode("utf-8", errors="replace")

        if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and len(source) < 500):
            p = Path(source)
            if p.is_file():
                if p.suffix.lower() == ".pdf":
                    return cls.extract_text_from_pdf_path(p)
                return p.read_text(encoding="utf-8", errors="replace")

        if isinstance(source, str):
            return source

        return None
