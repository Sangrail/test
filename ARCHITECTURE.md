# Architecture

This document describes the code as it runs now. [design/SYSTEM-DESIGN.md](design/SYSTEM-DESIGN.md) describes the wider design and the phases. [design/EXTRACTION.md](design/EXTRACTION.md) describes how extraction and the stores must grow.

## Overview

![Code architecture](design/code-architecture.png)

Source: [design/code-architecture.svg](design/code-architecture.svg), made by [design/make_architecture.py](design/make_architecture.py). Change the script when a module or an import changes. [design/system-design.png](design/system-design.png) shows the wider system and the phases.

The diagram shows the modules by layer. Every import points down the page. There are two processes: the web server (`python -m engineering_search`) and the MCP server, which the chat client starts. Each process has its own `SearchService`. They share the SQLite files in the state folder.

## The path of one question

[`SearchService.search`](engineering_search/service.py) does these steps in this order. The web page, the HTTP API and the MCP server all call it.

1. **Understand.** [`answer.understand`](engineering_search/answer.py) decides if the question asks for one value or for a list of documents. It also finds a number comparison, for example "greater than 5 kN/m²".
2. **Plan.** [`query.plan`](engineering_search/query.py) removes common words, adds synonyms, and makes words with digits into prefix searches.
3. **Look up.** [`SQLiteSearchIndex.candidates`](engineering_search/store.py) runs the FTS5 query and returns up to 1,000 passages, best first. For a list question, `document_matches` also finds the documents that contain every word.
4. **Check permissions.** [`MockPermissionStore.evaluate`](engineering_search/access.py) decides which of the matched files the user may read. Everything after this step uses only permitted files.
5. **Answer.** [`answer.answer`](engineering_search/answer.py) selects one sentence or table row. [`answer.list_documents`](engineering_search/answer.py) makes the document list and applies the number comparison.
6. **Page.** The supporting passages are paged.
7. **Audit.** The audit event is written. It holds the permission decision for each file and the source of the answer and of each passage. If the write fails, the user gets no evidence.
8. **Return.** The response holds `answer`, `evidence`, `searched_for`, counts and paging fields.

## Modules

| Module | Responsibility |
| --- | --- |
| [`core.py`](engineering_search/core.py) | Finds source files (`.md`, `.pdf`). Reads them into passages. Defines `Passage`, `Document` and the `SearchIndex` and `AuditStore` interfaces |
| [`store.py`](engineering_search/store.py) | `SQLiteSearchIndex`: the documents, passages and FTS5 tables. Changes are applied in one transaction |
| [`query.py`](engineering_search/query.py) | Changes a question into an index query: stop words, synonyms, prefix terms |
| [`answer.py`](engineering_search/answer.py) | Selects the answer text, makes document lists, compares numbers with unit conversion |
| [`access.py`](engineering_search/access.py) | Pretend users, path-based access rules, sessions. The access assumptions are at the top of the file |
| [`service.py`](engineering_search/service.py) | `SearchService`: search, read a file, reindex, scan, status and upload publish. The web app and the MCP server share it. It has no web code |
| [`app.py`](engineering_search/app.py) | The web app: HTTP routes, pretend sign-in, the index-team boundary, uploads and the web pages. It changes requests into `SearchService` calls |
| [`mcp_server.py`](engineering_search/mcp_server.py) | The MCP server (stdio) with `search_evidence` and `read_evidence`. It uses `SearchService` directly, without the web app |
| [`runtime.py`](engineering_search/runtime.py) | Opens the index, queue and audit files in the state folder. Builds the web app or the service alone |
| [`jobs.py`](engineering_search/jobs.py) | The SQLite upload queue and the worker threads |
| [`adapters.py`](engineering_search/adapters.py) | The SQLite audit store and the in-memory telemetry |
| [`static/`](engineering_search/static/) | The web pages: `search.html` (with the sign-in screen), `admin.html` (index operations) and `audit.html` (audit log) |

Every import points down the layers of the diagram:

- `__main__.py` imports `runtime.py`. `mcp_server.py` imports `runtime.py`, `service.py` and `access.py`.
- `runtime.py` imports `app.py`, `service.py` and the stores. It opens the SQLite files and gives them to the service as objects.
- `app.py` imports `service.py`, `access.py`, `adapters.py`, `jobs.py`, `store.py` and `core.py`. It imports the stores only to make defaults when none are given (the tests do this, with an in-memory index).
- `service.py` imports `query.py`, `answer.py`, `access.py`, `adapters.py`, `jobs.py` and `core.py`. It does not import `store.py`: it gets the index as an object.
- `answer.py` and `store.py` import `core.py` and `query.py`. `core.py`, `query.py`, `access.py`, `adapters.py` and `jobs.py` import nothing from the package.

Only `app.py` knows HTTP. Only `mcp_server.py` knows MCP. SQL is only in `store.py`, `adapters.py` and `jobs.py`.

## Reading files

[`extract`](engineering_search/core.py) reads one file and returns its passages.

