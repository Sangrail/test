# Run the service

Each person runs an independent copy of the service. The web server, the index, the upload queue and the audit log are all on the machine that runs the service. You do not need a central server, an account, an API key or a cloud database.

## Install

You need Python 3.11 or later and `uv`. The service was tested on macOS with Python 3.13. Linux uses the same commands. Windows was not tested.

```bash
uv sync --locked
```

The install needs network access. Indexing and search do not need network access.

## Start the web service

```bash
uv run --frozen python -m engineering_search
```

The service does these steps:

1. It opens or creates the index in `.runtime/`.
2. It detects the type of every file in `test-repository/`, reads and hashes the files that have a reader, and extracts passages, tables and facts from the new and changed files. It holds the index lock while it does this.
3. It starts two upload workers.
4. It starts the web server on `127.0.0.1:8000`.

Open <http://127.0.0.1:8000/search>. The page shows only the sign-in screen until you select a demo user. The screen says what each user can do and what to try. For example:

1. Sign in as JP. Ask "Has building control approved the Northgate warehouse?".
2. Ask "Do we have any documents in Northgate?". Select "Ask the next question about these documents only", then ask "Of those documents, which mention compliance?".
3. Ask "Which documents have a roof load greater than 5 kN/m²?".
4. Ask "What is the mezzanine floor load at Harbour?". The page shows "Value found, subject not confirmed": the sentence states a floor load, but it does not say "mezzanine".
5. Sign out, sign in as Kamal, and ask the first question again. Kamal cannot read the Northgate file. Thus the answer is "not found", or a closest match that the page marks as not an answer.
6. Sign in as Maya to open `/admin` (index operations) and `/audit` (audit log).

