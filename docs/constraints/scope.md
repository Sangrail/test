# Scope (S)


Scope is the arbiter of how far the MVP goes. The intent and the constraints may ask for more; scope says how far down that road this work goes. **Exceeding** scope is acceptable, and is recorded (a decision that goes beyond it links the scope item with *exceeds*). **Falling short** of scope is a failure to flag.

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [S1](#s1) | An MVP, not the final platform | scope | met | 1 |
| [S2](#s2) | Markdown and simple PDF, no OCR, no CAD | scope | met | 2 |
| [S3](#s3) | Synthetic or public test documents | scope | met | 1 |
| [S4](#s4) | The 29 October design inputs | scope | met | 1 |
| [S5](#s5) | Extraction is the connectors' job | scope | exceeded | 1 |
| [S6](#s6) | Not a distributed system | scope | met | 1 |

<a id="s1"></a>

## S1. An MVP, not the final platform

> The initial scope is an MVP, not the final platform or solution.

**Pillar:** scope. **Source:** [The brief](../../docs/Starting_document.md), scope.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Take shortcuts where they do not hide a risk, and write each one down. Prove the path from question to cited answer before building the platform.

**Where the MVP stands:** Built in about four to five hours. The shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md#mvp-shortcuts-in-the-code) and the production gaps in [production.md](production.md).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="s2"></a>

## S2. Markdown and simple PDF, no OCR, no CAD

> The first formats for the stand-in readers are Markdown and PDF with a text layer. No OCR. No DXF, DWG, JT or CATIA.

**Pillar:** scope. **Source:** A decision during the MVP. Set at the start; extended by [S4](scope.md#s4).

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** A small format set is enough to prove the chain. Reading more formats is the connectors' job ([C3](environment.md#c3)). Every other file is reported, not hidden.

**Where the MVP stands:** Met, and extended by [S4](scope.md#s4) with CSV and XLSX. CAD stays out of scope.

**Enforced by:** [`tests/test_indexer.py`](../../tests/test_indexer.py).

**Delivered by:** [`engineering_search/indexing/readers`](../../engineering_search/indexing/readers).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain (cited)

**History:**

- Version 2, from 2026-10-29, active. ADR 0020: the first formats are those of the stand-in readers; more formats are the connectors' job.
- Version 1, 2026-10-28 to 2026-10-29. First recorded with the use case and the constraints of the brief. It read: “The first formats are Markdown and PDF with a text layer. No OCR. No DXF, DWG, JT or CATIA.”

<a id="s3"></a>

## S3. Synthetic or public test documents

> The repository will be published, so the test documents must be synthetic or publicly shareable.

**Pillar:** scope. **Source:** A decision during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** No real engineering documents. Scores on the test data are therefore optimistic.

**Where the MVP stands:** Synthetic Markdown, PDF, CSV and XLSX files, and two public FHWA PDFs.

**Delivered by:** [`test-repository`](../../test-repository).

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (cited)
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="s4"></a>

## S4. The 29 October design inputs

> Add CSV and XLSX, detection of the file type from content, a coverage report, and SQL written by the MCP client over tables. CAD content stays out of scope.

**Pillar:** scope. **Source:** [The 29 October design inputs](../../docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md). With the [design notes](../../docs/engineering_knowledge_search_design_notes.html); dated inputs, not edited.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** The MCP client's language model plans structured questions; the server constrains and runs them. No second language model on the server.

**Where the MVP stands:** Built: CSV and XLSX readers, content detection, reader registry, coverage report, constrained SQL and the structured MCP tools.

**Enforced by:** [`tests/test_facts.py`](../../tests/test_facts.py).

**Delivered by:** [`engineering_search/indexing/detect.py`](../../engineering_search/indexing/detect.py), [`engineering_search/indexing/facts.py`](../../engineering_search/indexing/facts.py).

**Decisions:**

- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0021](../adr/0021-design-records-in-one-database.md): Keep intent, constraints, scope and decisions in one versioned SQLite database, the source of truth, and generate the documents from it (cited)

**History:**

- Version 1, from 2026-10-29, active. Recorded from the 29 October design inputs.

<a id="s5"></a>

## S5. Extraction is the connectors' job

> The MVP does not build extraction: connectors already extract metadata, text and properties ([C3](environment.md#c3)). Stand-ins may show the chain working.

**Pillar:** scope. **Source:** The product owner, during the MVP.

**Standing:** *exceeded*. The MVP goes beyond this scope item, knowingly. Acceptable, and recorded.

**What it means for the design:** Effort goes into what sits between the connectors and the answer. Readers beyond what the chain needs go past this scope.

**Where the MVP stands:** Exceeded, knowingly: the MVP has its own readers for Markdown, PDF text, CSV and XLSX, and its own rules that turn table cells into typed facts, to show the system partly working. They simulate connectors that are believed to exist (ADR 0020).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (goes beyond it)
- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it (goes beyond it)
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL (goes beyond it)

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: the readers go beyond the scope, because the brief says connectors exist.

<a id="s6"></a>

## S6. Not a distributed system

> The MVP is not a distributed system: one machine, one service process (and one MCP process per chat client).

**Pillar:** scope. **Source:** The product owner, during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Several users are served by one process within the time budget, or told to retry. Scaling out, replication and failover are beyond this scope even though the intent ([U3](use-case.md#u3)) and the constraints ([R6](requirements.md#r6)) point there; [P1](production.md#p1) records that.

**Where the MVP stands:** One process with admission control (ADR 0018). The work needed to serve the organisation is documented, not built.

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: scope says how far down the road the MVP goes, and it stops short of a distributed system.