- **Markdown:** the reader splits the text at headings and blank lines. It does not split inside code fences. Line numbers are lines of the file.
- **PDF:** the reader uses pypdf to get the text layer of each page. It splits each page at numbered headings (for example "3.1 Roof load limit") and blank lines. A passage has at most 15 lines. Line numbers are lines of the page text, and each passage has its page number.

If a file cannot be read, the index build skips it and reports it in `failed_files`. The other files are indexed.

## The index

The index is one SQLite file, `<state-dir>/index-<id>.sqlite3`.

| Table | Contents |
| --- | --- |
| `documents` | One row for each file: path, SHA-256 version, passage count |
| `passages` | The exact passage text, heading, line range and page |
| `passages_fts` | The FTS5 inverted index of each passage's heading, text and file-path words. It uses the `porter unicode61` tokenizer, so "loads" matches "load" |
| `meta` | The time of the last change |

A rebuild compares the SHA-256 of each file with the stored version. It reads only new and changed files, and removes deleted files. All changes are applied in one transaction. If the transaction fails, the old index stays.

The ranking:

1. Passages that contain more of the query words come first. Words in the heading or the file path count.
2. Then BM25, with weights 3 for the heading, 1 for the text and 0.5 for the file path.

## Permissions

All files are indexed. Permissions decide what each user sees. See the assumptions at the top of [`access.py`](engineering_search/access.py).

- A rule applies to the whole repository, to a folder, or to one file. The most specific rule wins.
- The service checks permissions on each request, before it selects the answer, counts results or pages them.
- A user never sees the name or the number of files that they cannot read.
- The audit log records each decision. Only the index team (Maya) can read it.

## Answers and sources

An answer is always text copied from one passage. It has the file, page, line range and file version of that passage. The acceptance tests in [`tests/test_use_case.py`](tests/test_use_case.py) check each answer against the file itself.

The service does not make text, calculate values or choose between documents that disagree. It shows the other documents that state a value, so the user can see conflicts.

## What runs where

| Process | Started by | Contents |
| --- | --- | --- |
| Web service | `python -m engineering_search` | FastAPI app, upload workers, startup index |
| MCP server | The chat client (`python -m engineering_search.mcp_server`) | A `SearchService` only. No web app, no upload workers |

Both processes can use the same state folder. They then share the index and the audit log. SQLite WAL mode and a 30-second lock timeout let them write in turn.

## MVP shortcuts in the code

The MVP takes these shortcuts on purpose, to deliver quickly. Each one is acceptable for a local demonstration with 138 files. Each one must change before a shared service. [TODO.md](TODO.md) gives the gaps and the next work.

| Area | Shortcut | Effect | Change before a shared service |
| --- | --- | --- | --- |
| Identity | Pretend sign-in. Sessions are in memory. The MCP server takes the user from `--user` | Anyone can act as any user. Sessions end when the service stops. The MCP identity is a security hole | Company sign-in (OAuth). User from a verified token |
| Permissions | Access rules are a Python dictionary in `access.py` | A change needs a code change. No groups or deny rules | Read the permissions from the repository |
| Concurrency | One lock (`SearchService.lock`) protects the index and the state. A search holds it from the index lookup to the audit write | Searches run one at a time. A search waits while an index commit runs | Read-only searches without a global lock, on a server index |
| Uploads | The upload routes in `app.py` call `service.queue` directly to create, read, fail and retry jobs. Only saving and indexing go through `SearchService` | Upload logic is in two modules. The MCP server cannot upload | Move the job steps into `SearchService` if another front end needs uploads |
| Errors | `ServiceError` carries an HTTP status code, also in the service | Simple: the web app returns the status, the MCP server returns the message. The service knows HTTP status numbers | Acceptable. Use named error types if more callers come |
| Index state | The last scan and the index state are in memory | After a restart, the index operations page shows "not scanned" until the next scan | Store the state with the index |
| Telemetry | In memory | Resets when the service stops | A metrics system |
| Readers | The file extension selects the reader (`.md` or `.pdf`) | A damaged or wrong file is found only when it fails | Detect the format and version from the content ([ADR 0003](docs/adr/0003-versioned-reader-selection.md)) |
| Query words | Stop words and synonyms are lists in `query.py` | Changes need a code change. The lists fit the test questions | A parameter dictionary that engineers maintain |
| Answer rules | Value patterns and units are regular expressions in `answer.py` | They fit the test documents. Other notations are missed | Index-time facts store ([design/EXTRACTION.md](design/EXTRACTION.md)) |
| List answers | A list question reads all passages of each matching document from SQLite | Fast for 138 files. Slow for many thousands of matches | Facts and metadata in the index, with filters in the query |
| Web pages | Plain HTML and JavaScript, no framework, no build step. Checked by eye | No automated web page tests | Add browser tests if the pages stay |
| Uploads | Markdown only, 10 MiB, local worker threads | No PDF upload. Workers stop with the service | A shared queue and workers ([design/SCALING.md](design/SCALING.md)) |
| Storage | SQLite files in one state folder, shared by the web service and the MCP server | One machine. Writers take turns | A server database or search engine |
