---
status: accepted
date: 2026-10-28
---
# Select a tested reader for each format and version, and record it

**Serves:** C2 (years of files in an existing repository), C3 (connectors extract from supported files), U4 (100% confidence in the source).

## Context

The repository holds years of files (C2). One format can have many versions, and an old version can need a different reader. The brief says that connectors and APIs extract from *supported* files (C3), so the system must know which files are supported. To have confidence in the source (U4), the system must also know how each file was read: a new reader can read the same file differently.

## Decision

- Detect the format and version of each file from its content. The file extension and the file date are hints only.
- A registry maps each format and version to a tested reader, with its exact version, its capabilities and the test files that prove it.
- The selection is deterministic. A missing runtime, a missing licence, an unsupported version or an unclear result gives an explicit outcome, never a silent fallback to another reader.
- For each source version, record the detected format and version, the selected reader and its version, and the result of the extraction.
- Never change a reader silently. A new reader gives a new extraction revision, after tests.

## Consequences

- A file that no reader can read becomes visible work, not a hidden gap ([ADR 0005](0005-coverage-and-reader-gaps.md)).
- The repository profile decides which readers come first ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). A viewer that reads the same formats is selected at the same time.
- Normal search reads stored passages and does not open the file again ([ADR 0004](0004-persistent-evidence.md)).

## Implementation

Planned. Today `extract` in [`core.py`](../../engineering_search/core.py) selects the reader by extension: `.md` or `.pdf` (pypdf). There is no format probe, no registry and no record of the reader version. No JT or CATIA SDK has been selected. CAD stays out of scope ([ADR 0001](0001-mvp-format-scope.md)).
