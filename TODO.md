# Gaps and next work

Updated 2026-10-28. This is an MVP, not the final platform. This document lists what is done, what is missing, and the next work. A checked item is implemented and tested. The [decision records](docs/adr/README.md) give the reasons. [ARCHITECTURE.md](ARCHITECTURE.md#mvp-shortcuts-in-the-code) lists the shortcuts in the code.

## Done

- [x] Index Markdown and simple PDF files (text layer only), page by page. Skip and report files that cannot be read or extracted. (PDFs without text are not reported. See [Known defects](#known-defects-fix-first).)
- [x] Indexer as its own component in `engineering_search/indexing/`, tested alone in `tests/test_indexer.py`. Detect the file type by extension. List every file with its type, and list files without a reader as unsupported without reading them. [ARCHITECTURE.md](ARCHITECTURE.md#the-indexing-line).
- [x] Keep the index in SQLite with an FTS5 inverted index. Extract only new and changed files when the index is updated (every file is still read and hashed). [ADR 0009](docs/adr/0009-sqlite-fts5-index-and-answers.md).
- [x] Change plain-language questions into index queries: stop words, synonyms, prefix search for codes such as S355. Show the user what was searched for.
- [x] Answer one value with the exact sentence or table row, and its file, page, lines and version. Show up to five other documents that also state a value. Say "not found" or "closest match" when the best passages do not state it. (`found` can still be a wrong value. See [Known defects](#known-defects-fix-first).)
- [x] Answer list questions: documents by project, topic, material or status, and by number (with unit conversion). At most 200 documents. Support follow-up questions about the previous list.
- [x] One search service (`service.py`) for the web page, the HTTP API and the MCP server.
- [x] MCP server with `search_evidence` and `read_evidence`, for a chat agent. Install and test guide: [docs/MCP.md](docs/MCP.md).
- [x] Path-based access rules (whole repository, folder, file). Check permissions before answers, counts and pages. (The index lookup limit still applies before the check. See [Known defects](#known-defects-fix-first).) [ADR 0010](docs/adr/0010-path-based-access-rules.md), [ADR 0006](docs/adr/0006-permissions-before-results.md).
- [x] Sign-in screen first. It shows what each demo user can do and which folders each user can read.
- [x] Audit each search before the evidence is returned. Withhold evidence if the audit fails.
- [x] Test repository with 138 files: synthetic Markdown and PDF, 120 generated project files, and two public FHWA PDFs.
- [x] Acceptance tests for the use case, and a test that no user gets information from a file that the user cannot read.
- [x] Scored question set with baseline and current results ([evaluation/README.md](evaluation/README.md)).
- [x] Upload queue with worker threads, index operations page and paged audit log for the index team.

## Gaps against the use case

| Need | What the MVP does | Gap |
| --- | --- | --- |
| Find a load limit, material or approval status | Selects the exact sentence or table row from the best passages | Uses rules on text. It does not know which element a value belongs to. When a document states several parameters, it can return the wrong one with status `found` |
| Filter by project | Matches the project name as a word, mostly in the folder and file name | Fails when the name is not in the path or text, or when a project has more than one name |
| Filter by number | Compares quantities in lines of documents that contain every question word | Not complete: it sees only what word search finds. Small unit list. The quantity can belong to a different element. Signs are ignored |
| 100% confidence in the source | Each answer is exact text with file, page, lines and SHA-256 version. Tests check this against the files | This proves where the text is, not that it answers the question. A correct source can still hold an old or draft value, or a different parameter. When documents disagree, the service shows up to five other documents but does not decide which is current |
| Plain-language questions | Basic keyword search with a small synonym list | Paraphrases are often missed. Better methods need a larger extraction phase, designed from real questions ([README](README.md#this-is-a-basic-method)) |
| Real documents | Works on 138 clean test files that the team made | The formats, versions, structure and quality of the real files are not known. The test scores do not predict real scores ([docs/METRICS.md](docs/METRICS.md)) |
| See the source in context | Shows the exact text, file, page and lines | No viewer. A lead cannot see the table, drawing or stamp around a value |
| Under 10 seconds | About 16 ms per question on 138 files, in the search service | Not measured on a real repository, with many users, or end to end through a chat agent |
| Chat-agent shell | MCP server with the same search service | No chat box on the web page. The MCP user is not verified (see below). Nothing checks that the agent's reply matches the tool result |

## Gaps in file support

- **PDF:** text layer only. No OCR. Tables come out as lines of text. Some characters are lost, for example foot and inch marks.
- **Uploads:** Markdown only.
- **CAD, BIM and other formats:** out of scope for the MVP. Each format and version needs a tested reader. [ADR 0001](docs/adr/0001-mvp-format-scope.md), [ADR 0003](docs/adr/0003-versioned-reader-selection.md), [design/DATA-PROFILE.md](design/DATA-PROFILE.md).
- **File types:** detected from the extension only. A misnamed or damaged file is found only when its reader fails, and the format version is not known.
- **Coverage:** failed files are reported in each index result. Unsupported and unreadable files are listed in `/index/status` with their type, from the last scan. The list is in memory only: there is no stored report. PDFs without a text layer are counted as indexed. [ADR 0005](docs/adr/0005-coverage-and-reader-gaps.md).

## Known defects (fix first)

An independent review on 2026-10-28 found and reproduced these errors. The open items are not fixed, and the current tests pass with them. [ARCHITECTURE.md](ARCHITECTURE.md#known-defects) gives the code location of each one.

- [x] **Skip files that cannot be read.** Fixed with the indexer component: a file read error is reported in `failed_files`, and the other files are indexed. Test: `tests/test_indexer.py`.

- [ ] **Bind the value to the question words.** `found` checks the question words against the whole document. A floor load can be the `found` answer to a roof load question, and a list comparison can cite a floor load for a roof load filter. Withhold ambiguous matches, or mark them as unverified candidates. Add regression tests.
- [ ] **Apply permissions and `within` before the retrieval limit.** The 1,000-passage limit applies first. Permitted results can be lost, and forbidden files can change a user's result. Add a test that adding forbidden files leaves a user's results unchanged.
- [ ] **Read signed quantities.** "-2 kN/m²" is compared as 2 kN/m². Parse the sign, or reject notation that the parser does not support.
- [ ] **Page the document list.** A list returns at most 200 documents, and `page` does not page it. Page the list, or document the limit in the API response.
- [ ] **Coordinate index refreshes across processes.** The web service and the MCP server can publish an older index over a newer one. Use a lock across processes, or reject stale publication.
- [ ] **Report PDFs without text.** Give them a separate "no text" outcome, not "indexed".
- [ ] **Make the leak test check every page.** `tests/test_no_leaks.py` stops after five pages of 50 passages.

## Next (phase 2)

- [ ] **Document and question research.** Profile the real repository: formats, versions, structure, tables, revisions, and where the parameters are. Collect real questions from engineering leads, with the answers and sources that they need. Add them to `evaluation/questions.json`, and keep some back from the developers. Use the results to select the readers, extractors, stores, indexes and viewer. See [design/DATA-PROFILE.md](design/DATA-PROFILE.md).
- [ ] **Project and revision metadata.** Get project, discipline, revision and status from the repository connector. Filter by them exactly ("at Northgate" becomes `project = Northgate`). See [design/EXTRACTION.md](design/EXTRACTION.md) section 2.1.
- [ ] **Facts store for the three parameter families.** Run the pattern rules from `answer.py` at index time. Store load limits, materials and approval statuses as typed records with their sources. Make number filters complete.
- [ ] **Parameter dictionary, version 1.** The 20 to 30 parameters that leads ask about, with their names, other names and units.
- [ ] **Revisions and supersession.** Record which document or revision replaces which. Show the current value first. Get an authority rule from the business for conflicts.
- [ ] **Viewer.** Let a user open the cited source at its page, sheet or element, in the cited version, with the same permissions. Select it with the readers. See [design/DATA-PROFILE.md](design/DATA-PROFILE.md) section 5.
- [ ] **Content-based detection and a versioned reader registry.** The `Detector` and the type-to-reader map exist. Add a detector that reads the file bytes (libmagic) and the format version, and select a tested reader for each format and version. Record the reader and its version for each file. Report files that no reader can read, grouped by format and version. [ADR 0003](docs/adr/0003-versioned-reader-selection.md).
- [ ] **Coverage report.** List unsupported, unreadable and empty files for the index team. [ADR 0005](docs/adr/0005-coverage-and-reader-gaps.md).
- [ ] **PDF upload.**
- [ ] **More tests.** An automated MCP test, scored "not found" and list questions, and browser tests for the web pages. See [evaluation/README.md](evaluation/README.md).

## Later (phase 3 and after)

- [ ] Semantic store (embeddings) with hybrid ranking. Keep it only if the question set shows a gain.
- [ ] Language model extraction with exact-span checks and a review queue.
- [ ] Layout-aware PDF tables. OCR, if the business needs it.
- [ ] CAD and BIM properties through the connectors. DXF, DWG, JT and CATIA stay out of scope until a decision brings them in.
- [ ] A chat box on the web page, through a server-side language model that calls the search service.

## Before use as a shared service

These gaps make the MVP unsafe as a shared service. Each one must be closed first.

- [ ] **Identity.** Sign-in is pretend. Anyone can select any user, including Maya. Use the company identity provider.
- [ ] **MCP identity (security hole).** The MCP server takes the user from the `--user` flag. It does not match the person who uses the chat client to the file permissions. Anyone who can edit the client configuration can read as JP. Run the MCP server as a remote server (Streamable HTTP) behind the company sign-in (OAuth). Take the user from the verified token, never from a flag or a tool argument. [docs/MCP.md](docs/MCP.md#the-security-hole-the-mcp-user-is-not-verified).
- [ ] **Local copies.** With the stdio MCP server and the local web service, the documents are on the tester's computer. A tester can open any file directly, so the permissions are a demonstration only. Keep the documents and the index on a server.
- [ ] **Permissions.** The rules are in `access.py`. Get them from the repository.
- [ ] **Audit.** The SQLite audit log is local, with no protection against changes and no retention rules. Define retention, backup and protection.
- [ ] **Language model data.** A chat agent sends the permitted text to the language model provider. Get approval for the documents that may go to it.
- [ ] **Scale.** One web process per state folder, local queue and workers, one global lock. Measure at the expected size and load. See [design/SCALING.md](design/SCALING.md).
- [ ] **Telemetry.** In memory only. It resets when the service stops.
- [ ] **Installation.** Only macOS is tested. Test each supported operating system.