The web page has no SQL box. Structured questions go through the HTTP API (`POST /sql`) or a chat client (see [Connect a chat agent](#connect-a-chat-agent-mcp)).

Press Ctrl-C to stop the service.

## Options

| Option | Default | Purpose |
| --- | --- | --- |
| `--documents PATH` | `DOCUMENT_ROOT` or `test-repository` | The folder to index. The service reads `.md`, `.pdf`, `.csv` and `.xlsx` files in all subfolders |
| `--state-dir PATH` | `STATE_DIR` or `.runtime` | The folder for the index, queue and audit databases |
| `--port 8001` | `8000` | The local port |
| `--upload-workers 4` | `INDEXER_WORKERS` or `2` | The number of upload workers, from 0 to 16 |
| `--no-startup-index` | off | Do not index at start. Use `/admin` to index |

## Where the data is

| File | Contents |
| --- | --- |
| `<state-dir>/index-<id>.sqlite3` | The search index: documents, passages, the FTS5 inverted index, the file inventory, tables, table rows and facts |
| `<state-dir>/index-<id>.lock` | The index lock. One process at a time holds it while it plans and publishes index changes |
| `<state-dir>/queue-<id>.sqlite3` | The upload job queue |
| `<state-dir>/audit.sqlite3` | The audit log |

`<id>` comes from the path of the document folder. Thus two document folders never share an index. You can delete an index file at any time. The service makes it again from the documents.

## Index your own files

```bash
uv run --frozen python -m engineering_search --documents /absolute/path/to/documents --state-dir /absolute/path/to/state
```

The service reads Markdown (UTF-8), PDF with a text layer, CSV (UTF-8) and XLSX files. It reads Markdown pipe tables, CSV files and workbook sheets as tables too, and extracts typed facts from them. It does not follow symbolic links. It does not change or move the documents.

The service detects the type of each file from its content and its extension. For PDF, XLSX, DOCX and JT, the content signature decides. It lists files that it cannot read (for example `.txt`, `.docx`, `.dwg`, `.jt`, or a file whose content does not match its extension) in `/admin` with their type, format version and status, and does not read them.

If the service cannot read or extract a file (for example, a permission error, invalid UTF-8, an encrypted file or a damaged PDF), it does not stop. It skips the file and shows the file in `failed_files` in the index result. The other files are indexed.

A PDF without a text layer (for example, a scan) has the status `NO_TEXT_LAYER`, and a PDF with some empty pages has `INDEXED_PARTIAL`. The service has no OCR, so the text of those pages cannot be found. A workbook formula without a value that Excel cached is left empty, and the file is `INDEXED_PARTIAL`. The index team sees every such file, with the reason and a hint, in the coverage report (`GET /index/coverage`).

The access rules in `engineering_search/access.py` apply to your files too. If no rule matches a path, the whole-repository rule applies, and all three users can read the file.

After you add, change or delete files, select **Reindex documents** in `/admin`. The service reads and hashes every file that has a reader, and extracts only the new and changed files (and files whose reader version changed). There is no automatic file watcher.

## Connect a chat agent (MCP)

The MCP server lets a chat agent search the documents and query their tables. It uses the same search service, index, permissions and audit log as the web page. The chat client starts the server as a local process and talks to it over stdio. The server is not exposed over HTTP.

```bash
uv run --frozen python -m engineering_search.mcp_server --user jp
```

`--user` selects whose permissions apply. Nothing verifies it. In production, the user must come from the sign-in of the MCP client (OAuth), not from a flag.

The MCP server refreshes the index when it starts. The web service and several MCP servers can share one state folder: the index lock (`index-<id>.lock`) lets one process at a time plan and publish index changes, and the others wait.

The repository has project configuration for two clients: `.mcp.json` (Claude Code) and `.pi/mcp.json` (Pi). Both start the server with `uv` as user `jp`. Codex takes the server from `-c mcp_servers.engineering_search.*` overrides on its command line, so no global configuration changes. These three clients were checked by hand. [docs/MCP.md](docs/MCP.md) gives the setup for each client, which questions to ask, and what to report. To check the server without a chat client:

```bash
uv run --frozen python -m scripts.check_mcp
```

The script lists the tools, asks three text questions, and runs one SQL question with a citation. [`tests/test_mcp_stdio.py`](tests/test_mcp_stdio.py) does the same in the test suite.

The server has these tools:

| Tool | Input | Output |
| --- | --- | --- |
| `search_evidence` | `question`, optional `mode` (`auto`, `answer`, `list`), `within` (file IDs of a previous list), `limit` (1 to 50) and `page` | `answer` (one value with its status, or a page of up to 200 documents, with exact sources), what was searched for, and the supporting passages |
| `read_evidence` | `file_id`, optional `page` | All passages of one file, or of one PDF page |
| `describe_schema` | none | The tables that `query_sql` can read, and notes on units and citations |
| `list_tables` | none | The names of those tables |
| `describe_table` | `table` | The columns of one table, with type, meaning and units |
| `query_sql` | `sql` (one `SELECT`, written by the client), optional `limit` (1 to 500) | `columns`, `rows`, `row_count`, `truncated`. Only rows from files the user may read |
| `get_document_evidence` | `file_id`, `table_no`, `row_no` | One table row as read, its line and page, its facts, the file version and the passage that holds it |
| `get_index_coverage` | optional `gaps_limit` | The coverage report. Registered only when `--user` is an index-team user (`maya`) |

The client writes the SQL. The service does not. It runs the statement against a copy of the permitted rows in memory, with one `SELECT` only, a list of allowed tables and functions, a read-only connection, a step budget, a row limit and a length limit. The same API is on the web service: `GET /sql/schema`, `POST /sql` and `GET /evidence/<file>/tables/<n>/rows/<n>`.

A browser cannot talk to an MCP server directly. A chat box on the web page needs a server-side language model that calls the same search function. That is not part of the MVP.

## Run on a remote machine

Copy the repository to the remote machine and run the same commands there:

```bash
uv sync --locked
```

```bash
uv run --frozen python -m engineering_search --documents /srv/engineering-documents --state-dir /srv/engineering-search-state
```

The service listens only on `127.0.0.1`. To use it from your laptop, open an SSH tunnel in a second terminal:

```bash
ssh -N -L 18000:127.0.0.1:8000 your-user@your-host
```

Then open <http://127.0.0.1:18000/search>. The documents, the index and the audit log stay on the remote machine.

SSH controls who can reach the machine. The service itself still uses pretend sign-in. Anyone who can reach it can select Maya.

## Test and package

```bash
uv sync --locked --extra test
```

```bash
uv run --frozen pytest -q
```

The suite has 142 tests and takes about 4 minutes. It includes a real MCP client session over stdio.

```bash
uv run --frozen python -m scripts.evaluate
```

```bash
uv run --frozen python scripts/package_source.py
```

The last command makes `.runtime/engineering-search-mvp.zip`. The ZIP contains only listed source files and `test-repository/`. It does not contain uploads, databases or the virtual environment. The command does not overwrite an existing ZIP.

## Make the test data again

The synthetic files in `test-repository/` come from scripts. To change them, edit the script and run it. Do not edit the output by hand.

The synthetic PDFs:

```bash
uv run --frozen python scripts/make_test_pdfs.py
```

The structured fixtures (`project-harbour/` and `registers/component-register.csv`):

```bash
uv run --frozen python scripts/make_structured_fixtures.py
```

The 120 generated project files come from `scripts/seed_demo.py`. `test-repository/TEST-DATA.txt` describes every folder.

The two FHWA PDFs are real public documents. Do not edit them. `test-repository/public-fhwa/SOURCES.txt` gives their source.
