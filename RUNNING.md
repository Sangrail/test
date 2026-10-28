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
2. It reads the new and changed files in `test-repository/`.
3. It starts two upload workers.
4. It starts the web server on `127.0.0.1:8000`.

Open <http://127.0.0.1:8000/search>. The page shows only the sign-in screen until you select a demo user. The screen says what each user can do and what to try. For example:

1. Sign in as JP. Ask "Has building control approved the Northgate warehouse?".
2. Ask "Do we have any documents in Northgate?". Select "Ask the next question about these documents only", then ask "Of those documents, which mention compliance?".
3. Ask "Which documents have a roof load greater than 5 kN/m²?".
4. Sign out, sign in as Kamal, and ask the first question again. Kamal cannot read the Northgate file. Thus the answer is "not found", or a closest match that the page marks as not an answer.
5. Sign in as Maya to open `/admin` (index operations) and `/audit` (audit log).

Press Ctrl-C to stop the service.

## Options

| Option | Default | Purpose |
| --- | --- | --- |
| `--documents PATH` | `DOCUMENT_ROOT` or `test-repository` | The folder to index. The service reads `.md` and `.pdf` files in all subfolders |
| `--state-dir PATH` | `STATE_DIR` or `.runtime` | The folder for the index, queue and audit databases |
| `--port 8001` | `8000` | The local port |
| `--upload-workers 4` | `INDEXER_WORKERS` or `2` | The number of upload workers, from 0 to 16 |
| `--no-startup-index` | off | Do not index at start. Use `/admin` to index |

## Where the data is

| File | Contents |
| --- | --- |
| `<state-dir>/index-<id>.sqlite3` | The search index: documents, passages and the FTS5 inverted index |
| `<state-dir>/queue-<id>.sqlite3` | The upload job queue |
| `<state-dir>/audit.sqlite3` | The audit log |

`<id>` comes from the path of the document folder. Thus two document folders never share an index. You can delete an index file at any time. The service makes it again from the documents.

## Index your own files

```bash
uv run --frozen python -m engineering_search --documents /absolute/path/to/documents --state-dir /absolute/path/to/state
```

The service reads `.md` files (UTF-8) and `.pdf` files. It does not follow symbolic links. It does not change or move the documents.

If the service cannot read a file, it does not stop. It skips the file and shows the file in `failed_files` in the index result. The other files are indexed.

The access rules in `engineering_search/access.py` apply to your files too. If no rule matches a path, the whole-repository rule applies, and all three users can read the file.

After you add, change or delete files, select **Reindex documents** in `/admin`. The service reads only the changed files. There is no automatic file watcher.

## Connect a chat agent (MCP)

The MCP server lets a chat agent search the documents. It uses the same search function, index, permissions and audit log as the web page. The chat client starts the server as a local process and talks to it over stdio.

```bash
uv run --frozen python -m engineering_search.mcp_server --user jp
```

`--user` selects whose permissions apply. In production, the user must come from the sign-in of the MCP client (OAuth), not from a flag.

[docs/MCP.md](docs/MCP.md) tells you how to connect Claude Code or Claude Desktop, which questions to ask, and what to report. To check the server without a chat client:

```bash
uv run --frozen python -m scripts.check_mcp
```

The server has two tools:

| Tool | Input | Output |
| --- | --- | --- |
| `search_evidence` | `question`, optional `mode` (`auto`, `answer`, `list`), `within` (file IDs of a previous list), `limit` (1 to 50) and `page` | `answer` (one value, or a list of documents, with exact sources), what was searched for, and the supporting passages |
| `read_evidence` | `file_id`, optional `page` | All passages of one file, or of one PDF page |

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

```bash
uv run --frozen python -m scripts.evaluate
```

```bash
uv run --frozen python scripts/package_source.py
```

The last command makes `.runtime/engineering-search-mvp.zip`. The ZIP contains only listed source files and `test-repository/`. It does not contain uploads, databases or the virtual environment. The command does not overwrite an existing ZIP.

## Make the test PDFs again

The synthetic PDFs in `test-repository/` come from a script. To change them, edit the script and run it:

```bash
uv run --frozen python scripts/make_test_pdfs.py
```

The two FHWA PDFs are real public documents. Do not edit them. `test-repository/public-fhwa/SOURCES.txt` gives their source.
