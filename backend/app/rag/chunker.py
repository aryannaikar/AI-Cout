"""Forwarder to rag.chunker for backward compatibility."""
from rag.cleaner import clean_legal_text as clean_text
from rag.chunker import LegalAwareChunker, LegalChunk, chunk_legal_document

__all__ = ["clean_text", "LegalAwareChunker", "LegalChunk", "chunk_legal_document"]