# Case Packet Directory

This directory is designated for `Case_Packet.pdf` files prepared externally for the AI Court of India.

## Security & Data Isolation Rule
1. `Case_Packet.pdf` contains relevant case facts, parties, charges, witnesses, exhibits, and arguments without the court's final verdict.
2. `Ground_Truth_Verdict.pdf` contains the actual court judgment and reasoning.
   - **DO NOT** place `Ground_Truth_Verdict.pdf` into this directory or into `data/legal_corpus/`.
   - **DO NOT** ingest `Ground_Truth_Verdict.pdf` into ChromaDB.
   - The RAG system is strictly prohibited from indexing any files in `data/cases/`.
