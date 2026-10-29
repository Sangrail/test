# Gaps and next work

Updated 2026-10-29. This is an MVP, not the final platform. This document lists what is done, what is missing, and the next work. A checked item is implemented and tested. The [decision records](docs/adr/README.md) give the reasons. [ARCHITECTURE.md](ARCHITECTURE.md) describes the code as it runs.

## Done

### Indexing

- [x] Indexer as its own component in `engineering_search/indexing/`, tested alone. Detect the file type from the content; the extension is a hint. A content that contradicts the extension is `FORMAT_MISMATCH` and is not read. [ADR 0003](docs/adr/0003-versioned-reader-selection.md).
- [x] Reader registry with injected readers, several for each type, each with a manifest (version, format versions, dependencies, capabilities). Readers: Markdown (text and pipe tables), PDF (text layer), CSV, XLSX. The reader and its version are stored for each file; a new reader version re-extracts the file.
- [x] One status for each file, from a fixed list (`INDEXED_FULL`, `INDEXED_PARTIAL`, `NO_TEXT_LAYER`, `NO_READER`, `FORMAT_MISMATCH`, `ENCRYPTED`…), stored with the index. A PDF without text is `NO_TEXT_LAYER`, not indexed. [ADR 0005](docs/adr/0005-coverage-and-reader-gaps.md).
- [x] Coverage report for the index team: by type, format version, status, folder and capability, with the gaps and a hint for each. `GET /index/coverage` and the MCP tool `get_index_coverage`.
- [x] SQLite FTS5 index. Extract only new and changed files (every file is still read and hashed). Publish each document in one transaction. A file lock stops two processes from refreshing the same index at once. [ADR 0009](docs/adr/0009-sqlite-fts5-index-and-answers.md).

### Unstructured path (text)

- [x] Change plain-language questions into index queries: stop words, synonyms, prefix search for codes such as S355. Show the user what was searched for.
- [x] Answer one value with the exact sentence or table row, and its file, page, lines and version. The cited sentence must name the question words (through the sentence, its heading, the file path or the title); if it does not, the status is `unverified`. A floor load is no longer the `found` answer to a roof load question. [ADR 0013](docs/adr/0013-no-answer-before-a-wrong-answer.md).
- [x] Answer list questions by project, topic, material, status and number (with sign and unit conversion). Lists are paged at 200 documents with the total count. Follow-up questions about the previous list.

### Structured path (tables and SQL)

- [x] Tables from CSV, XLSX and Markdown, with the line, page or sheet of each row. Typed facts from table cells by fixed rules: parameter, role (capacity, demand, specification, status, measurement), value, unit, SI value, subject and project. [ADR 0016](docs/adr/0016-structured-facts-and-client-written-sql.md).
- [x] Constrained SQL written by the MCP client: a per-request projection of the files the user may read, one `SELECT`, read-only, an authoriser, a step budget and a row limit. Audited by statement hash, not by rows.
- [x] Row citations: `get_document_evidence` gives the cells, facts, SHA-256 version and verbatim line.
- [x] The vertical slice: "S355 components under 5 kN/m² with citations" gives 7 rows for JP and 6 for Kamal.

### Access, audit and interfaces

- [x] Admission control: each search, read and SQL query is answered within the 8 s budget or refused at once with 503 and a retry time, in the web app and the MCP server. Load test: `scripts/load_test.py`. [ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md).

- [x] One search service for the web page, the HTTP API and the MCP server. [ADR 0011](docs/adr/0011-one-search-service.md).
- [x] Path-based access rules. Permissions apply before the retrieval limit, before answers, counts and pages, and before SQL sees any row. [ADR 0006](docs/adr/0006-permissions-before-results.md).
- [x] Audit each search and SQL query before the evidence is returned. Withhold evidence if the audit fails.
- [x] MCP server over local stdio, verified with Claude Code, Codex and Pi. Project files `.mcp.json` and `.pi/mcp.json`. Install and test guide: [docs/MCP.md](docs/MCP.md).
- [x] Sign-in screen, upload queue with worker threads, index operations page and paged audit log for the index team.

### Tests and data

