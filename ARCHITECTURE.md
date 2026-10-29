# Architecture

This document describes the code as it runs now. [design/SYSTEM-DESIGN.md](design/SYSTEM-DESIGN.md) describes the wider design and the phases. [design/EXTRACTION.md](design/EXTRACTION.md) describes how extraction and the stores must grow.

## Overview

![Code architecture](design/code-architecture.png)

Source: [design/code-architecture.svg](design/code-architecture.svg), made by [design/make_architecture.py](design/make_architecture.py). Change the script when a module or an import changes. [design/system-design.png](design/system-design.png) shows the wider system and the phases.

The diagram shows the modules by layer. Every import points down the page. There are two kinds of process: the web server (`python -m engineering_search`) and the MCP server, which each chat client starts. Each process has its own `SearchService`. They share the SQLite files in the state folder, and a lock file that lets one process at a time change the index. Each process admits a search, read or SQL query only if it can answer it within the time budget ([Time budget and admission](#time-budget-and-admission)).

## Two ways to answer

The service answers a question in one of two ways. Both use the same index, permissions and audit log.

| | Unstructured (text) | Structured (tables and facts) |
| --- | --- | --- |
| Example | "What is the roof load limit at Northgate?" | "Which S355 components have an allowable load under 5 kN/m²?" |
| Extracted at index time | Passages: headings, sentences and table rows, with line numbers | Tables, their rows, and typed facts from the cells, with line numbers |
| Who forms the query | The service: stop words, synonyms, prefix terms, a number comparison | The MCP client (Claude Code, Codex, Pi) writes one SQL `SELECT`. The service does not write SQL. It checks the statement, limits it, and runs it |
| Where it runs | The SQLite FTS5 index, then answer selection by fixed rules | A read-only SQLite database in memory, built for the one request, with only the rows the user may read |
| Result | One sentence or table row copied from a passage, or a list of documents with the qualifying line | Rows. Each row has its file, table, row, line and page |
| Code | [`query.py`](engineering_search/query.py), [`answer.py`](engineering_search/answer.py), `SearchService.search` | [`sql.py`](engineering_search/sql.py), `SearchService.query_sql` and `table_row_evidence` |
| Tools | `search_evidence`, `read_evidence` | `describe_schema`, `list_tables`, `describe_table`, `query_sql`, `get_document_evidence` |

The quality of a structured answer depends on the SQL that the client writes. The service makes sure that the statement can only read the permitted rows, and that each row can be cited. It does not check that the statement asks the right question. [ADR 0016](docs/adr/0016-structured-facts-and-client-written-sql.md) records this decision.

## Two lines: indexing and searching

The service does two separate jobs. They meet only at the index.

| Line | What it does | Code |
| --- | --- | --- |
| **Indexing** | Find every file in the document folder, detect its type and format version, choose a reader, read the file into passages and tables, extract facts from the tables, and plan the changes to the index | [`engineering_search/indexing/`](engineering_search/indexing/): `Indexer`. `SearchService.scan`, `reindex` and the upload workers call it, and `SearchService` publishes its plan |
| **Searching** | Change a question into an index query, check permissions, look it up, select the answer, audit and return. Or run a client's SQL over the permitted rows | [`query.py`](engineering_search/query.py), [`answer.py`](engineering_search/answer.py), [`sql.py`](engineering_search/sql.py), the lookups in [`store.py`](engineering_search/store.py), and `SearchService.search` and `query_sql` |

The index ([`store.py`](engineering_search/store.py)) is shared: indexing writes it through `SearchService`, and searching reads it. The indexing package does not import the store, the service or the web app. Nothing on the search line imports the indexing package. [`units.py`](engineering_search/units.py) is shared by both lines: the fact rules and the answer rules read numbers and units with the same table.

## The path of one question (unstructured)

[`SearchService.search`](engineering_search/service.py) does these steps in this order. The web page, the HTTP API and the MCP tool `search_evidence` all call it.

1. **Understand.** [`answer.understand`](engineering_search/answer.py) decides if the question asks for one value or for a list of documents. It also finds a number comparison, for example "greater than 5 kN/m²".
2. **Plan.** [`query.plan`](engineering_search/query.py) removes common words, adds synonyms, and makes words with digits into prefix searches.
3. **Find the matching files.** [`SQLiteSearchIndex.document_matches`](engineering_search/store.py) returns every file that contains at least one query word, with the number of query words it contains. If `within` is given, only those files are kept.
4. **Check permissions.** [`MockPermissionStore.evaluate`](engineering_search/access.py) decides which of these files the user may read. Everything after this step uses only permitted files.
5. **Look up.** [`SQLiteSearchIndex.candidates`](engineering_search/store.py) runs the FTS5 query over the permitted files only, and returns up to 1,000 passages (`CANDIDATE_LIMIT`), best first. The file filter is inside the index query, before the limit. Thus a forbidden file cannot push a permitted passage out of the result.
6. **Answer.** For one value, [`answer.answer`](engineering_search/answer.py) reads the 8 best permitted passages and selects one sentence or table row. It then reads all passages of that document to set the status (see [Answers and sources](#answers-and-sources)). For a list, [`answer.list_documents`](engineering_search/answer.py) reads every passage of each permitted document that contains every query word, and applies the number comparison.
7. **Page.** The supporting passages are paged with `limit` and `page`. The document list of a list answer is paged too, at 200 documents a page, with the same `page` value. `answer.count` is the total number of documents, `answer.document_pages` the number of pages, and `answer.truncated` is true when later pages exist.
8. **Audit.** The audit event is written. It holds the permission decision for each matched file and the source of the answer and of each passage. If the write fails, the user gets no evidence.
9. **Return.** The response holds `answer`, `evidence`, `searched_for`, counts and paging fields.

## The path of one SQL query (structured)

[`SearchService.query_sql`](engineering_search/service.py) does these steps. `POST /sql` and the MCP tool `query_sql` call it.

1. **Check permissions.** The service evaluates the permissions of the user on every indexed file.
2. **Build the projection.** [`SQLiteSearchIndex.structured`](engineering_search/store.py) returns the tables, rows and facts of the permitted files only. [`sql.Projection`](engineering_search/sql.py) loads them into a new SQLite database in memory. Forbidden rows are never in it, so no `WHERE`, `JOIN`, `COUNT`, aggregate or `LIMIT` can see them.
3. **Run the statement.** The projection accepts one statement that starts with `SELECT` or `WITH`, of at most 4,000 characters. An authoriser allows reads of the five projection tables and a list of plain functions, and denies everything else. `PRAGMA query_only` stops writes. A step budget stops a query that runs too long. At most 500 rows are returned (100 by default), with `truncated` when there are more.
4. **Audit.** The event holds the SHA-256 of the statement, its length, the number of files in scope and excluded by policy, the number of rows, and the files named in the result. It never holds the rows. A refused statement is audited too, with the error.
5. **Return.** The response holds `columns`, `rows`, `row_count`, `truncated` and the number of readable files.

The projection is closed after the request. The service lock is held only while the projection is built, not while the statement runs.

The projection has these tables ([`sql.SCHEMA`](engineering_search/sql.py) describes every column, and `describe_schema` returns it to the client):

| Table | Contents |
| --- | --- |
| `documents` | One row per readable indexed file: `file_id`, `project` (from a top folder named `project-<name>`), `folder`, `file_type`, `source_version`, `passages` |
| `facts` | One row per typed cell: `subject`, `parameter`, `role`, `value` as written, `number` with its sign, `unit`, `si_value`, `dimension`, `project` and `project_source` (`row` or `folder`), with `file_id`, `table_no`, `row_no`, `line` and `page` |
| `components` | A view: one row per table row that has facts, with `material_grade`, `allowable_load_kn_m2` (a capacity), `imposed_load_kn_m2` (a demand) and `compliance_status`. Loads are in kN/m² |
| `table_rows` | Every table row, with its original cells as JSON |
| `source_tables` | Every table, with its name and its column headers as JSON |

To cite a row, the client calls `get_document_evidence` (`GET /evidence/<file>/tables/<n>/rows/<n>`). [`SearchService.table_row_evidence`](engineering_search/service.py) checks the permission for that file and returns the column names, the cells as read, the line and page, the file version, the facts of the row, and the passage that holds the row.

## Modules

| Module | Responsibility |
| --- | --- |
| [`indexing/`](engineering_search/indexing/) | The indexing line. See [The indexing line](#the-indexing-line) |
| [`core.py`](engineering_search/core.py) | Defines `Passage`, `Table`, `TableRow`, `Fact` and `Document`, and the `SearchIndex` and `AuditStore` interfaces. `SearchIndex` is the seam where the store is injected |
| [`units.py`](engineering_search/units.py) | The unit table, signed numbers, and conversion to SI units (pressure in Pa). Used by the fact rules and the answer rules |
| [`store.py`](engineering_search/store.py) | `SQLiteSearchIndex`: documents, passages and the FTS5 index, the stored inventory, tables, rows and facts. Changes are applied in one transaction |
| [`query.py`](engineering_search/query.py) | Changes a question into an index query: stop words, synonyms, prefix terms |
| [`answer.py`](engineering_search/answer.py) | Selects the answer text and its status, makes document lists, compares numbers with unit conversion |
| [`sql.py`](engineering_search/sql.py) | The constrained SQL projection, its schema and its limits |
| [`access.py`](engineering_search/access.py) | Pretend users, path-based access rules, sessions. The access assumptions are at the top of the file |
| [`service.py`](engineering_search/service.py) | `SearchService`: search, read a file, SQL query, table row evidence, schema, reindex, scan, status, coverage and upload publish. It calls the `Indexer` and publishes its plans to the index under its locks. The web app and the MCP server share it. It has no web code |
| [`app.py`](engineering_search/app.py) | The web app: HTTP routes, pretend sign-in, the index-team boundary, uploads and the web pages. `AdmissionMiddleware` admits each search, SQL query and row-evidence request before it waits for a worker thread. It changes requests into `SearchService` calls |
| [`mcp_server.py`](engineering_search/mcp_server.py) | The MCP server (stdio). Tools: `search_evidence`, `read_evidence`, `describe_schema`, `list_tables`, `describe_table`, `query_sql`, `get_document_evidence`, and `get_index_coverage` for the index team only. It uses `SearchService` directly, without the web app |
| [`runtime.py`](engineering_search/runtime.py) | Opens the index, lock, queue and audit files in the state folder. Builds the web app or the service alone |
| [`jobs.py`](engineering_search/jobs.py) | The SQLite upload queue and the worker threads |
| [`adapters.py`](engineering_search/adapters.py) | The cross-process `FileLock`, `Admission` (the time budget), the SQLite audit store and the in-memory telemetry |
| [`static/`](engineering_search/static/) | The web pages: `search.html` (with the sign-in screen), `admin.html` (index operations) and `audit.html` (audit log). There is no web page for SQL or for the coverage report |

Every import points down the layers of the diagram:

- `__main__.py` imports `runtime.py`. `mcp_server.py` imports `runtime.py`, `service.py` and `access.py`.
- `runtime.py` imports `app.py`, `service.py`, `access.py` and the stores. It opens the SQLite files and the lock file, and gives them to the service as objects.
- `app.py` imports `service.py`, `access.py`, `adapters.py`, `jobs.py`, `store.py` and `core.py`. It imports the stores only to make defaults when none are given (the tests do this, with an in-memory index).
- `service.py` imports `indexing/`, `query.py`, `answer.py`, `sql.py`, `access.py`, `adapters.py`, `jobs.py` and `core.py`. It does not import `store.py`: it gets the index as an object.
- `indexing/` imports only `core.py` and `units.py`.
- `answer.py` imports `core.py`, `query.py` and `units.py`. `store.py` imports `core.py` and `query.py`.
- `core.py`, `units.py`, `query.py`, `sql.py`, `access.py`, `adapters.py` and `jobs.py` import nothing from the package.

Only `app.py` knows HTTP. Only `mcp_server.py` knows MCP. SQL is only in `store.py`, `sql.py`, `adapters.py` and `jobs.py`.

## The indexing line

All of it is in [`engineering_search/indexing/`](engineering_search/indexing/). [`tests/test_indexer.py`](tests/test_indexer.py) and [`tests/test_coverage.py`](tests/test_coverage.py) test it with a folder only: no web app, no index database and no queue.

```text
Indexer.scan()          every file → detect type and version → choose a reader → read and hash if one fits → Inventory
Indexer.plan(indexed)   scan, compare with the index, extract the files that need it → IndexPlan
SearchService           under the index lock: index.apply(upserts, removals, inventory), in one transaction
```

| File | Contents |
| --- | --- |
| `detect.py` | `ContentDetector` (the default) and `ExtensionDetector` |
| `status.py` | The status of each file, and a hint for each status that is a gap |
| `inventory.py` | `SourceFile` and `Inventory`: every file of a scan, with its type, format version, status, reader and warnings |
| `readers/` | The readers, their manifests, and the registry (`default_registry()`) |
| `facts.py` | The fixed rules that turn table cells into facts |
| `indexer.py` | `Indexer`: scan, plan, extract one file |
| `coverage.py` | The coverage report |

### 1. Detect the file type and format version

[`ContentDetector`](engineering_search/indexing/detect.py) treats the extension as a hint. It reads at most the first 512 bytes, and checks the signature of the formats that have one:

| Content | Type and version |
| --- | --- |
| `%PDF-1.7` | `pdf`, version 1.7 |
| A ZIP with `xl/workbook.xml` | `excel` |
| A ZIP with `word/document.xml` | `word` |
| `Version 10.0 JT` in the 80-character header | `jt`, version 10.0 |

When the content has a signature, the content decides the type. When the extension claims a format with a signature and the signature is absent, the status is `FORMAT_MISMATCH`. When the header starts correctly but is broken (for example a damaged ZIP), the status is `INVALID_HEADER`. Markdown and CSV have no signature: the extension decides. Other known extensions (`.txt`, `.dwg`, `.dxf`, CATIA, `.ifc`) are named by extension. Any other extension is `unknown`.

The JT probe reads the version string of the header only. It is not a JT parser. A detected version does not mean that any reader can read the file.

A detector is any object with `detect(path, head) -> FileSignature` (the `Detector` protocol). Pass another one as `Indexer(root, detector=...)`.

### 2. Choose a reader

[`ReaderRegistry.select`](engineering_search/indexing/readers/registry.py) chooses the first reader that reads the file type and the format version, and whose Python packages are installed. [`default_registry()`](engineering_search/indexing/readers/registry.py) is the one place that lists the readers. Several readers can read one type; the first that fits is chosen.

Each reader has a manifest ([`readers/base.py`](engineering_search/indexing/readers/base.py)): an ID and a reader version, the file types, the format versions it is tested with, its capabilities (text, tables, metadata, geometry) and its dependencies.

| Reader | Type | What it reads | Status when it cannot read all of a file |
| --- | --- | --- | --- |
| `markdown-text@2` | `markdown` | UTF-8 text, split at headings and blank lines, not inside code fences. Pipe tables are also read as tables, with the line of each row | `MALFORMED` if the file is not UTF-8. `NO_EXTRACTABLE_CONTENT` if there is no text |
| `pdf-text-pypdf@1` | `pdf` 1.x and 2.x | The text layer of each page, with pypdf, split at numbered headings and blank lines, at most 15 lines a passage. No tables. No OCR | `NO_TEXT_LAYER` if no page has text. `INDEXED_PARTIAL` if some pages have no text. `ENCRYPTED`, `MALFORMED` |
| `csv-table@1` | `csv` | One table. Each data row is also a passage, with the header line as its heading | `INDEXED_PARTIAL` if rows have a different number of cells than the header |
| `xlsx-openpyxl@1` | `excel` | One table per sheet, and one passage per data row. The page of a passage is the sheet number, and its lines are sheet rows. Cell values are the values that Excel cached | `INDEXED_PARTIAL` if a formula has no cached value: the cell is left empty, and the warning names it. Hidden sheets are read, with a warning. `ENCRYPTED`, `MALFORMED` |

The registry tells three cases apart when no reader fits:

| Status | Meaning |
| --- | --- |
| `NO_READER` | A known file type with no registered reader, for example `jt`, `text`, `word` or `dwg` |
| `UNSUPPORTED_VERSION` | Readers exist for the type, but none is tested with this format version |
| `DEPENDENCY_MISSING` | A reader fits, but a package that it needs is not installed |

An unknown type is `UNSUPPORTED_FORMAT`.

### 3. Scan into an inventory

[`Indexer.scan`](engineering_search/indexing/indexer.py) lists every regular file below the document folder. It does not follow symbolic links, and it skips hidden files and folders (names that start with `.`). An unreadable folder fails the scan. A file is read and hashed (SHA-256) only if a reader fits. Each file gets one status ([`status.py`](engineering_search/indexing/status.py)):

| Group | Statuses | In the index |
| --- | --- | --- |
| Read | `INDEXED_FULL`, `INDEXED_PARTIAL`, `NO_TEXT_LAYER`, `NO_EXTRACTABLE_CONTENT` (`CLASSIFIED` before extraction) | Yes. A file with no text is in the index with zero passages, and its status says why |
| Not supported | `UNSUPPORTED_FORMAT`, `NO_READER`, `UNSUPPORTED_VERSION`, `DEPENDENCY_MISSING`, `FORMAT_MISMATCH`, `INVALID_HEADER` | No. Listed with type, version and size |
| Failed | `READ_ERROR`, `MALFORMED`, `ENCRYPTED`, `READER_CRASH` | No. Listed in `failed_files` |

The inventory is published with the index, in the `files` table. Thus it survives a restart. `/index/status` and the index operations page show the type, format version and status of each file. The coverage report ([`coverage.py`](engineering_search/indexing/coverage.py), `GET /index/coverage` and the MCP tool `get_index_coverage`, index team only) counts the files by type and format version, by status, by top folder and by capability, lists the readers, and lists each file that was not fully read, with the reason and a hint.

### 4. Extract tables and facts

[`Indexer.extract`](engineering_search/indexing/indexer.py) reads one file with its reader, then runs [`facts.extract_facts`](engineering_search/indexing/facts.py) over the tables. Facts come only from table cells, never from free text.

The rules read the column header, the table name and the cell:

- A cell under a grade or material header that matches a grade pattern (S355J2+N, C30/37, B500B, Grade 50) is a `material_grade` with the role `specification`.
- A cell under a status, approval or compliance header is a `compliance_status` with the role `status`, as written.
- A cell with a quantity (a number with a unit in the cell, or a plain number with the unit in the header, for example "Allowable UDL (kN/m²)") is converted to SI. The header then decides the parameter and the role: `allowable_distributed_load` or `load_capacity` (capacity), `roof_imposed_load`, `imposed_load` or `applied_load` (demand), `settlement` or `deflection` (measurement). Any other quantity gets the column name as its parameter and the role `unknown`.
- The subject is the cell of the first column whose header names a component, member, mark, reference or similar, otherwise the first column. A `Project` column sets the project of each row.
- In a key-value table (`| Parameter | Value | ... |`), the row label takes the place of the column header, and the subject is the table's heading.

Capacity and demand are never the same parameter. A number keeps its sign: "-12" under "Predicted settlement (mm)" is −0.012 m.

### 5. Plan the index changes

[`Indexer.plan`](engineering_search/indexing/indexer.py) takes the versions that are in the index now (file ID → SHA-256) and the last published inventory. It extracts a file when:

- the file is new or its content changed;
- the chosen reader or reader version changed; or
- the previous status of the file is not known.

It returns an `IndexPlan`: the documents to write, the file IDs to remove, the versions after publish, the inventory and the failed files. The indexer never writes the index.

If a file cannot be read or extracted, the plan reports it in `failed_files` with its status, and the other files are indexed. A failed file is removed from the index, so an old version is not kept as if it were current.

Uploads use the same component: the upload workers call `Indexer.extract` for one file.

### 6. Publish

`SearchService.reindex` holds the index lock from reading the index versions to publishing the plan. The lock is a `FileLock` on `<state-dir>/index-<id>.lock` ([`adapters.py`](engineering_search/adapters.py)), which `runtime.py` injects. It uses `flock`, so other processes see it. Thus the web server and the MCP servers that share one index take turns: no process can publish a plan that it made from versions that another process has since changed. The upload workers hold the same lock when they publish one file.

## The index

The index is one SQLite file, `<state-dir>/index-<id>.sqlite3`.

| Table | Contents |
| --- | --- |
| `documents` | One row for each indexed file: path, SHA-256 version, passage count |
| `passages` | The exact passage text, heading, line range and page |
| `passages_fts` | The FTS5 inverted index of each passage's heading, text and file-path words. It uses the `porter unicode61` tokenizer, so "loads" matches "load" |
| `files` | The last published inventory: one JSON record per file found, including files that are not indexed |
| `source_tables` | Each table read from a document: its number, its name (the heading above it, or the sheet name) and its column headers |
| `table_rows` | Each table row: its cells as read, its line, and its page (or sheet) |
| `facts` | The typed facts of each table row |
| `meta` | The time of the last change |

A rebuild runs the [indexing line](#the-indexing-line): it reads and hashes every file that has a reader. It extracts only the files listed in [step 5](#5-plan-the-index-changes), and removes deleted files. `read_files` in the index result counts the extracted files, not the files that were read and hashed. All changes are applied in one transaction. If the transaction fails, the old index stays.

The ranking:

1. Passages that contain more of the query words come first. Words in the heading or the file path count.
2. Then BM25, with weights 3 for the heading, 1 for the text and 0.5 for the file path.

## Permissions

All files are indexed. Permissions decide what each user sees. See the assumptions at the top of [`access.py`](engineering_search/access.py).

- A rule applies to the whole repository, to a folder, or to one file. The most specific rule wins. For example, `project-harbour/harbour-roof-schedule.xlsx` is readable by JP and Maya only.
- For a text question, the service evaluates permissions on every file that contains a query word, then filters inside the index query, before the 1,000-passage limit, the answer, the counts and the pages.
- For SQL, the service evaluates permissions on every indexed file, and builds the projection from the permitted files only, before any filter, join, count or limit.
- A response contains no name, text or count of files that the user cannot read. [`tests/test_no_leaks.py`](tests/test_no_leaks.py) checks this for every user, every evaluation question in each mode, questions made from each forbidden file, `within` lists that name forbidden files, the first five and the last result pages, and direct reads. [`tests/test_sql.py`](tests/test_sql.py) checks that a user gets only rows from permitted files.
- The audit log records each decision. Only the index team (Maya) can read it.

## Answers and sources

A text answer is always text copied from one passage. It has the file, page, line range and file version of that passage. The acceptance tests in [`tests/test_use_case.py`](tests/test_use_case.py) check each answer against the file itself.

The source proves where the text is. The status says how well the text is bound to the question. A question word is **bound** when it is in the selected sentence, in its passage heading, in the file path, or in the document title. The title is the heading of the first passage, and only if that passage starts on the first 3 lines of the file (or of the first page).

| Status | Meaning |
| --- | --- |
| `found` | Every question word is bound to the selected sentence |
| `unverified` | The document contains every question word, but the sentence does not name some of them (`unbound_words`). The value may be about something else. For example, "What is the mezzanine floor load at Harbour?" gets "The floor design load is 4.0 kN/m² on all warehouse slabs." with `mezzanine` unbound |
| `partial` | Some question words are not in the document (`missing_words`) |
| `not_found` | No sentence states a value and matches enough question words |

For a list with a number comparison, a document qualifies only if one line states a quantity that meets the comparison and every question word is bound to that line. Thus "floor load 10 kN/m²" does not qualify a document for "roof load greater than 5 kN/m²".

Numbers keep their sign. "−12 mm" and "-2 kN/m²" are negative. A hyphen inside a code ("B-104") or a range ("1-2 kN") is not a sign.

The service does not make text or choose between documents that disagree. It shows up to five other documents that state a value, taken from the 8 best passages, so the user can see some conflicts. This is not every value in the repository.

A structured answer is a set of rows. Each row carries `file_id`, `table_no`, `row_no`, `line` and `page`, and `get_document_evidence` returns the row as read with its passage. The client chooses the rows with its SQL. The service does not check that the SQL matches the question.

## What runs where

| Process | Started by | Contents |
| --- | --- | --- |
| Web service | `python -m engineering_search` | FastAPI app, upload workers, startup index |
| MCP server | Each chat client (`python -m engineering_search.mcp_server --user <id>`) | A `SearchService` only. No web app, no upload workers. Refreshes the index when it starts |

Several processes can use the same state folder. They then share the index, the lock file and the audit log. SQLite WAL mode and a 30-second lock timeout let them write in turn, so no write is half applied. The index lock lets one process at a time plan and publish index changes. [`tests/test_binding.py`](tests/test_binding.py) checks that a refresh waits while another holder has the lock.

The MCP server was used by hand over local stdio from Claude Code (`.mcp.json`), Codex (`-c mcp_servers.engineering_search.*` overrides on the command line) and Pi (`.pi/mcp.json`). [`tests/test_mcp_stdio.py`](tests/test_mcp_stdio.py) starts the server over stdio with a real MCP client. The server is not exposed over HTTP. [docs/MCP.md](docs/MCP.md) gives the setup for each client.

## Time budget and admission

The use case asks for an answer in under 10 seconds. One process answers one request at a time: `SearchService.lock` is held from the file match to the audit write, and the index has one SQLite connection. On the 148 test files that is about 10 requests a second. Without a limit, the 1,000th of 1,000 simultaneous requests waited 102 s.

[`Admission`](engineering_search/adapters.py) refuses a request at once if it cannot be answered within the budget (`SEARCH_BUDGET_SECONDS`, default 8 s, which leaves 2 s for the network and the chat client):

1. With n = requests in flight + 1, the predicted time is n × mean + 2 × √n × spread. The mean and spread are moving averages of measured service times (smoothing 0.05, first guess 0.2 s).
2. A request's own service time runs from the later of its arrival and the previous departure to its departure, so time spent waiting is not counted as work.
3. If the prediction is over the budget, the request is refused with a retry time, before any work, and with no evidence.

| Front end | Where it admits | What a refused caller gets |
| --- | --- | --- |
| Web app | `AdmissionMiddleware`, for `POST /search`, `POST /sql` and `GET /evidence/...`, before the route waits for a worker thread | 503, a `Retry-After` header and `{"busy": true, "retry_after_seconds": n, "message": ...}`. The web page shows the message |
| MCP server | `service.admit()` around each search, read, SQL and evidence tool | The same object as the tool error. The server instructions tell the agent to report it and not to retry in a loop |

Index operations and uploads are not admitted. `/index/status` shows the index team the learnt service time and spread, requests in flight, refusals and capacity.

Measured with `scripts/load_test.py` (one process, budget 8 s): at 100 and at 1,000 simultaneous requests, every answered request finished within 5.7 s and every refusal came back within 0.25 s. About 50 of each burst are answered. This bounds the time a user waits; it does not add capacity. [ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md) gives the numbers and the work needed to serve the company: concurrent reads, several worker processes, SQL without a copy per request, and load tests at the real size. Serving the whole organisation, with any number of users each answered within 10 seconds and no single point of failure, is its own engineering work: [docs/README.md](docs/README.md#making-it-available-to-an-organisation) sets out what it needs.

Over local stdio each chat client starts its own MCP server process, so MCP users do not queue behind each other in one process. They share the machine and the SQLite files.

## MVP shortcuts in the code

The MVP takes these shortcuts on purpose, to deliver quickly. Each one is acceptable for a local demonstration with 148 files. Each one must change before a shared service. [TODO.md](TODO.md) gives the gaps and the next work.

| Area | Shortcut | Effect | Change before a shared service |
| --- | --- | --- | --- |
| Identity | Pretend sign-in. Sessions are in memory. The MCP server takes the user from `--user` | Anyone can act as any user. Sessions end when the service stops. The MCP identity is not verified: it is a security hole | Company sign-in (OAuth). User from a verified token |
| Permissions | Access rules are a Python dictionary in `access.py` | A change needs a code change. No groups or deny rules | Read the permissions from the repository |
| Index-team tool | The MCP server registers `get_index_coverage` only when `--user` is an index-team user | The check rests on the unverified `--user` flag | The verified identity decides |
| Concurrency | One lock (`SearchService.lock`) and one SQLite connection in each process. A search holds the lock from the file match to the audit write. A file lock serialises index publication between processes | About 10 requests a second per process on the test data. Admission control keeps each answer within the budget by refusing the rest at once ([Time budget and admission](#time-budget-and-admission)) | One read connection per thread with snapshot reads, no global lock for searches, several worker processes ([ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md)) |
| SQL | The client writes the SQL. The service limits it (one `SELECT`, authoriser, read-only, step budget, row limit) and builds a projection for each request | The answer is only as good as the client's SQL, and it is not yet scored ([ADR 0019](docs/adr/0019-evaluate-retrieval-and-nl-to-sql.md)). Each request copies the permitted structured rows into memory: about 2 µs a fact to build and 1 µs to query `components`, so 3 s at a million facts, under the service lock. At 200,000 facts the 2,000,000-step budget stops even the standard S355 query, because `components` groups every fact | A query service with permissions in the database, or fixed query tools for common questions |
| Uploads | The upload routes in `app.py` call `service.queue` directly to create, read, fail and retry jobs. Only saving and indexing go through `SearchService` | Upload logic is in two modules. The MCP server cannot upload | Move the job steps into `SearchService` if another front end needs uploads |
| Errors | `ServiceError` carries an HTTP status code, also in the service | Simple: the web app returns the status, the MCP server returns the message. The service knows HTTP status numbers | Acceptable. Use named error types if more callers come |
| Index state | The inventory is stored with the index. The last scan time, the last index run and the operation state are in memory | After a restart, the index operations page shows the stored inventory but not the last run | Store the run history with the index |
| Telemetry | In memory | Resets when the service stops | A metrics system |
| File types | `ContentDetector` checks signatures for PDF, XLSX, DOCX and JT only. Markdown, CSV and the others are named by extension | A misnamed text file is found only when its reader fails. The JT probe reads the header version, not the content | libmagic or a format identification tool, and the format versions of more types ([ADR 0003](docs/adr/0003-versioned-reader-selection.md)) |
| Readers | Markdown, text-layer PDF, CSV and XLSX only | No OCR, no PDF tables, no Word, no CAD or BIM content. The coverage report lists these files | Readers or connectors for the formats that the real repository holds ([design/DATA-PROFILE.md](design/DATA-PROFILE.md)) |
| Query words | Stop words and synonyms are lists in `query.py` | Changes need a code change. The lists fit the test questions | A parameter dictionary that engineers maintain |
| Answer rules | Value patterns are regular expressions in `answer.py`. The title is a heuristic: the first heading, only if its passage starts on the first 3 lines | They fit the test documents. Other notations are missed. A Markdown title with no text directly under it is not used, so its words do not bind | Readers return the title. More patterns from real documents |
| Fact rules | Fixed header and cell patterns in `facts.py`, from tables only | A value in free text is not a fact. A header that the rules do not know gives the role `unknown`. Key-value tables put their heading in `subject`, so `components` mixes real components (B-104) with 121 rows whose subject is "Roof load", mostly from the generated project files; a query must filter by project, grade or subject to tell them apart | A parameter dictionary, and extraction from text with span checks ([design/EXTRACTION.md](design/EXTRACTION.md)) |
| List answers | A list question reads all passages of each matching document from SQLite. Pages of 200 documents | Fast for 148 files. Slow for many thousands of matches | Facts and metadata in the index, with filters in the query |
| Web pages | Plain HTML and JavaScript, no framework, no build step. Checked by eye. No SQL page and no coverage page | No automated web page tests | Add browser tests if the pages stay |
| Uploads | Markdown only, 10 MiB, local worker threads | No PDF, CSV or XLSX upload. Workers stop with the service | A shared queue and workers ([design/SCALING.md](design/SCALING.md)) |
| Storage | SQLite files in one state folder, shared by the web service and the MCP servers. The file lock uses `flock` | One machine. Writers take turns. Not tested on Windows | A server database or search engine |

## Defects fixed since the review

An independent review on 2026-10-28 found six defects. All six are now fixed, and each fix has a test.

| Defect | Fix | Test |
| --- | --- | --- |
| A wrong parameter could be returned with status `found` | The status checks the question words against the sentence, its heading, the file path and the title. Otherwise it is `unverified`. A list comparison needs every question word bound to the qualifying line | [`tests/test_binding.py`](tests/test_binding.py) |
| The 1,000-passage lookup limit applied before permissions and `within` | The permitted files are passed into the FTS5 query, before the limit | [`tests/test_binding.py`](tests/test_binding.py), [`tests/test_no_leaks.py`](tests/test_no_leaks.py) |
| Number comparisons ignored a minus sign | Signed numbers are read ([`units.py`](engineering_search/units.py) `SIGNED`) | [`tests/test_binding.py`](tests/test_binding.py), [`tests/test_facts.py`](tests/test_facts.py) |
| A list stopped at 200 documents and could not be paged | `page` pages the document list. `count` is the total | [`tests/test_binding.py`](tests/test_binding.py) |
| Index refreshes in two processes were not coordinated | A cross-process file lock serialises plan and publish | [`tests/test_binding.py`](tests/test_binding.py) |
| A PDF without a text layer counted as indexed | The PDF reader reports `NO_TEXT_LAYER` or `INDEXED_PARTIAL`, and the coverage report lists the file | [`tests/test_coverage.py`](tests/test_coverage.py) |

Also fixed earlier: a file read error no longer stops the whole index refresh. The indexer reports the file as `READ_ERROR` in `failed_files` and indexes the others ([`tests/test_indexer.py`](tests/test_indexer.py)).
