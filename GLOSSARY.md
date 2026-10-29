# Engineering evidence search

Terms used to describe source evidence, file compatibility and search coverage.

## Language

**Source version**:
A particular content revision of a document. It is distinct from the version of the file format used to encode that content. The service records it as the SHA-256 of the file.
_Avoid_: File version without qualification

**Format version**:
The revision of a file format in which a document is encoded. A document's age alone does not establish its format version or readability. The detector reads it from the content where the format states one, for example `%PDF-1.7` or the JT header.

**File type**:
The name that a detector gives to a file, for example `markdown`, `pdf`, `excel` or `jt`. A file type without a reader is not supported.

**Detector**:
The part of the indexer that names the file type and format version of each file. The default `ContentDetector` treats the extension as a hint and lets the content signature decide for PDF, XLSX, DOCX and JT.

**Format mismatch**:
A file whose content does not have the signature of the type that its extension claims, for example a text note saved as `.jt`. Its status is `FORMAT_MISMATCH`. A file that starts like its type but has a broken header is `INVALID_HEADER`.

**File status**:
The outcome of one file in a scan or a refresh, for example `INDEXED_FULL`, `INDEXED_PARTIAL`, `NO_TEXT_LAYER`, `NO_READER` or `READ_ERROR`. `engineering_search/indexing/status.py` lists them all. Every status other than `INDEXED_FULL` is a coverage gap.

**Inventory**:
Every file found by one scan, with its file type, format version, status, reader and warnings. It is stored with the index.

**Indexer**:
The component that scans the document folder, detects file types, chooses readers, reads the files, extracts facts from their tables, and plans the changes to the search index. It is in `engineering_search/indexing/`. It does not write the index.

**Reader**:
A concrete implementation that interprets a file format and produces passages and tables. Its supported format versions must be established through verification. The MVP has readers for Markdown, text-layer PDF, CSV and XLSX.

**Reader manifest**:
What a reader declares: its ID and version, the file types and format versions it is tested with, its capabilities (text, tables, metadata, geometry) and the packages it needs.

**Reader version**:
A particular release of a reader. Different reader versions can interpret the same source differently. A file is extracted again when its reader version changes.

**Reader registry**:
The one list of readers (`default_registry()`). For each file it chooses the first reader that fits the type, the format version and the installed packages, or says why none fits: `NO_READER`, `UNSUPPORTED_VERSION` or `DEPENDENCY_MISSING`.

**Reader selection**:
The recorded choice of reader and reader version used to interpret a particular source version. The inventory records it as `reader_id@reader_version`.

**Evidence passage**:
Content extracted from an identified source version, with a location that allows its origin to be checked. Provenance does not establish engineering correctness or approval.

**Search hit**:
An evidence passage that matches a query. Several hits can come from one document.
_Avoid_: Search result database when referring to the stored evidence corpus

**Coverage gap**:
A discovered document or part of a document that cannot currently contribute searchable evidence, with an identified reason where possible. The coverage report lists each gap with its status and a hint.

**Coverage report**:
The files of the last refresh, counted by file type and format version, by status, by top folder and by capability, with each gap. It names files, so only the index team may see it.

**Excluded match**:
A matching passage or row withheld because the user's permissions do not allow access. It is distinct from an explicit attempt to open a forbidden file.

**Inverted index**:
An index that maps each word to the passages that contain it. A search looks up the words. It does not read the documents. The MVP uses SQLite FTS5.

**Query plan**:
The words that the service searches for after it removes common words, adds synonyms and makes codes into prefix searches. The response shows it as "Searched for".

**Candidate limit**:
The most passages that one text query ranks (1,000). The permitted files are applied inside the index query, before this limit.

**Answer**:
One sentence or table row, copied exactly from a passage, that the service selects as stating the value that a question asks for. It has the source of that passage and a status.
_Avoid_: Generated answer. The service does not write answer text.

**Bound word**:
A question word that is in the answer sentence, its passage heading, the file path or the document title. Words elsewhere in the document are not bound: they do not describe the value.

**Answer status**:
`found` (every question word is bound), `unverified` (the document has every question word, but some are not bound: `unbound_words`), `partial` (some question words are not in the document: `missing_words`) or `not_found`.

**Document list**:
The answer to a "which documents" question: one entry for each readable document that contains every question word, with the line that shows why. With a number comparison, every question word must be bound to that line. Lists are paged at 200 documents.

**Access rule**:
A path (the whole repository, a folder or a file) and the users who may read it. The most specific rule for a file applies.

**Table**:
Rows and columns read from a document: a Markdown pipe table, a CSV file or a workbook sheet. Each row keeps its line (or sheet row) and page (or sheet number).

**Fact**:
A typed value from one table cell, extracted at index time by fixed rules: subject, parameter, role, the value as written, the number with its sign, the unit, the SI value, the dimension and the project, with the file, table, row and line. Facts come only from tables, never from free text.

**Role**:
What a fact's value is: `capacity` (an allowable value), `demand` (an imposed or applied value), `specification` (a material grade), `status` (an approval status), `measurement` (for example a settlement), or `unknown`. A capacity is never compared with a demand.

**Projection**:
A read-only SQLite database in memory, built for one SQL request, with only the structured rows of the files that the user may read.

**Constrained SQL**:
One `SELECT` statement that the MCP client writes and the service runs against a projection, with an allowlist of tables and functions, a read-only connection, a step budget, a row limit and a length limit. The service does not write the SQL and does not check that it asks the right question.

**Search service**:
The one component that searches, runs SQL, reads files, checks permissions and writes the audit log (`SearchService` in `service.py`). The web app and the MCP server both call it.

**Index lock**:
A lock file (`index-<id>.lock` in the state folder) that lets one process at a time plan and publish changes to a shared index.

**MCP server**:
A process that gives a chat client (Claude Code, Codex, Pi) the tools `search_evidence`, `read_evidence`, `describe_schema`, `list_tables`, `describe_table`, `query_sql` and `get_document_evidence` over the Model Context Protocol, on local stdio. It calls the search service. See docs/MCP.md.