- [x] Test repository with 148 files: synthetic Markdown, PDF, CSV and XLSX, 120 generated project files, two public FHWA PDFs, a scan with no text, and two `.jt` files that are not valid JT.
- [x] Acceptance tests for the use case. A leak test for every user, mode and format. Binding, SQL safety and permission tests, and an MCP test over stdio with a real client session.
- [x] Scored question set with baseline and current results ([evaluation/README.md](evaluation/README.md)).
- [x] Gold set of 13 NL-to-SQL questions, each with a trap, proven against the extraction by `tests/test_sql_questions.py`. The live-client harness is not built.

## Gaps against the use case

| Need | What the MVP does | Gap |
| --- | --- | --- |
| Find a load limit, material or approval status | Tables: typed facts and SQL. Prose: the exact sentence, bound to the question words | Facts come from tables only. A value stated only in a sentence is found by text search, and binding is a word check: a sentence that names the subject can still state a different parameter |
| Filter by number | SQL over typed facts in SI units, complete for tables. Text lists compare quantities in bound sentences | Text lists see only what word search finds. Small unit and parameter lists. New column kinds get role `unknown` |
| Filter by project | Facts take the project from a project column or the folder. Text search matches the project name as a word | Fails when the project is in neither, or has more than one name |
| 100% confidence in the source | Each answer or row has file, page or sheet, lines and SHA-256 version. Tests check this against the files | This proves where the value is, not that it is current. When documents disagree (B-104 is in two files), nothing decides which one wins |
| Plain-language questions | Text: keyword search with a small synonym list. Tables: the chat agent writes SQL | Paraphrases are often missed by text search. The SQL can be safe but wrong: nothing checks that it asks for the right thing |
| Real documents | Works on 148 clean test files that the team made | The formats, versions, structure and quality of the real files are not known. The test scores do not predict real scores ([docs/METRICS.md](docs/METRICS.md)) |
| See the source in context | Shows the exact text or row, file, page or sheet, and lines | No viewer. A lead cannot see the table, drawing or stamp around a value |
| Under 10 seconds | About 80 ms median per question on 148 files. Admission control answers within 8 s or refuses at once with a retry time ([ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md)) | One process answers about 10 requests a second: under load most users are told to retry. The SQL projection is copied for each request (3 s at a million facts). Not measured on a real repository or end to end through a chat agent |
| Chat-agent shell | MCP server with the same service, verified with three clients | The MCP user is not verified (see below). Nothing checks that the agent's reply matches the tool result |

## Gaps in file support

- **PDF:** text layer only. No OCR. Tables in PDFs come out as lines of text, not as tables, so they give no facts.
- **XLSX:** a formula with no cached value is left empty and the file is `INDEXED_PARTIAL`. Merged headers and hidden sheets are not handled specially.
- **Uploads:** Markdown only.
- **Word, CAD, BIM and other formats:** not read. Scans and CAD files are listed in the coverage report as gaps. The JT probe reads the version header only. [ADR 0001](docs/adr/0001-mvp-format-scope.md), [design/DATA-PROFILE.md](design/DATA-PROFILE.md).

## Known limits (fix or decide)

- [ ] **Facts from prose.** Values in sentences are not facts. Decide from real questions whether to extract them, and how to prove each one against its exact span.
- [ ] **Duplicates across files.** The same component in two files (B-104 in the schedule and the register) gives two rows. Decide which source wins, with a rule from the business.
- [ ] **Document title heuristic.** The first passage counts as the title only if it starts in the first three lines. Replace it with the reader's own title when the readers give one.
- [ ] **Evaluation ranking.** Success@1 fell from 0.94 to 0.88 when the structured fixtures were added: schedule rows with "roof … load" in their headers now outrank one expected passage (Q01, Q12). Every scored answer is still correct. Review the ranking against real questions before any tuning ([evaluation/README.md](evaluation/README.md)).
- [ ] **Components that are not components.** Key-value tables put their heading in `subject`, so the `components` view holds 121 "Roof load" rows from the generated files next to B-104 and R-310. A question about "components above 5 kN/m²" gets them unless the SQL filters by project or grade. Decide whether `components` should hold only rows with a component identifier.
- [ ] **SQL parameters.** `query_sql` takes no bound parameters. Values are written into the SQL.
- [ ] **SQL parser.** Safety rests on SQLite's authoriser and `query_only`, checked by bypass tests. A parser allowlist would give clearer errors.

## Next (phase 2)

