---
status: accepted
date: 2026-10-29
version: 1
---

# Assume the environment in the brief exists, and use stand-ins only to prove the chain

Amends [ADR 0001](0001-mvp-format-scope.md), [ADR 0003](0003-versioned-reader-selection.md) and [ADR 0005](0005-coverage-and-reader-gaps.md): their readers and their format scope describe stand-ins for the connectors, not extraction to be built.

**Serves:** [C1](../constraints/environment.md#c1) (an architecture direction exists), [C2](../constraints/environment.md#c2) (the files live in an existing repository), [C3](../constraints/environment.md#c3) (connectors extract metadata, text and properties), [C4](../constraints/environment.md#c4) (structured and/or semantic stores exist), [C5](../constraints/environment.md#c5) (a chat-agent shell exists), [S1](../constraints/scope.md#s1) (MVP only).

## Context

The brief states five things that already exist ([C1](../constraints/environment.md#c1) to [C5](../constraints/environment.md#c5)). In particular, connectors and APIs already extract metadata, text and properties from supported files ([C3](../constraints/environment.md#c3)).

The MVP still needs files to be read, stored and queried to run end to end, so it has its own readers for Markdown, PDF with a text layer, CSV and XLSX, its own SQLite stores, a local folder for a repository and local chat clients. Earlier records ([ADR 0001](0001-mvp-format-scope.md), [ADR 0003](0003-versioned-reader-selection.md), [ADR 0005](0005-coverage-and-reader-gaps.md)) describe the readers as if extraction were part of this work. Read that way, the MVP appears to ignore the constraint and to propose rebuilding what the company already has.

## Decision

- Treat [C1](../constraints/environment.md#c1) to [C5](../constraints/environment.md#c5) as given. The MVP does not design or build them.
- Where the MVP needs one of them to run, use the simplest stand-in that proves the chain from question to cited answer, and name it as a stand-in:

| In the brief | Stand-in in the MVP | In a real deployment |
| --- | --- | --- |
| [C1](../constraints/environment.md#c1) an architecture direction | One search service behind an HTTP API, a web page and an MCP server | The existing architecture calls the same service |
| [C2](../constraints/environment.md#c2) an existing repository | A local folder of test files, and folder rules for permissions | The repository, its versions and its permissions, through its connector |
| [C3](../constraints/environment.md#c3) connectors extract metadata, text and properties | Readers for Markdown, PDF text layer, CSV and XLSX | The existing connectors and APIs, each behind the reader interface |
| [C4](../constraints/environment.md#c4) structured and semantic stores | SQLite: an FTS5 index, tables and typed facts | The company's stores |
| [C5](../constraints/environment.md#c5) a chat-agent shell | Claude Code, Codex and Pi over a local MCP server | The company's chat-agent shell, over remote MCP or its tool API |

- The work that is the MVP's own is what sits between these: knowing the questions, what to take from tables and how to type it, permissions before limits, binding an answer to its subject, citations, constrained SQL, the time budget, and the tests and evaluation.
- The reader interface (`ReaderManifest`, `Extraction`) is where a connector plugs in: an adapter returns the same passages and tables, with source locations and a version.

## Consequences

- Better PDF or Markdown parsing is not MVP work. A gap in a stand-in reader is recorded, not fixed, unless it breaks the chain.
- The format scope of [ADR 0001](0001-mvp-format-scope.md) ([S2](../constraints/scope.md#s2)) is the scope of the stand-ins, not of the product.
- Reader selection and coverage ([ADR 0003](0003-versioned-reader-selection.md), [ADR 0005](0005-coverage-and-reader-gaps.md)) stay: the service must still know what read each file, in which version, and which files nothing could read. With real connectors they record the connector's name and version.
- The quality of real connector output (OCR, tables in PDF files, CAD properties) is unknown, and must be profiled on the real repository ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)).

## Implementation

Done in the documents: [docs/README.md](../README.md#what-is-assumed-and-what-stands-in-for-it), the constraint pages ([C1](../constraints/environment.md#c1) to [C5](../constraints/environment.md#c5) have the standing *assumed* and list their stand-ins), and the docstring of the reader package, [`engineering_search/indexing/readers/__init__.py`](../../engineering_search/indexing/readers/__init__.py). No behaviour changed.

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-29 | now | Recorded when the decision was made. | sangrail |
