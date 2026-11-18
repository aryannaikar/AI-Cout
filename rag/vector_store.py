"""
Vector store implementation using ChromaDB for persistent legal corpus indexing.
Guarantees idempotency and duplicate prevention via deterministic chunk IDs and upsert.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

try:
    import grpc
except Exception:
    import sys
    import warnings
    from unittest.mock import MagicMock
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="opentelemetry")
    mock_grpc = MagicMock()
    mock_grpc.__version__ = "1.63.2"
    sys.modules["grpc"] = mock_grpc
    sys.modules["grpc._compression"] = MagicMock()
    sys.modules["grpc._cython"] = MagicMock()
    sys.modules["grpc._cython.cygrpc"] = MagicMock()

import chromadb
from chromadb.config import Settings

from rag.chunker import LegalChunk
from rag.config import config

logger = logging.getLogger(__name__)


import threading


class LegalVectorStore:
    """
    ChromaDB-backed persistent vector store for the Indian Legal Corpus.
    Provides idempotent upserts, metadata querying, collection clearing,
    and semantic similarity search.
    """

    _client_cache: dict[str, Any] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        persist_directory: Optional[str | Path] = None,
        collection_name: Optional[str] = None,
    ):
        self.persist_directory = Path(persist_directory or config.vectorstore_dir).resolve()
        self.collection_name = collection_name or config.collection_name

        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        path_key = str(self.persist_directory)
        with LegalVectorStore._lock:
            if path_key not in LegalVectorStore._client_cache:
                logger.info(
                    "Initializing ChromaDB at '%s', collection '%s'",
                    self.persist_directory,
                    self.collection_name,
                )
                LegalVectorStore._client_cache[path_key] = chromadb.PersistentClient(
                    path=path_key,
                    settings=Settings(anonymized_telemetry=False),
                )
            self.client = LegalVectorStore._client_cache[path_key]

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "AI Court of India - Legal Corpus"},
            )

    def add_chunks(
        self,
        chunks: list[LegalChunk],
        embeddings: list[list[float]],
        batch_size: int = 500,
    ) -> int:
        """
        Idempotently insert or update legal chunks into ChromaDB.
        Using collection.upsert ensures that running ingestion multiple times
        will NOT create duplicate chunks.

        Args:
            chunks: List of LegalChunk objects.
            embeddings: Corresponding embedding vectors.
            batch_size: ChromaDB insertion batch limit (default 500).

        Returns:
            Number of chunks upserted.
        """
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
            )

        total_upserted = 0
        total = len(chunks)

        for i in range(0, total, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            ids = [chunk.chunk_id for chunk in batch_chunks]
            documents = [chunk.text for chunk in batch_chunks]
            metadatas = [chunk.to_metadata() for chunk in batch_chunks]

            # Upsert ensures idempotent insertion without duplicates
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=batch_embeddings,
                metadatas=metadatas,
            )
            total_upserted += len(batch_chunks)
            logger.debug("Upserted %d/%d chunks", total_upserted, total)

        logger.info("Successfully upserted %d chunks into ChromaDB", total_upserted)
        return total_upserted

    def add_documents(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        ids: list[str],
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Backward-compatible raw insertion method supporting metadatas."""
        if metadatas is None:
            metadatas = [{} for _ in ids]
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict[str, list]:
        """
        Perform vector similarity search.

        Args:
            query_embedding: Dense embedding vector of the search query.
            n_results: Number of results to return.
            where: Optional metadata filter dict (e.g. {"short_name": "BNS"}).

        Returns:
            Dictionary with 'ids', 'documents', 'metadatas', 'distances'.
        """
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        return self.collection.query(**kwargs)

    def count(self) -> int:
        """Return total number of chunks currently stored in the collection."""
        return self.collection.count()

    def clear(self) -> None:
        """Delete all documents in the collection by deleting and recreating it."""
        logger.warning("Clearing collection '%s'", self.collection_name)
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "AI Court of India - Legal Corpus"},
        )

    def get_by_id(self, chunk_id: str) -> Optional[dict]:
        """Retrieve a specific chunk by its deterministic ID."""
        res = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if res and res["ids"] and len(res["ids"]) > 0:
            return {
                "id": res["ids"][0],
                "document": res["documents"][0] if res["documents"] else "",
                "metadata": res["metadatas"][0] if res["metadatas"] else {},
            }
        return None
