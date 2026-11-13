"""
Corpus ingestion script for Indian Legal RAG.
Loads PDFs from legal_corpus, applies legal chunking, generates embeddings,
and stores in persistent ChromaDB.

Usage:
    python -m rag.ingest
    python -m rag.ingest --rebuild
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from rag.chunker import LegalAwareChunker
from rag.config import config
from rag.embeddings import EmbeddingModel
from rag.loader import PDFLoader
from rag.vector_store import LegalVectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rag.ingest")


def run_ingestion(
    corpus_dir: Path | None = None,
    rebuild: bool = False,
    batch_size: int = 64,
) -> int:
    """
    Execute full legal corpus ingestion.

    Args:
        corpus_dir: Directory containing legal corpus subdirectories.
        rebuild: If True, clears existing vector collection first.
        batch_size: Batch size for embedding generation.

    Returns:
        Total number of chunks indexed.
    """
    start_time = time.time()
    corpus_path = corpus_dir or config.legal_corpus_dir

    print("=" * 70)
    print("AI COURT OF INDIA - LEGAL CORPUS INGESTION")
    print("=" * 70)
    print(f"Legal Corpus Directory: {corpus_path}")
    print(f"Vector Store Directory: {config.vectorstore_dir}")
    print(f"Collection Name:        {config.collection_name}")
    print(f"Embedding Model:        {config.embedding_model_name}")
    print(f"Rebuild Mode:           {rebuild}")
    print("=" * 70)

    loader = PDFLoader()
    chunker = LegalAwareChunker(
        max_chunk_size=config.chunk_max_size,
        chunk_overlap=config.chunk_overlap,
    )
    vector_store = LegalVectorStore()

    if rebuild:
        print("\n[!] Rebuild requested. Clearing existing vector collection...")
        vector_store.clear()
        print("    Collection cleared.")

    # 1. Load PDFs
    print("\n[1/4] Loading PDF documents from legal corpus...")
    documents = loader.load_corpus(corpus_path)
    if not documents:
        print(f"ERROR: No valid PDF documents found in '{corpus_path}'!")
        sys.exit(1)

    print(f"      Loaded {len(documents)} statutes/acts.")

    # 2. Chunk documents
    print("\n[2/4] Chunking legal documents with legal structure preservation...")
    all_chunks = []
    doc_chunk_stats = {}

    for doc in documents:
        doc_chunks = chunker.chunk_document(doc)
        all_chunks.extend(doc_chunks)
        doc_chunk_stats[doc.act_name] = len(doc_chunks)
        print(f"      - {doc.act_name}: {doc.total_pages} pages -> {len(doc_chunks)} legal chunks")

    print(f"      Total legal chunks generated: {len(all_chunks)}")

    # 3. Generate Embeddings
    print(f"\n[3/4] Generating dense embeddings using '{config.embedding_model_name}'...")
    embedding_model = EmbeddingModel()
    texts = [chunk.text for chunk in all_chunks]

    emb_start = time.time()
    embeddings = embedding_model.encode(
        texts=texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    emb_elapsed = time.time() - emb_start
    print(f"      Generated {len(embeddings)} embeddings in {emb_elapsed:.2f}s "
          f"({len(embeddings) / max(0.01, emb_elapsed):.1f} chunks/sec).")

    # 4. Upsert into ChromaDB
    print("\n[4/4] Storing chunks idempotently into ChromaDB...")
    upserted = vector_store.add_chunks(all_chunks, embeddings)
    total_in_store = vector_store.count()

    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    for act, count in doc_chunk_stats.items():
        print(f"  * {act}: {count} chunks")
    print(f"\n  Total chunks upserted this run: {upserted}")
    print(f"  Total chunks in ChromaDB:      {total_in_store}")
    print(f"  Total time elapsed:            {total_time:.2f} seconds")
    print("=" * 70)
    print("Legal RAG ingestion complete and ready for AI Court agents.\n")

    return total_in_store


def main():
    parser = argparse.ArgumentParser(
        description="Ingest legal corpus documents into ChromaDB for AI Court of India."
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Path to legal corpus directory (default: from config).",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear existing collection before ingesting.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.embedding_batch_size,
        help="Batch size for embedding generation.",
    )

    args = parser.parse_args()
    run_ingestion(
        corpus_dir=args.corpus_dir,
        rebuild=args.rebuild,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
