# Engineering evidence search

Terms used to describe source evidence, file compatibility and search coverage.

## Language

**Source version**:
A particular content revision of a document. It is distinct from the version of the file format used to encode that content.
_Avoid_: File version without qualification

**Format version**:
The revision of a file format in which a document is encoded. A document's age alone does not establish its format version or readability.

**Reader**:
A concrete implementation that interprets a file format and produces content suitable for indexing. Its supported format versions must be established through verification.

**Reader version**:
A particular release of a reader. Different reader versions can interpret the same source differently.

**Reader selection**:
The recorded choice of reader and reader version used to interpret a particular source version.

**Evidence passage**:
Content extracted from an identified source version, with a location that allows its origin to be checked. Provenance does not establish engineering correctness or approval.

**Search hit**:
An evidence passage that matches a query. Several hits can come from one document.
_Avoid_: Search result database when referring to the stored evidence corpus

**Coverage gap**:
A discovered document or part of a document that cannot currently contribute searchable evidence, with an identified reason where possible.

**Excluded match**:
A matching passage withheld because the user's permissions do not allow access. It is distinct from an explicit attempt to open a forbidden file.

**Inverted index**:
An index that maps each word to the passages that contain it. A search looks up the words. It does not read the documents. The MVP uses SQLite FTS5.

**Query plan**:
The words that the service searches for after it removes common words, adds synonyms and makes codes into prefix searches. The response shows it as "Searched for".

**Answer**:
One sentence or table row, copied exactly from a passage, that the service selects as stating the value that a question asks for. It has the source of that passage. The selection is a word match: the service does not verify that the value belongs to the asked element.
_Avoid_: Generated answer. The service does not write answer text.

**Document list**:
The answer to a "which documents" question: one entry for each readable document that contains every question word, with the line that shows why. At most 200 entries are returned.

**Access rule**:
A path (the whole repository, a folder or a file) and the users who may read it. The most specific rule for a file applies.

**Fact**:
A typed record of an engineering property (parameter, subject, value, unit, status) with its exact source span. Facts are a later phase. See design/EXTRACTION.md.

**Search service**:
The one component that searches, reads files, checks permissions and writes the audit log (`SearchService` in `service.py`). The web app and the MCP server both call it.

**MCP server**:
A process that gives a chat agent the tools `search_evidence` and `read_evidence` over the Model Context Protocol. It calls the search service. See docs/MCP.md.
