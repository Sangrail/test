# Constraints (C)

> A broader architecture direction already exists, the files live in an existing repository, Connector and APIs can extract metadata/text/properties from supported files, extracted information can be stored in structured and/or semantic stores, and a chat-agent shell can call backend APIs or tools to expose a conversational plane for users.

All five already exist in the company. The MVP does not build them. Where the flow needs one, the MVP has a minimal stand-in, labelled as a stand-in, so the use case can be proved end to end ([ADR 0001](../adr/0001-prove-the-use-case-with-stand-in-readers.md)). Stand-ins are not grown into products.

| ID | Item | Standing | Stand-in in the MVP |
| --- | --- | --- | --- |
| [C1](#c1) | A broader architecture direction already exists | assumed | none: the MVP sits behind tools and an HTTP API so it can fit |
| [C2](#c2) | The files live in an existing repository | assumed | [`test-repository/`](../../test-repository/), read in place |
| [C3](#c3) | Connectors and APIs extract metadata, text and properties from supported files | assumed | the sample readers in [`engineering_search/indexing/readers/`](../../engineering_search/indexing/readers/) |
| [C4](#c4) | Extracted information can be stored in structured and/or semantic stores | assumed | one SQLite file: tables, typed facts and a full-text index |
| [C5](#c5) | A chat-agent shell can call backend APIs or tools | assumed | the MCP server; the web search page is a test harness |

<a id="c1"></a>

## C1. A broader architecture direction already exists

> "A broader architecture direction already exists"

**For the design:** the MVP must not invent a platform. It is one service with a narrow interface (tools and HTTP), so the existing direction can place it.

**In the MVP:** no stand-in. [ADR 0005](../adr/0005-one-search-service-behind-tools.md) and [ADR 0010](../adr/0010-a-local-single-process.md).

<a id="c2"></a>

## C2. The files live in an existing repository

> "the files live in an existing repository"

**For the design:** the system reads the repository where it is. It does not take files in, copy them or own them. A source is the file on disc as it is now ([K3](clarifications.md#k3)); there are no revisions to manage.

**In the MVP:** `--documents` points at the repository; the indexer scans it, re-reads only new and changed files, and removes deleted ones ([ADR 0007](../adr/0007-the-source-is-the-file-on-disc.md)). There are no uploads ([K12](clarifications.md#k12)). The test repository stands in: [`test-repository/TEST-DATA.txt`](../../test-repository/TEST-DATA.txt).

<a id="c3"></a>

## C3. Connectors and APIs extract metadata, text and properties from supported files

> "Connector and APIs can extract metadata/text/properties from supported files"

**For the design:** extraction is solved elsewhere. The search must work from what connectors give it: text with a location, and properties as name–value pairs.

**In the MVP:** sample readers for Markdown, text-layer PDF, CSV, XLSX and DXF (notes and title-block attributes) stand in for the connectors, only to show the flow ([ADR 0001](../adr/0001-prove-the-use-case-with-stand-in-readers.md), [K7](clarifications.md#k7)). Files without a reader are listed with the reason in the coverage report. Registered in [`registry.py`](../../engineering_search/indexing/readers/registry.py); tested in [`tests/test_indexer.py`](../../tests/test_indexer.py), [`tests/test_dxf.py`](../../tests/test_dxf.py), [`tests/test_coverage.py`](../../tests/test_coverage.py).

<a id="c4"></a>

## C4. Extracted information can be stored in structured and/or semantic stores

> "extracted information can be stored in structured and/or semantic stores"

**For the design:** "and/or" leaves the choice open ([K8](clarifications.md#k8)). The MVP uses structured tables (typed facts) and a lexical full-text index. Semantic search is out of scope ([O1](gaps.md#o1)).

**In the MVP:** SQLite with FTS5 ([`store.py`](../../engineering_search/store.py)) and typed facts from tables ([`facts.py`](../../engineering_search/indexing/facts.py)). [ADR 0002](../adr/0002-structured-tables-and-full-text-search.md).

<a id="c5"></a>

## C5. A chat-agent shell can call backend APIs or tools

> "a chat-agent shell can call backend APIs or tools to expose a conversational plane for users"

**For the design:** the conversation belongs to the shell. The MVP provides the tools it calls and the rules for using them.

**In the MVP:** an MCP server over stdio ([`mcp_server.py`](../../engineering_search/mcp_server.py), [docs/MCP.md](../MCP.md)) with Claude Code, Codex or Pi as the shell. The web search page calls the same service and is a test harness, not a chat shell. [ADR 0005](../adr/0005-one-search-service-behind-tools.md); tested in [`tests/test_mcp_stdio.py`](../../tests/test_mcp_stdio.py).
