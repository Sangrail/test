# Scope (S)

<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

What the MVP includes and excludes.

| ID | Constraint | Standing |
| --- | --- | --- |
| [S1](#s1) | An MVP, not the final platform | met |
| [S2](#s2) | Markdown and simple PDF, no OCR, no CAD | met |
| [S3](#s3) | Synthetic or public test documents | met |
| [S4](#s4) | The 29 October design inputs | met |

<a id="s1"></a>

## S1. An MVP, not the final platform

> The initial scope is an MVP, not the final platform or solution.

**Source:** [The brief](../../docs/Starting_document.md), scope.

**Standing:** *met*. Met by the MVP, on the test data.

**What it means for the design:** Take shortcuts where they do not hide a risk, and write each one down. Prove the path from question to cited answer before building the platform.

**Where the MVP stands:** Built in about four to five hours. The shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md#mvp-shortcuts-in-the-code) and the production gaps in [production.md](production.md).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

<a id="s2"></a>

## S2. Markdown and simple PDF, no OCR, no CAD

> The first formats for the stand-in readers are Markdown and PDF with a text layer. No OCR. No DXF, DWG, JT or CATIA.

**Source:** A decision during the MVP. Set at the start; extended by [S4](scope.md#s4).

**Standing:** *met*. Met by the MVP, on the test data.

**What it means for the design:** A small format set is enough to prove the chain. Reading more formats is the connectors' job ([C3](environment.md#c3)). Every other file is reported, not hidden.

**Where the MVP stands:** Met, and extended by [S4](scope.md#s4) with CSV and XLSX. CAD stays out of scope.

**Enforced by:** [`tests/test_indexer.py`](../../tests/test_indexer.py).

**Delivered by:** [`engineering_search/indexing/readers`](../../engineering_search/indexing/readers).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain (cited)

<a id="s3"></a>

## S3. Synthetic or public test documents

> The repository will be published, so the test documents must be synthetic or publicly shareable.

**Source:** A decision during the MVP.

**Standing:** *met*. Met by the MVP, on the test data.

**What it means for the design:** No real engineering documents. Scores on the test data are therefore optimistic.

**Where the MVP stands:** Synthetic Markdown, PDF, CSV and XLSX files, and two public FHWA PDFs.

**Delivered by:** [`test-repository`](../../test-repository).

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (cited)
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository

<a id="s4"></a>

## S4. The 29 October design inputs

> Add CSV and XLSX, detection of the file type from content, a coverage report, and SQL written by the MCP client over tables. CAD content stays out of scope.

**Source:** [The 29 October design inputs](../../docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md). With the [design notes](../../docs/engineering_knowledge_search_design_notes.html); dated inputs, not edited.

**Standing:** *met*. Met by the MVP, on the test data.

**What it means for the design:** The MCP client's language model plans structured questions; the server constrains and runs them. No second language model on the server.

**Where the MVP stands:** Built: CSV and XLSX readers, content detection, reader registry, coverage report, constrained SQL and the structured MCP tools.

**Enforced by:** [`tests/test_facts.py`](../../tests/test_facts.py).

**Delivered by:** [`engineering_search/indexing/detect.py`](../../engineering_search/indexing/detect.py), [`engineering_search/indexing/facts.py`](../../engineering_search/indexing/facts.py).

**Decisions:**

- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0021](../adr/0021-design-records-in-one-database.md): Keep the brief, the constraints and the decision records in one SQLite database, and generate their pages from it (cited)
