---
status: accepted
date: 2026-10-28
---
# Start with Markdown and simple text-layer PDF

**Serves:** S1 (MVP only), S2 (Markdown and simple PDF, no OCR, no CAD), U5 (no CAD file or PDF viewer).

## Context

The brief limits the MVP to Markdown and simple PDF (S2). It excludes OCR and the CAD formats DXF, DWG, JT and CATIA. The MVP must prove the full path from a question to an answer with an exact source (U4, U5) before the system takes on complex formats. A real repository holds many formats and versions (C2), so the format boundary must stay open for later readers ([ADR 0003](0003-versioned-reader-selection.md)).

## Decision

- Read UTF-8 Markdown and PDF files that have a text layer.
- "Simple PDF" means text that a library can extract, with the page number as its location. OCR, encrypted files, embedded drawings, complex table reconstruction and layout analysis are out of scope.
- Markdown passages keep line numbers. PDF passages keep the page number and the line numbers in the extracted page text.
- A location proves where the text came from. It does not prove that an engineering value is approved or correct.
- Semantic search, CAD geometry, the decision about which document is the authority, and production distribution are later work.

## Consequences

- The user sees the exact text and its file, page and lines, so the user does not need to open the PDF (U5).
- A PDF with some text does not mean that all its pages, tables or images are searchable. A scanned page gives no text.
- The 10-second target (U3) is measured on the test corpus only. It is not a promise for any file or any computer.

## Implementation

Done. The [indexing package](../../engineering_search/indexing/): `ExtensionDetector` names `.md` files `markdown` and `.pdf` files `pdf`. Only these two types have readers in `readers.py`. The Markdown reader splits by headings and blank lines. The PDF reader works page by page with pypdf (at most 15 lines in each passage). Files of other types are listed as unsupported and are not read. A file that cannot be read is skipped and reported ([ADR 0005](0005-coverage-and-reader-gaps.md)). Uploads accept Markdown only. Tests: `tests/test_indexer.py`, `tests/test_index.py`, `tests/test_use_case.py`.
