---
status: accepted, amended by 0020 (the readers are stand-ins for connectors)
date: 2026-10-28
version: 2
---

# Report the files that cannot be read

> **Amended** by [ADR 0020](0020-assume-the-environment-and-stand-in-for-it.md): the readers are stand-ins for the connectors that the brief says exist ([C3](../constraints/environment.md#c3)), written to prove the chain, not extraction to be built.

**Serves:** [C2](../constraints/environment.md#c2) (years of files in an existing repository), [C3](../constraints/environment.md#c3) (supported files only), [U4](../constraints/use-case.md#u4) (100% confidence in the source).

## Context

If a search finds nothing, the user must not think that no document states the value when the true reason is that a file could not be read. That would break confidence in the answer ([U4](../constraints/use-case.md#u4)). The repository holds years of files ([C2](../constraints/environment.md#c2)), and connectors read only supported files ([C3](../constraints/environment.md#c3)), so some files will not be readable. A 20-year-old drawing is a question of compatibility. Its age does not prove that it is supported or obsolete.

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

Done. [`indexing/status.py`](../../engineering_search/indexing/status.py) names one status for each file: classification (`CLASSIFIED`, `UNSUPPORTED_FORMAT`, `NO_READER`, `UNSUPPORTED_VERSION`, `DEPENDENCY_MISSING`, `FORMAT_MISMATCH`, `INVALID_HEADER`, `READ_ERROR`) and reading (`INDEXED_FULL`, `INDEXED_PARTIAL`, `NO_TEXT_LAYER`, `NO_EXTRACTABLE_CONTENT`, `MALFORMED`, `ENCRYPTED`, `READER_CRASH`), each with a hint. A PDF without a text layer is `NO_TEXT_LAYER`, not indexed. The inventory is stored in the index (`files` table) with the format version, the reader and the warnings, and survives a restart. [`indexing/coverage.py`](../../engineering_search/indexing/coverage.py) builds the report by type, format version, status, folder and capability. The index team gets it at `GET /index/coverage` and through the MCP tool `get_index_coverage`. Other users do not, because the report names files. Tests: `tests/test_coverage.py`, `tests/test_indexer.py`, `tests/test_startup.py`.

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 2 | 2026-10-29 | now | Amended by ADR 0020: the readers are stand-ins for connectors. | sangrail |
| 1 | 2026-10-28 | 2026-10-29 (Displaced by version 2) | Recorded when the decision was made. | sangrail |

- Amended by [ADR 0020](0020-assume-the-environment-and-stand-in-for-it.md).
