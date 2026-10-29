# Constraints from the brief (C)

The environment that the brief says already exists. The MVP must fit it, not replace it. Quoted or closely paraphrased from [the brief](../Starting_document.md).

| ID | Constraint |
| --- | --- |
| [C1](#c1) | A broader architecture direction already exists |
| [C2](#c2) | The files live in an existing repository |
| [C3](#c3) | Connectors extract metadata, text and properties |
| [C4](#c4) | Structured and/or semantic stores |
| [C5](#c5) | A chat-agent shell calls backend APIs or tools |

<a id="c1"></a>

## C1. A broader architecture direction already exists

> A broader architecture direction already exists.

**Source:** Brief, constraints.

**What it means for the design:** This component must be a backend that other parts can call, not a separate product with its own front end only.

**Where the MVP stands:** One search service behind both the web app and the MCP server. The wider architecture is not known in detail.

**Decisions:**

- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent

<a id="c2"></a>

## C2. The files live in an existing repository

> The files live in an existing repository.

**Source:** Brief, constraints.

**What it means for the design:** The system does not own the files. A real repository holds years of files in many formats and versions, with its own permissions. The format boundary must stay open for later readers.

**Where the MVP stands:** A local folder stands in for the repository. Files are read in place and never changed. Permissions are a Python dictionary, not the repository's own.

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (cited)
- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data
- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it
- [ADR 0005](../adr/0005-coverage-and-reader-gaps.md): Report the files that cannot be read
- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules

<a id="c3"></a>

## C3. Connectors extract metadata, text and properties

> Connectors and APIs can extract metadata, text and properties from supported files.

**Source:** Brief, constraints.

**What it means for the design:** Only *supported* files can be read, so the system must know which files are supported, which are not, and why.

**Where the MVP stands:** The MVP has its own readers (Markdown, PDF text layer, CSV, XLSX) and reports every file it cannot read. No connector is used yet.

**Decisions:**

- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it
- [ADR 0005](../adr/0005-coverage-and-reader-gaps.md): Report the files that cannot be read
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL

<a id="c4"></a>

## C4. Structured and/or semantic stores

> Extracted information can be stored in structured and/or semantic stores.

**Source:** Brief, constraints.

**What it means for the design:** The stores should be chosen from the questions and the data, and both kinds may be needed.

**Where the MVP stands:** A keyword index (FTS5) for text, and tables and typed facts for structured questions. No semantic (embedding) store: it is deferred until the questions show a gain.

**Decisions:**

- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL

<a id="c5"></a>

## C5. A chat-agent shell calls backend APIs or tools

> A chat-agent shell can call backend APIs or tools to expose a conversational plane for users.

**Source:** Brief, constraints.

**What it means for the design:** The service exposes tools that a chat agent can call. The agent's language model is part of the system and must be measured.

**Where the MVP stands:** An MCP server over local stdio, used from Claude Code, Codex and Pi. The agent writes the SQL for table questions.

**Decisions:**

- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale
