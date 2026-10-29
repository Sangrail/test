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

Mostly done. [`indexing/detect.py`](../../engineering_search/indexing/detect.py): `ContentDetector` treats the extension as a hint and checks the first 512 bytes. A PDF header gives the PDF version, a ZIP with `xl/workbook.xml` is XLSX, and a JT file's 80-character header gives its version (for example JT 10.0). Content that contradicts the extension is `FORMAT_MISMATCH` and is not given to a reader. [`readers/registry.py`](../../engineering_search/indexing/readers/registry.py): `ReaderRegistry` holds several readers for each type, each with a manifest (name, version, formats, format versions, dependencies, capabilities). It picks the first installed reader that supports the format version, and tells `NO_READER`, `UNSUPPORTED_VERSION` and `DEPENDENCY_MISSING` apart. The detector and the registry are injected into `Indexer`. The reader and its version are stored for each file, and a new reader version re-extracts the file. Tests: `tests/test_coverage.py`, `tests/test_indexer.py`.

Not done: detection for formats without a signature (Markdown and CSV are named by extension), and any JT or CATIA reader. The JT probe reads the version string only. CAD stays out of scope ([ADR 0001](0001-mvp-format-scope.md)).
