"""
AI Court of India - Legal RAG Package.
Phase 1 implementation for Indian Legal Retrieval-Augmented Generation.
"""

from rag.chunker import LegalAwareChunker, LegalChunk
from rag.cleaner import clean_legal_text
from rag.config import RAGConfig, config
from rag.embeddings import EmbeddingModel
from rag.loader import LegalDocument, PDFLoader, PDFPage
from rag.retriever import LegalRetriever, RetrievalResult
from rag.vector_store import LegalVectorStore

__all__ = [
    "RAGConfig",
    "config",
    "PDFLoader",
    "PDFPage",
    "LegalDocument",
    "clean_legal_text",
    "LegalAwareChunker",
    "LegalChunk",
    "EmbeddingModel",
    "LegalVectorStore",
    "LegalRetriever",
    "RetrievalResult",
]
