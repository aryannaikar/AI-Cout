# Legal document source handling

`original/` contains the supplied full Act PDFs copied from Downloads. Preserve the source files. Their publication/amendment cutoffs have not yet been independently verified.

`condensed/` contains supplementary navigation guides only. They are not authoritative law and are deliberately outside `legal_corpus/`, so normal ingestion will not index them. The condensed IPC guide references the Shabuddin benchmark; it is kept under `condensed/benchmark-isolated/` and must not enter live legal retrieval.

## Recommended ingestion for the original Acts

1. Verify each source against an official Gazette/India Code publication and record source URL, Act identifier, publication date, amendment cutoff, commencement/effective dates, and SHA-256 checksum.
2. Extract PDF text page-wise while retaining page numbers; manually inspect headings, tables, provisos, explanations, illustrations, and OCR quality against rendered pages.
3. Parse complete sections and subsections into deterministic section-aware chunks. Keep full parent-section text available when sub-chunks are retrieved.
4. Add explicit metadata: `short_name`, `act_name`, `act_year`, `legal_regime`, `version_label`, `effective_from`, `effective_to`, `source_file`, `source_page_start`, `source_page_end`, `source_url`, `source_reliability`, and `is_complete_text`.
5. Use stable IDs derived from Act/version/section/subsection/source checksum and Chroma `upsert` for incremental idempotence. Never use rebuild mode for this addition.
6. Retrieve substantive provisions only from verified full-text sources. Treat charge records as allegations and condensed guides as navigation hints, never as statutory text. If complete text/version cannot be verified, explicitly report the limitation.

Current pipeline entry points are `rag/loader.py`, `rag/chunker.py`, `rag/ingest.py`, `rag/vector_store.py`, and `rag/retriever.py`. The loader's current legal corpus map and chunk metadata do not yet encode version/effective-date/completeness/source-reliability for historical Act versions; add those fields before ingesting the original files.
