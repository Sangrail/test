---
status: accepted
date: 2026-10-29
---
<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

# Read tables into typed facts at index time, and let the MCP client write constrained SQL

Supersedes in part [ADR 0014](0014-defer-facts-store-and-embeddings.md): the facts store is no longer deferred for tables. Embeddings stay deferred. Extends the formats of [ADR 0001](0001-mvp-format-scope.md) with CSV and XLSX.

**Serves:** [U1](../constraints/use-case.md#u1) (load limit, material or approval status), [U2](../constraints/use-case.md#u2) (100+ documents), [U4](../constraints/use-case.md#u4) (100% confidence in the source), [U6](../constraints/use-case.md#u6) (no query languages for the user), [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [R3](../constraints/requirements.md#r3) (lists by value), [C3](../constraints/environment.md#c3) (connectors extract properties), [C4](../constraints/environment.md#c4) (structured and/or semantic stores), [C5](../constraints/environment.md#c5) (a chat-agent shell calls tools), [S4](../constraints/scope.md#s4) (the 29 October design inputs).

## Context

The text path ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)) answers one value from prose well enough. It answers filter questions badly: "Which S355 components have an allowable load under 5 kN/m²?" needs every matching row, a numeric comparison in one unit, and the difference between what a component can carry (a capacity) and what it must carry (a demand). Word search sees only the passages that it ranks, so the list is not complete, and a number near a keyword can belong to a different element.

Much of the data that leads ask about is already structured: component schedules and registers in CSV and Excel, and tables in Markdown and PDF. The 29 October design inputs ([handoff](../CODEX_ENGINEERING_SEARCH_HANDOFF.md), [design notes](../engineering_knowledge_search_design_notes.html)) ask for these tables to keep their row identity and source location, and for the MCP client's LLM to plan structured questions. They rule out a second LLM on the server.

The premise is that the indexer is designed from the questions and the data: to build it, you need an idea of the questions; to answer them, you need to know what data you have and what you can extract from it. That gives two kinds of extracted data, unstructured (passages) and structured (tables and facts), and a way in for each.

Who writes the structured query has three options:

1. **The service plans it from the plain-language question.** No LLM, but a rule-based planner for joins and filters is a query language in disguise, and it is brittle.
2. **A server-side LLM writes SQL.** Needs an API key and a provider on the server, and sends questions to it. The design inputs rule it out.
3. **The chat agent that already reads the question writes SQL, and the server constrains it.** The LLM is already in the loop ([C5](../constraints/environment.md#c5)). The user still asks in plain language ([U6](../constraints/use-case.md#u6)). The server owns safety and permissions.

## Decision

- **Extract tables and typed facts at index time.** Readers return tables with the source line, page or sheet of each row: Markdown pipe tables, CSV files and XLSX sheets. Fixed rules (`indexing/facts.py`) read the column header, the table name and the cell, and give each cell a parameter, a role (capacity, demand, specification, status, measurement, unknown), the value as written, a number, a unit and an SI value. Facts come only from table cells, never from free text. Capacity and demand are never the same parameter.
- **Publish a small, documented schema** to the client: `documents`, `facts`, `components` (a view with the common parameters as columns), `table_rows` and `source_tables`. `describe_schema`, `list_tables` and `describe_table` describe it. The schema holds no document data.
- **The MCP client's LLM writes the SQL.** `query_sql` runs one statement. The service does not plan structured questions itself, and the web search bar does not claim to.
- **Constrain the SQL on the server, for each request:**
  - Build an in-memory SQLite projection with only the rows from files the user may read, and every dependent row. Forbidden data is absent, not filtered, so counts, joins and `NOT EXISTS` cannot reveal it. The base index is never exposed to SQL.
  - Accept one `SELECT` or `WITH` statement, at most 4000 characters.
  - Run it with `PRAGMA query_only`, an authoriser that allows reads of the published tables only and a short function allowlist, a budget of 2,000,000 SQLite steps, and at most 500 rows.
  - Audit the SHA-256 and length of the statement, the files in scope and excluded, the row count and the cited files, not the rows.
- **Every row can be cited.** Rows carry `file_id`, `table_no`, `row_no`, `line` and `page`. `get_document_evidence` returns the row's cells, its facts, the file's SHA-256 version and the verbatim line.
- **Keep the text path.** `search_evidence` and `read_evidence` are unchanged. The server instructions tell the agent to choose: SQL for filters, joins and counts over tables; text search for values in prose.

## Consequences

- "S355 components under 5 kN/m²" returns every matching row from the files the user may read, with citations: 7 rows for JP, 6 for Kamal. Verified with Claude Code, Codex and Pi ([docs/MCP.md](../MCP.md#what-was-verified)).
- The server makes the SQL safe; it does not make it right. The LLM can write a valid query for the wrong thing. The column names (`allowable_load_kn_m2`, `imposed_load_kn_m2`) and the instructions guide it, and the tool call shows the SQL to the tester.
- A value stated only in prose is not a fact. SQL does not find it; text search does.
- The rules know a small set of parameters and units. A new kind of column becomes a fact with role `unknown` until a rule is added.
- The web page has no structured path. `POST /sql` exists in the HTTP API for a future client-planned flow.
- Building a projection per request is simple and safe, and costs time in proportion to the permitted data. It does not scale to a large repository; a policy-enforced view over the base index is the later design ([design/SCALING.md](../../design/SCALING.md)).
- The safety rests on SQLite's authoriser and `query_only`, not on a SQL parser. The bypass tests in `tests/test_sql.py` are the check. The MCP tool does not take bound parameters yet.

## Implementation

Done for CSV, XLSX and Markdown tables. Readers: [`readers/csv.py`](../../engineering_search/indexing/readers/csv.py), [`readers/xlsx.py`](../../engineering_search/indexing/readers/xlsx.py) (`openpyxl`; a formula with no cached value is left empty and the file is `INDEXED_PARTIAL`), [`readers/markdown.py`](../../engineering_search/indexing/readers/markdown.py). Facts: [`indexing/facts.py`](../../engineering_search/indexing/facts.py), units in [`units.py`](../../engineering_search/units.py). Store: `source_tables`, `table_rows` and `facts` in [`store.py`](../../engineering_search/store.py). Projection and safety: [`sql.py`](../../engineering_search/sql.py). Service: `query_sql`, `sql_schema`, `table_row_evidence` in [`service.py`](../../engineering_search/service.py). HTTP: `POST /sql`, `GET /sql/schema`, `GET /evidence/{file_id}/tables/{n}/rows/{n}`. MCP tools in [`mcp_server.py`](../../engineering_search/mcp_server.py).

Tests: `tests/test_facts.py` (the rules), `tests/test_sql.py` (expected rows by hand from the fixtures, permissions, refused statements, audit, citations, the example queries in docs/MCP.md), `tests/test_mcp_stdio.py` (a real MCP client over stdio), `tests/test_no_leaks.py` (CSV and XLSX files included). Not done: tables in PDF files, facts from prose, bound parameters in `query_sql`.
