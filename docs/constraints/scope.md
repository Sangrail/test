# Scope (S)

What the MVP includes and excludes.

| ID | Constraint |
| --- | --- |
| [S1](#s1) | An MVP, not the final platform |
| [S2](#s2) | Markdown and simple PDF, no OCR, no CAD |
| [S3](#s3) | Synthetic or public test documents |
| [S4](#s4) | The 29 October design inputs |

<a id="s1"></a>

## S1. An MVP, not the final platform

> The initial scope is an MVP, not the final platform or solution.

**Source:** Brief, scope.

**What it means for the design:** Take shortcuts where they do not hide a risk, and write each one down. Prove the path from question to cited answer before building the platform.

**Where the MVP stands:** Built in about four to five hours. The shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md#mvp-shortcuts-in-the-code) and the production gaps in [production.md](production.md).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale

<a id="s2"></a>

## S2. Markdown and simple PDF, no OCR, no CAD

> The first formats are Markdown and PDF with a text layer. No OCR. No DXF, DWG, JT or CATIA.

**Source:** Initial MVP scope, set at the start. Extended by [S4](#s4).

**What it means for the design:** A small, honest format set, with every other file reported, not hidden.

**Where the MVP stands:** Met, and extended by S4 with CSV and XLSX. CAD stays out of scope.

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF

<a id="s3"></a>

## S3. Synthetic or public test documents

> The repository will be published, so the test documents must be synthetic or publicly shareable.

**Source:** Added at the start of the MVP.

**What it means for the design:** No real engineering documents. Scores on the test data are therefore optimistic.

**Where the MVP stands:** Synthetic Markdown, PDF, CSV and XLSX files, and two public FHWA PDFs.

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (cited)
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository

<a id="s4"></a>

## S4. The 29 October design inputs

> Add CSV and XLSX, detection of the file type from content, a coverage report, and SQL written by the MCP client over tables. CAD content stays out of scope.This is done for my own edification, just to prove out data flows. Though I said I'd start with Markdown and simple PDF. These are done because they give me obvious structured data. 

**Source:** [Handoff](../CODEX_ENGINEERING_SEARCH_HANDOFF.md) and [design notes](../engineering_knowledge_search_design_notes.html), 29 October 2026 (dated inputs; not edited).

**What it means for the design:** The MCP client's language model plans structured questions; the server constrains and runs them. No second language model on the server.

**Where the MVP stands:** Built: CSV and XLSX readers, content detection, reader registry, coverage report, constrained SQL and the structured MCP tools.

**Decisions:**

- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