- [ ] **Evaluate the design records database** ([ADR 0021](docs/adr/0021-design-records-in-one-database.md)) after a few real changes: is editing prose in SQLite workable, or should the prose move to files that the database references? Should the MCP server get write tools? Known weaknesses: no history (constraints and decisions are updated in place, with no active or displaced versions), a binary source that does not merge, standing typed by hand rather than derived from tests, no features table. Decide the source of truth (SQLite, or text files with SQLite as an index), then add append-only versions and links from decisions to constraint versions ([design/records/README.md](design/records/README.md#weaknesses-and-what-comes-next)).

- [ ] **Document and question research.** Profile the real repository: formats, versions, structure, tables, revisions, and where the parameters are. Collect real questions from engineering leads, with the answers and sources that they need. Add them to `evaluation/questions.json`, and keep some back from the developers. See [design/DATA-PROFILE.md](design/DATA-PROFILE.md).
- [ ] **Parameter dictionary, version 1.** The 20 to 30 parameters that leads ask about, with their names, other names and units. Extend the fact rules from it.
- [ ] **Project and revision metadata.** Get project, discipline, revision and status from the repository connector. See [design/EXTRACTION.md](design/EXTRACTION.md).
- [ ] **Revisions and supersession.** Record which document or revision replaces which. Show the current value first.
- [ ] **PDF tables.** Layout-aware table extraction, so PDF schedules give facts.
- [ ] **Viewer.** Open the cited source at its page, sheet or row, in the cited version, with the same permissions.
- [ ] **PDF, CSV and XLSX upload.**
- [ ] **NL-to-SQL evaluation harness.** An opt-in MCP trace and a runner that asks Claude Code, Codex and Pi each question in `evaluation/sql_questions.json`, scores execution accuracy, trap pass rate and reply fidelity, and saves a baseline with the client and model versions ([ADR 0019](docs/adr/0019-evaluate-retrieval-and-nl-to-sql.md)).
- [ ] **Retrieval evaluation, extended.** Not-found, list, paraphrase and status-scored questions; real questions from leads, a third held back.
- [ ] **Concurrent reads.** One read connection per thread with snapshot reads, no global lock for searches ([ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md)).
- [ ] **SQL without a copy per request.** Cache projections by permission set and index version, or enforce permissions in a server database; make `components` an indexed table; scale the step budget with the data.
- [ ] **More tests.** Browser tests for the web pages.

## Later (phase 3 and after)

- [ ] Remote MCP server over Streamable HTTP, behind company sign-in (see below).
- [ ] ChatGPT and GitHub Copilot as MCP clients. Not tested.
- [ ] A structured path on the web page: a client-planned query through an authenticated API. The search bar does not plan SQL today.
- [ ] Semantic store (embeddings) with hybrid ranking. Keep it only if the question set shows a gain.
- [ ] Language model extraction with exact-span checks and a review queue.
- [ ] OCR, if the business needs it. CAD and BIM properties through the connectors.

## Before use as a shared service

These gaps make the MVP unsafe as a shared service. Each one must be closed first.

- [ ] **Identity.** Sign-in is pretend. Anyone can select any user, including Maya. Use the company identity provider.
- [ ] **MCP identity (security hole).** The MCP server takes the user from the `--user` flag. It does not match the person who uses the chat client to the file permissions. Anyone who can edit the client configuration can read as JP. Run the MCP server as a remote server (Streamable HTTP) behind the company sign-in (OAuth). Take the user from the verified token, never from a flag or a tool argument. [docs/MCP.md](docs/MCP.md#the-security-hole-the-mcp-user-is-not-verified).
- [ ] **Local copies.** With the stdio MCP server and the local web service, the documents are on the tester's computer. A tester can open any file directly, so the permissions are a demonstration only. Keep the documents and the index on a server.
- [ ] **Permissions.** The rules are in `access.py`. Get them from the repository.
- [ ] **Audit.** The SQLite audit log is local, with no protection against changes and no retention rules. Define retention, backup and protection.
- [ ] **Language model data.** A chat agent sends the permitted text and rows to the language model provider. Get approval for the documents that may go to it.
- [ ] **Scale.** One process answers about 10 requests a second; admission control refuses the rest. Several worker processes, a shared queue, and load tests at the expected size and concurrency in CI. See [ADR 0018](docs/adr/0018-admission-control-and-the-time-budget.md), [design/SCALING.md](design/SCALING.md) and [docs/README.md](docs/README.md#making-it-available-to-an-organisation).
- [ ] **Telemetry.** In memory only. It resets when the service stops.
- [ ] **Installation.** Only macOS is tested. Test each supported operating system.
