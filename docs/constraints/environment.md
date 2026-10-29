# Constraints from the brief (C)

<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

The environment that [the brief](../Starting_document.md) says **already exists**. The MVP does not design or build any of it. Where the MVP needs one of these to run end to end, it uses the simplest stand-in that proves the chain from question to cited answer, and names it as a stand-in. For example, connectors already extract metadata, text and properties from supported files ([C3](environment.md#c3)), so the MVP's PDF, Markdown, CSV and XLSX readers are placeholders for them, not a proposal to build extraction ([ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md)).

| ID | Constraint | Standing |
| --- | --- | --- |
| [C1](#c1) | A broader architecture direction already exists | assumed |
| [C2](#c2) | The files live in an existing repository | assumed |
| [C3](#c3) | Connectors extract metadata, text and properties | assumed |
| [C4](#c4) | Structured and/or semantic stores | assumed |
| [C5](#c5) | A chat-agent shell calls backend APIs or tools | assumed |

<a id="c1"></a>

## C1. A broader architecture direction already exists

> A broader architecture direction already exists.

**Source:** [The brief](../../docs/Starting_document.md), constraints.

**Standing:** *assumed*. The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.

**What it means for the design:** This component is a backend that other parts of that architecture call, not a separate product.

**Where the MVP stands:** One search service behind an HTTP API, a web page and an MCP server stands in for this component's place in that architecture. The wider architecture is not known in detail.

**Stand-in in the MVP:** [`engineering_search/app.py`](../../engineering_search/app.py), [`engineering_search/mcp_server.py`](../../engineering_search/mcp_server.py), [`engineering_search/service.py`](../../engineering_search/service.py).

**Decisions:**

- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

<a id="c2"></a>

## C2. The files live in an existing repository

> The files live in an existing repository.

**Source:** [The brief](../../docs/Starting_document.md), constraints.

**Standing:** *assumed*. The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.

**What it means for the design:** The system does not own the files. A real repository holds years of files in many formats and versions, with its own permissions. The service reads what is there and never changes it.

**Where the MVP stands:** A local folder of test files stands in for the repository, and folder rules in `access.py` stand in for its permissions. Files are read in place and never changed. Real permissions are [P3](production.md#p3).

**Stand-in in the MVP:** [`engineering_search/access.py`](../../engineering_search/access.py), [`test-repository`](../../test-repository).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (cited)
- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it
- [ADR 0005](../adr/0005-coverage-and-reader-gaps.md): Report the files that cannot be read
- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

<a id="c3"></a>

## C3. Connectors extract metadata, text and properties

> Connectors and APIs can extract metadata, text and properties from supported files.

**Source:** [The brief](../../docs/Starting_document.md), constraints.

**Standing:** *assumed*. The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.

**What it means for the design:** The connectors exist and are not part of this work. The service consumes what they extract (text, tables and properties, with source locations and versions), and it must know which files were read, by which connector and version, and which were not.

**Where the MVP stands:** The MVP's readers for Markdown, PDF text layer, CSV and XLSX are placeholders for the connectors, written only to prove the chain from file to cited answer. They are not a proposal to build extraction. Each sits behind the reader interface (`ReaderManifest`, `Extraction`), which is where a connector adapter plugs in ([ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md)). Every file that no reader handles is reported.

**Stand-in in the MVP:** [`engineering_search/indexing/readers`](../../engineering_search/indexing/readers).

**Enforced by:** [`tests/test_indexer.py`](../../tests/test_indexer.py).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (cited)
- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it
- [ADR 0005](../adr/0005-coverage-and-reader-gaps.md): Report the files that cannot be read
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

<a id="c4"></a>

## C4. Structured and/or semantic stores

> Extracted information can be stored in structured and/or semantic stores.

**Source:** [The brief](../../docs/Starting_document.md), constraints.

**Standing:** *assumed*. The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.

**What it means for the design:** The stores should be chosen from the questions and the data, and both kinds may be needed.

**Where the MVP stands:** SQLite stands in for the stores: an FTS5 keyword index for passages, and tables and typed facts for structured questions. No semantic (embedding) store: it is deferred until the questions show a gain.

**Stand-in in the MVP:** [`engineering_search/sql.py`](../../engineering_search/sql.py), [`engineering_search/store.py`](../../engineering_search/store.py).

**Decisions:**

- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain

<a id="c5"></a>

## C5. A chat-agent shell calls backend APIs or tools

> A chat-agent shell can call backend APIs or tools to expose a conversational plane for users.

**Source:** [The brief](../../docs/Starting_document.md), constraints.

**Standing:** *assumed*. The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.

**What it means for the design:** The service exposes tools that a chat agent can call. The agent's language model is part of the system and must be measured.

**Where the MVP stands:** Claude Code, Codex and Pi over a local MCP server stand in for the company's chat-agent shell. The agent writes the SQL for table questions.

**Stand-in in the MVP:** [`engineering_search/mcp_server.py`](../../engineering_search/mcp_server.py).

**Enforced by:** [`tests/test_mcp_stdio.py`](../../tests/test_mcp_stdio.py).

**Decisions:**

- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale
- [ADR 0020](../adr/0020-assume-the-environment-and-stand-in-for-it.md): Assume the environment in the brief exists, and use stand-ins only to prove the chain
