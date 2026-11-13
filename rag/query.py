"""
CLI query tool for Indian Legal RAG.
Allows interactive or command-line testing of legal provisions retrieval.

Usage:
    python -m rag.query "What law applies to possession of stolen property?"
    python -m rag.query "What provisions govern electronic evidence?" --top-k 3
"""

from __future__ import annotations

import argparse
import json
import sys

# Ensure UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeErrors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rag.config import config
from rag.retriever import LegalRetriever


def query_corpus(
    query_text: str,
    top_k: int = 5,
    act_filter: str | None = None,
    output_json: bool = False,
) -> None:
    """Execute a legal query and format results for display."""
    retriever = LegalRetriever(top_k=top_k)

    results = retriever.retrieve(
        query=query_text,
        top_k=top_k,
        act_filter=act_filter,
    )

    if output_json:
        dicts = [r.to_dict() for r in results]
        print(json.dumps(dicts, indent=2))
        return

    print("\n" + "=" * 75)
    print("AI COURT OF INDIA - LEGAL RETRIEVAL")
    print("=" * 75)
    print(f"Query:      '{query_text}'")
    print(f"Top K:      {top_k}")
    if act_filter:
        print(f"Act Filter: {act_filter}")
    print(f"Results:    {len(results)} found")
    print("=" * 75)

    if not results:
        print("\nNo matching legal provisions found.")
        return

    for i, res in enumerate(results, start=1):
        print(f"\n[RESULT {i}] - Similarity Score: {res.score:.4f} (Distance: {res.distance:.4f})")
        print(f"Citation:    {res.citation()}")
        print(f"Act:         {res.act_name}")
        print(f"Provision:   {res.section or res.article or 'N/A'}")
        if res.title and res.title != (res.section or res.article):
            print(f"Title:       {res.title}")
        if res.chapter:
            print(f"Chapter:     {res.chapter}")
        if res.part:
            print(f"Part:        {res.part}")
        print(f"Page:        {res.page}")
        print(f"Chunk ID:    {res.chunk_id}")
        print("-" * 75)
        print("Text Excerpt:")
        lines = res.text.splitlines()
        preview = "\n".join(lines[:10])
        if len(lines) > 10:
            preview += f"\n... [{len(lines) - 10} more lines]"
        print(preview)
        print("-" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Query the Indian Legal Corpus RAG system."
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        help="Legal query string (e.g. 'possession of stolen property').",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.retrieval_top_k,
        help="Number of legal results to retrieve.",
    )
    parser.add_argument(
        "--act",
        type=str,
        default=None,
        help="Filter results by statute short name (e.g. BNS, BSA, IT_Act, Constitution).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON array of results.",
    )

    args = parser.parse_args()

    if not args.query:
        print("Please provide a query string. Example:")
        print("  python -m rag.query \"What law applies to possession of stolen property?\"")
        sys.exit(1)

    query_corpus(
        query_text=args.query,
        top_k=args.top_k,
        act_filter=args.act,
        output_json=args.json,
    )


if __name__ == "__main__":
    main()
