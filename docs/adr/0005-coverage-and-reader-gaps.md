---
status: accepted
date: 2026-10-28
---
# Report the files that cannot be read

**Serves:** C2 (years of files in an existing repository), C3 (supported files only), U4 (100% confidence in the source).

## Context

If a search finds nothing, the user must not think that no document states the value when the true reason is that a file could not be read. That would break confidence in the answer (U4). The repository holds years of files (C2), and connectors read only supported files (C3), so some files will not be readable. A 20-year-old drawing is a question of compatibility. Its age does not prove that it is supported or obsolete.

## Decision

- Keep an inventory of all discovered files, with a clear outcome for each: out of scope, unsupported format, unknown version, reader not available, encrypted, damaged, extraction failed, partly extracted, no text, or indexed.
- Discovery and eligibility are separate. List an out-of-scope CAD file without reading it.
- One bad file must not stop the index build.
- Group the report by format, version and reason, with counts, for the index team. Never show an unreadable file as a search result with zero matches. Never show its name to a user who cannot read it ([ADR 0006](0006-permissions-before-results.md)).
- Coverage figures must keep unreadable and unsupported files in the total.

## Consequences

- The team can see which reader to build or buy next, and test it on real old files.
- An unsupported version needs a new reader, not endless retries.

## Implementation

Partial. The [`Indexer`](../../engineering_search/indexing/indexer.py) lists every file with its type and one outcome: `indexable`, `unsupported` (no reader; listed without being read) or `unreadable`. A file that cannot be read or extracted is logged, returned in `failed_files`, and the other files are indexed. `/index/status` shows the types and outcomes of the last scan for the index team. Tests: `tests/test_indexer.py`, `tests/test_startup.py`, `tests/test_search.py`.

Not met yet:

- The inventory is in memory, not a stored report, and it is not grouped by format version.
- The outcomes are fewer than the decision lists. There is no "encrypted", "damaged" or "unknown version", and no "no text": a PDF without a text layer is indexed with zero passages and is not reported. The index status can show `up_to_date`.
