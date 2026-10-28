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

Partial. `SearchService.reindex` in [`service.py`](../../engineering_search/service.py) skips a file that cannot be extracted, logs it and returns it in `failed_files`. The other files are indexed. There is no stored coverage report, and files that are not `.md` or `.pdf` are not listed. Tests: `tests/test_startup.py` (invalid UTF-8).

Two parts of the decision are not met:

- "One bad file must not stop the index build." The first read of each file is outside the per-file error handler. A file read error (for example, `PermissionError`) stops the whole refresh with status 503.
- "No text" as an outcome. A PDF without a text layer is indexed with zero passages, and is not reported. The index status can show `up_to_date`.
