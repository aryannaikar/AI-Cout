"""
Configuration settings for the Legal RAG pipeline of AI Court of India.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Find project root (directory containing data, rag, or README.md)
CURRENT_FILE = Path(__file__).resolve()


def _find_project_root() -> Path:
    current = CURRENT_FILE.parent
    for _ in range(4):
        if (current / "backend").is_dir() and (current / "data").is_dir():
            return current
        if (current / "README.md").exists() or (current / ".git").exists():
            return current
        if (current / "data").exists() and current.name != "backend":
            return current
        if current.parent == current:
            break
        current = current.parent
    return CURRENT_FILE.parent.parent


PROJECT_ROOT = _find_project_root()

# Load environment variables from .env if present
env_paths = [
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "backend" / ".env",
]
for env_file in env_paths:
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)


@dataclass
class RAGConfig:
    """Central configuration for Legal RAG."""

    # Project paths
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    legal_corpus_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "legal_corpus")
    cases_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "cases")
    vectorstore_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "vectorstore")

    # Vector store settings
    collection_name: str = os.getenv("COLLECTION_NAME", "indian_legal_corpus")

    # Embedding model settings
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

    # Chunking settings
    chunk_max_size: int = int(os.getenv("CHUNK_MAX_SIZE", "1500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # Retrieval settings
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    retrieval_candidate_k: int = int(os.getenv("RETRIEVAL_CANDIDATE_K", "20"))
    hybrid_rrf_k: int = int(os.getenv("HYBRID_RRF_K", "60"))

    # Reranker settings
    reranker_model_name: str = os.getenv(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    use_reranker: bool = os.getenv("USE_RERANKER", "true").lower() in {"1", "true", "yes"}

    # Reranker settings
    use_reranker: bool = os.getenv("USE_RERANKER", "true").lower() == "true"
    reranker_model_name: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    def __post_init__(self):
        # Disable noisy symlink warnings from huggingface_hub
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        
        # Override with environment variables if present
        if os.getenv("CHROMA_DB_PATH"):
            self.vectorstore_dir = Path(os.getenv("CHROMA_DB_PATH")).resolve()
        if os.getenv("LEGAL_CORPUS_DIR"):
            self.legal_corpus_dir = Path(os.getenv("LEGAL_CORPUS_DIR")).resolve()
        if os.getenv("COLLECTION_NAME"):
            self.collection_name = os.getenv("COLLECTION_NAME")


# Global default configuration instance
config = RAGConfig()
