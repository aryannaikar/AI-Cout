"""Forwarder to rag.loader for backward compatibility."""
from rag.loader import PDFLoader, PDFPage, LegalDocument, extract_pdf_pages, extract_pdf_text

__all__ = ["PDFLoader", "PDFPage", "LegalDocument", "extract_pdf_pages", "extract_pdf_text"]