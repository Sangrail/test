---
status: accepted
date: 2026-10-28
---
# Store extracted passages with their source version

**Serves:** U3 (under 10 seconds), U4 (100% confidence in the source), U5 (no need to open the file).

## Context

To answer in under 10 seconds (U3) across many documents, search cannot open every file for each question. To give 100% confidence in the source (U4), each answer must point to an exact, fixed version of the file. The user must not need to open the file to check it (U5).

## Decision

- Extract each file once, and store its passages with the file, the location (lines, and the page for a PDF) and the SHA-256 of the file content.
- Search reads only the stored passages.
- Apply a change to a document as one transaction. A failed update must not leave part of a document in the index.
- Keep three versions separate: the source version (content hash), the format version, and the reader version ([ADR 0003](0003-versioned-reader-selection.md)). A new reader can change the passages of a file whose hash did not change.
- Deleted files leave the index. Permissions apply to all stored passages, every time ([ADR 0006](0006-permissions-before-results.md)).

## Consequences

- Each answer has a file, page, line range and SHA-256 version. A test can check it against the file itself.
- The index survives a restart. A restart reads and hashes every file, and extracts only new and changed files.
- Until the reader version is recorded, a reader change cannot be traced in the stored passages.

## Implementation

Done. [`store.py`](../../engineering_search/store.py): `SQLiteSearchIndex` keeps `documents` (file and SHA-256), `passages` (text, heading, lines, page), the FTS5 index, `files` (type, format version, reader and reader version, status, warnings) and, for tables, `source_tables`, `table_rows` and `facts` ([ADR 0016](0016-structured-facts-and-client-written-sql.md)), in `index-<id>.sqlite3` ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)). `apply` and `upsert` write a document, its tables, facts and file record in one transaction. A new reader version re-extracts the file. Tests: `tests/test_index.py` (persistence and one transaction), `tests/test_coverage.py` (statuses survive a restart), `tests/test_use_case.py` (each answer checked against the file).
