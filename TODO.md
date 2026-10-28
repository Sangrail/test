# Gaps and next work

Updated 2026-10-28. This is an MVP, not the final platform. This document lists what is done, what is missing, and the next work. A checked item is implemented and tested. The [decision records](docs/adr/README.md) give the reasons. [ARCHITECTURE.md](ARCHITECTURE.md#mvp-shortcuts-in-the-code) lists the shortcuts in the code.

## Done

- [x] Index Markdown and simple PDF files (text layer only), page by page. Skip and report files that cannot be read.
- [x] Keep the index in SQLite with an FTS5 inverted index. Read only new and changed files when the index is updated. [ADR 0009](docs/adr/0009-sqlite-fts5-index-and-answers.md).
- [x] Change plain-language questions into index queries: stop words, synonyms, prefix search for codes such as S355. Show the user what was searched for.
- [x] Answer one value with the exact sentence or table row, and its file, page, lines and version. Show other documents that also state a value. Say "not found" or "closest match" when no readable document states it.
- [x] Answer list questions: documents by project, topic, material or status, and by number (with unit conversion). Support follow-up questions about the previous list.
- [x] One search service (`service.py`) for the web page, the HTTP API and the MCP server.
- [x] MCP server with `search_evidence` and `read_evidence`, for a chat agent. Install and test guide: [docs/MCP.md](docs/MCP.md).
- [x] Path-based access rules (whole repository, folder, file). Check permissions before answers, counts and pages. [ADR 0010](docs/adr/0010-path-based-access-rules.md), [ADR 0006](docs/adr/0006-permissions-before-results.md).
- [x] Sign-in screen first. It shows what each demo user can do and which folders each user can read.
- [x] Audit each search before the evidence is returned. Withhold evidence if the audit fails.
- [x] Test repository with 138 files: synthetic Markdown and PDF, 120 generated project files, and two public FHWA PDFs.
- [x] Acceptance tests for the use case, and a test that no user gets information from a file that the user cannot read.
- [x] Scored question set with baseline and current results ([evaluation/README.md](evaluation/README.md)).
- [x] Upload queue with worker threads, index operations page and paged audit log for the index team.

## Gaps against the use case

| Need | What the MVP does | Gap |
| --- | --- | --- |
| Find a load limit, material or approval status | Selects the exact sentence or table row from the best passages | Uses rules on text. It does not know which element a value belongs to |
| Filter by project | Matches the project name as a word, mostly in the folder and file name | Fails when the name is not in the path or text, or when a project has more than one name |
| Filter by number | Compares quantities in lines of documents that contain every question word | Not complete: it sees only what word search finds. Small unit list |
| 100% confidence in the source | Each answer is exact text with file, page, lines and SHA-256 version. Tests check this against the files | A correct source can still hold an old or draft value. When documents disagree, the service shows all values but does not decide which is current |
| Plain-language questions | Basic keyword search with a small synonym list | Paraphrases are often missed. Better methods need a larger extraction phase, designed from real questions ([README](README.md#this-is-a-basic-method)) |
| Real documents | Works on 138 clean test files that the team made | The formats, versions, structure and quality of the real files are not known. The test scores do not predict real scores ([docs/METRICS.md](docs/METRICS.md)) |
| See the source in context | Shows the exact text, file, page and lines | No viewer. A lead cannot see the table, drawing or stamp around a value |
| Under 10 seconds | About 16 ms per question on 138 files | Not measured on a real repository or with many users |
| Chat-agent shell | MCP server with the same search service | No chat box on the web page. The MCP user is not verified (see below) |

## Gaps in file support

- **PDF:** text layer only. No OCR. Tables come out as lines of text. Some characters are lost, for example foot and inch marks.
- **Uploads:** Markdown only.
- **CAD, BIM and other formats:** out of scope for the MVP. Each format and version needs a tested reader. [ADR 0001](docs/adr/0001-mvp-format-scope.md), [ADR 0003](docs/adr/0003-versioned-reader-selection.md), [design/DATA-PROFILE.md](design/DATA-PROFILE.md).
- **Coverage:** failed files are reported in each index result, but there is no stored report of unsupported or unreadable files. [ADR 0005](docs/adr/0005-coverage-and-reader-gaps.md).

## Next (phase 2)

- [ ] **Document and question research.** Profile the real repository: formats, versions, structure, tables, revisions, and where the parameters are. Collect real questions from engineering leads, with the answers and sources that they need. Add them to `evaluation/questions.json`, and keep some back from the developers. Use the results to select the readers, extractors, stores, indexes and viewer. See [design/DATA-PROFILE.md](design/DATA-PROFILE.md).
- [ ] **Project and revision metadata.** Get project, discipline, revision and status from the repository connector. Filter by them exactly ("at Northgate" becomes `project = Northgate`). See [design/EXTRACTION.md](design/EXTRACTION.md) section 2.1.
- [ ] **Facts store for the three parameter families.** Run the pattern rules from `answer.py` at index time. Store load limits, materials and approval statuses as typed records with their sources. Make number filters complete.
- [ ] **Parameter dictionary, version 1.** The 20 to 30 parameters that leads ask about, with their names, other names and units.
- [ ] **Revisions and supersession.** Record which document or revision replaces which. Show the current value first. Get an authority rule from the business for conflicts.
- [ ] **Viewer.** Let a user open the cited source at its page, sheet or element, in the cited version, with the same permissions. Select it with the readers. See [design/DATA-PROFILE.md](design/DATA-PROFILE.md) section 5.
- [ ] **Reader registry.** Detect the format and version of each file from its content, and select a tested reader. Record the reader and its version for each file. Report files that no reader can read, grouped by format and version. [ADR 0003](docs/adr/0003-versioned-reader-selection.md).
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
