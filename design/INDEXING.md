# Indexing structured and unstructured data

This page says exactly what the MVP does when it indexes a file: what it extracts, where each piece is stored, and how each piece is used when a question is asked. It describes the code as it runs ([`engineering_search/indexing/`](../engineering_search/indexing/), [`store.py`](../engineering_search/store.py)). [ARCHITECTURE.md](../ARCHITECTURE.md#the-indexing-line) has the module detail; [EXTRACTION.md](EXTRACTION.md) says how extraction must grow after the MVP.

![How one file is indexed](indexing.svg)

Source: [indexing.svg](indexing.svg), drawn by hand. The hatched boxes are stand-ins for the company's connectors ([C3](../docs/constraints/constraints.md#c3), [ADR 0001](../docs/adr/0001-prove-the-use-case-with-stand-in-readers.md)).

## In short

- **Every file takes the same line.** Scan, detect the type, choose a reader, hash, read, extract facts, publish. There is no separate pipeline for structured files.
- **A reader returns two kinds of output from one file.** *Passages* are prose with its location. *Tables* are rows and columns, each row with its line. A file can return either or both.
- **Passages go to a full-text index.** They are found by their words. Nothing is extracted from prose at index time; the rules that pick a value from a sentence run when the question is asked.
- **Tables go to fixed tables, and their cells become facts.** At index time, fixed rules turn each cell into a typed fact (parameter, role, value, unit, SI value). These are queried with SQL.
- **Every table row is also a passage.** A row can be found by its words and by SQL.
- **Every piece keeps its source.** Each passage, row and fact names its file, its line or lines, its page or sheet, and the file's content fingerprint (the SHA-256 of its bytes).
- **One transaction publishes a file.** Its old rows are deleted and its new rows are written together, or nothing changes.
- **Permissions are not in the index.** Every file is indexed. Each request applies the user's permissions before ranking, limits and counts ([ADR 0004](../docs/adr/0004-permissions-before-ranking-limits-and-counts.md)).

## What "structured" and "unstructured" mean here

| Term | In this MVP | Examples in the test repository |
| --- | --- | --- |
| **Unstructured** | Text whose rows and columns, if any, the reader cannot see. It becomes passages | Markdown paragraphs, the text layer of a PDF (including any table in it), the notes on a DXF drawing |
| **Structured** | Data that the reader sees as a table: a header row and data rows. It becomes a table, its rows and its facts | A CSV file, an XLSX sheet, a Markdown pipe table, the title-block attributes of a DXF drawing |
| **Mixed** | One file with both. Each part takes its own lane, and table rows are also kept as passages | A Markdown specification with a table under one heading and prose under another; a DXF drawing with notes and a title block |

The decision is the reader's, by format. A table in a PDF is unstructured to the MVP: pypdf returns its cells as lines of text. A layout-aware PDF reader is not built ([G8](../docs/constraints/gaps.md#g8)).

## 1. The common line

[`Indexer.plan`](../engineering_search/indexing/indexer.py) runs these steps for every regular file below the document folder. Hidden files and symbolic links are skipped.

| Step | What it does | Extracts | Code |
| --- | --- | --- | --- |
| Scan | Lists every file. The path relative to the folder is the file ID | File ID, size | `Indexer.paths` |
| Detect | Reads the extension and at most the first 512 bytes. The content decides when the format has a signature (`%PDF-1.7`, a ZIP with `xl/workbook.xml`, a JT header, a DXF `$ACADVER`); otherwise the extension decides | File type, format version, or `FORMAT_MISMATCH` / `INVALID_HEADER` | [`detect.py`](../engineering_search/indexing/detect.py) |
| Choose a reader | The registry picks the first reader whose manifest reads that type and format version and whose packages are installed. If none fits, the file is listed with a status (`NO_READER`, `UNSUPPORTED_VERSION`, `DEPENDENCY_MISSING`, `UNSUPPORTED_FORMAT`) and is not indexed | Reader ID and version | [`readers/registry.py`](../engineering_search/indexing/readers/registry.py) |
| Hash | Reads the whole file and takes the SHA-256 of its bytes: the content fingerprint, stored as `source_version`. A file is hashed only if a reader fits | Content fingerprint | `Indexer._classify` |
| Decide | The file is read again only if it is new, its fingerprint changed, its reader or reader version changed, or its last status is not known. Otherwise the indexed rows stay | | `Indexer.plan` |
| Read | The reader turns the bytes into an `Extraction`: passages, tables, a status and warnings. A reader that cannot read the file raises `MALFORMED`, `ENCRYPTED` or `UNSUPPORTED_VERSION`; any other error is `READER_CRASH`. One bad file never stops the others | Passages, tables, status, warnings | [`readers/`](../engineering_search/indexing/readers/) |
| Facts | Fixed rules turn table cells into typed facts | Facts | [`facts.py`](../engineering_search/indexing/facts.py) |
| Publish | The service writes the plan in one transaction, under a file lock that other processes see | | `SearchService.reindex`, `SQLiteSearchIndex.apply` |

The indexer only reads. It never writes the index and does not import the store; the service publishes its plan ([ARCHITECTURE.md](../ARCHITECTURE.md#two-lines-indexing-and-searching)).

## 2. Metadata: what the MVP knows about each file

The brief says connectors extract metadata ([C3](../docs/constraints/constraints.md#c3)). The MVP has no connector, so it knows only what the file system and the bytes tell it.

| Metadata | Extracted by | Stored in | Used for |
| --- | --- | --- | --- |
| File ID (the path) | Scan | Every table (`file_id`) | Citations; its words are indexed with every passage, so "northgate" matches a file in `project-northgate/` |
| File type and format version | Detector | `files` (the inventory) | Choosing a reader; the coverage report |
| Size, status, warnings | Scan and reader | `files` | The coverage report and the index operations page |
| Reader ID and version | Registry | `files` | Re-reading a file when its reader changes |
| Content fingerprint (SHA-256) | Indexer | `documents.source_version`, and on every passage | Detecting a change; every citation carries it |
| Project | Not stored. The SQL projection derives it when a request runs: from a top folder named `project-<name>`, or from a `Project` column of a table row ([K15](../docs/constraints/clarifications.md#k15)) | `documents.project` and `facts.project` in the projection | Filtering by project in SQL |
| Drawing number, revision, approval status, title | The DXF reader, from the title block | As a table, its rows and its facts (section 4) | Search and SQL, like any table |
| Who may read the file | Not extracted. [`access.py`](../engineering_search/access.py) holds path rules, a stand-in for the repository's own permissions ([G1](../docs/constraints/gaps.md#g1)) | Not in the index | Each request |

Not extracted: author, dates, revision fields of the repository, PDF document information, Markdown front matter. A real connector would supply them ([EXTRACTION.md](EXTRACTION.md#21-file-metadata)).

## 3. The unstructured lane: passages

**What a passage is.** A run of lines from one file. It holds the file ID, the content fingerprint, a heading, the first and last line, the page (or sheet), and the exact text. The heading line is not part of the text. Line numbers are 1-based; for a PDF they count the lines of that page's text.

**How each reader makes passages.**

| Reader | Splits at | Heading |
| --- | --- | --- |
| `markdown-text@2` | Headings and blank lines, never inside a code fence | The nearest `#` heading above |
| `pdf-text-pypdf@1` | Numbered headings ("3.1 Roof load limit") and blank lines, at most 15 lines a passage, page by page | The nearest numbered heading on the page |
| `csv-table@2` | Each data row is one passage, the row as written. A row with a quoted line break cites all its lines | The header row |
| `xlsx-openpyxl@1` | Each data row is one passage, its cells joined with ` \| `. The page is the sheet number and the line is the sheet row | The sheet name and the header row |
| `dxf-text@1` | Each TEXT or MTEXT note is one passage. Each title-block attribute is one passage `TAG \| value` | The layer of the note, or the name of the title-block table |

**Where passages are stored.**

- `passages` holds the verbatim text and its location. This is what an answer quotes.
- `passages_fts` is a SQLite FTS5 inverted index over three columns: the heading, the text, and the words of the file path. It uses the `porter unicode61` tokenizer, so "loads" matches "load".

**How passages are used.** `search_evidence` plans the question into words, finds every file that contains one, applies the user's permissions, then ranks only the permitted passages that match. Ranking puts passages with more of the question's words first, then BM25 with the weights 3 (heading), 1 (text) and 0.5 (path). Fixed pattern rules then pick the sentence or table row that states a value, and quote it ([`answer.py`](../engineering_search/answer.py)). These rules run when the question is asked. Nothing is extracted from prose at index time.

**What this lane does not do.** It makes no facts from prose: a value that only a sentence states is found by its words, not by SQL. No OCR, so a scanned PDF is `NO_TEXT_LAYER`. No semantic (embedding) store ([O1](../docs/constraints/gaps.md#o1), [ADR 0002](../docs/adr/0002-structured-tables-and-full-text-search.md)).

## 4. The structured lane: tables, rows and facts

**What a table is.** A table number within its file, a name, the column headers, and the rows. Each row holds its cells as read, its line and its page or sheet.

| Reader | Tables it returns | Name |
| --- | --- | --- |
| `markdown-text@2` | Each pipe table (a `\| a \| b \|` row with a `\|---\|` line under it), outside code fences. Each row cites its own line | The nearest heading above |
| `csv-table@2` | The file as one table; the first non-empty row is the header. A row with too few or too many cells is padded or cut, and the file is `INDEXED_PARTIAL` | The file name |
| `xlsx-openpyxl@1` | One table per sheet; the first non-empty row is the header. Cell values are the values Excel cached. A formula with no cached value is left empty and named in a warning | The sheet name |
| `dxf-text@1` | Each block reference with attributes, in the ENTITIES section, as a two-column Property/Value table. The property is the tag with spaces for underscores. Each row cites the line of its value | The drawing number and revision, when the title block has them |
| `pdf-text-pypdf@1` | None | |

**Where tables are stored.** In three fixed tables, whatever the file: `source_tables` (one row per table), `table_rows` (one row per data row, its cells as JSON) and `facts`. No file ever creates a database table ([ADR 0011](../docs/adr/0011-tables-land-in-one-fixed-schema.md)).

**How cells become facts.** [`extract_facts`](../engineering_search/indexing/facts.py) runs at index time on every table, by fixed rules on the column header, the table name and the cell. It never reads prose.

| Rule | Result |
| --- | --- |
| A cell under a grade, material, steel or concrete header that matches a grade (S355J2+N, C30/37, B500B, Grade 50) | `material_grade`, role `specification` |
| A cell under a status, approval or compliance header | `compliance_status`, role `status`, as written |
| A number with a unit in the cell, or a plain number with the unit in the header ("Allowable UDL (kN/m²)") | Converted to SI. The header decides the parameter and role: `allowable_distributed_load` or `load_capacity` (capacity), `roof_imposed_load`, `imposed_load` or `applied_load` (demand), `settlement` or `deflection` (measurement). Any other quantity is named after its column, with role `unknown` |
| The subject of each fact | The cell of the first column whose header names a component, member, mark, reference or similar; otherwise the first column |
| A key-value table (`\| Parameter \| Value \| … \|`) | The row label takes the place of the column header; the subject is the table's name |
| A `Project` column | Sets the project of each fact in that row |

Each fact keeps its file, table, row and column. Its line and page come from its row. Capacity and demand are never the same parameter. A number keeps its sign.

**How tables are used.** `query_sql` takes one `SELECT` written by the chat agent. The service evaluates the user's permissions on every indexed file, then copies the tables, rows and facts of the permitted files only into a new, read-only SQLite database for that one request. That projection has the tables `documents`, `facts`, `components` (a view), `table_rows` and `source_tables` ([`sql.py`](../engineering_search/sql.py)). Each result row names its file, table, row and line, and `get_document_evidence` returns the row as read with its facts and its passage.

## 5. Mixed documents

A mixed document is read once, by one reader, and each part takes its own lane.

| Format | Prose | Tables | Overlap |
| --- | --- | --- | --- |
| Markdown | Passages per section | Each pipe table | The table's lines stay in the section's passage, so a row is found by its words and by SQL |
| DXF drawing | A passage per note | The title block | Each attribute is also a passage (`TAG \| value`) |
| CSV, XLSX | None | The table or sheets | Each data row is also a passage |
| PDF | Passages per page | None (not built) | |

### Worked example: `specifications/roof-load.md`

The file, as written:

```text
 1  # Demonstration roof specification
 2
 3  SYNTHETIC EXAMPLE — not approved for engineering use.
 4
 5  ## Roof load
 6
 7  | Parameter | Value | Conditions | Approval status |
 8  | --- | --- | --- | --- |
 9  | Maximum uniformly distributed roof load | 5 kN/m² | Static load, dry conditions | Approved in this synthetic example |
10
11  ## Material specification
12
13  Roof support beams: S355 structural steel. This material specification applies to the example roof only.
```

What the index holds for it, as the code produces it:

| Store | Rows |
| --- | --- |
| `documents` | `specifications/roof-load.md`, fingerprint `d3c37521…6789`, 3 passages |
| `files` | type `markdown`, reader `markdown-text@2`, status `INDEXED_FULL` |
| `passages` and `passages_fts` | 3 passages: line 3 under "Demonstration roof specification"; lines 7–9 under "Roof load" (the table as written); line 13 under "Material specification". Each is indexed with the path words "specifications roof load" |
| `source_tables` | Table 1, "Roof load", columns Parameter, Value, Conditions, Approval status |
| `table_rows` | Row 1, line 9, its four cells |
| `facts` | Subject "Roof load": `allowable_distributed_load`, role capacity, "5 kN/m²", 5000 N/m², pressure. Subject "Roof load": `compliance_status`, "Approved in this synthetic example". Both cite table 1, row 1, line 9 |

So:

- "What is the maximum roof load?" is answered from either lane. The search quotes line 9, and SQL over `facts` returns 5 kN/m², citing the same line.
- "Roof support beams: S355 structural steel." on line 13 is prose. A search for "roof support beams" finds it. A SQL query for `material_grade = 'S355'` does not, because facts come only from tables.

## 6. When a file changes on disc

The source is the file on disc as it is now ([K3](../docs/constraints/clarifications.md#k3), [ADR 0007](../docs/adr/0007-the-source-is-the-file-on-disc.md)).

1. **Between refreshes.** Before an answer quotes a file, the service hashes the cited files again. A file whose bytes no longer match its fingerprint, or that is gone, is left out of a search or SQL result and named in `changed_files`; a direct read of it is refused (409). The answer falls back to the next permitted file, and old text is never quoted.
2. **The refresh.** It runs when a process starts and when the index team asks (`POST /index`, or Reindex on the index operations page) ([K16](../docs/constraints/clarifications.md#k16)). Nothing watches the repository: automatic refresh is part of [G5](../docs/constraints/gaps.md#g5).
3. **What a refresh does.** It hashes every file that has a reader, re-reads only the files that changed, and in one transaction deletes their old passages, rows and facts and writes the new ones. Deleted files are removed. For the example above, after "5 kN/m²" was edited to "6 kN/m²", one file was re-read, and the next search quoted 6 kN/m² with the new fingerprint.

## 7. Permissions and the index

Every file is indexed, whoever may read it. Permissions are applied per request, never baked into the index:

- For a search, the user's permissions are evaluated on every file that contains a question word. The ranking, the 1,000-passage limit, the answer, the counts and the pages use permitted files only.
- For SQL, the projection holds permitted files only, so no `WHERE`, `JOIN`, `COUNT` or `LIMIT` can see a forbidden row.
- A change of permissions takes effect on the next request; nothing is re-indexed.

In the example, JP may read `specifications/` and Kamal may not. For the same question, JP's answer quotes line 9 of the specification. Kamal's answer comes from a file that he may read, and his response has no name, text or count from the specification ([K13](../docs/constraints/clarifications.md#k13)).

## 8. Limits

| Limit | Effect | Recorded in |
| --- | --- | --- |
| Readers are stand-ins | Five formats, simply read. Real connectors replace them | [ADR 0001](../docs/adr/0001-prove-the-use-case-with-stand-in-readers.md), [K7](../docs/constraints/clarifications.md#k7) |
| No facts from prose | A value only in a sentence is not in SQL | [EXTRACTION.md](EXTRACTION.md#4-what-the-mvp-does-now) |
| No PDF tables, no OCR | A PDF table is text; a scan has no text | [G8](../docs/constraints/gaps.md#g8) |
| No CAD geometry; JT, DWG and Word not read | Listed in the coverage report as `NO_READER` | [G8](../docs/constraints/gaps.md#g8) |
| Fixed fact rules | A header the rules do not know gives role `unknown`; synonyms across files stay apart until an ontology maps them | [ADR 0011](../docs/adr/0011-tables-land-in-one-fixed-schema.md), [G6](../docs/constraints/gaps.md#g6) |
| No repository metadata | No author, date or revision; the project comes from folder names | [K15](../docs/constraints/clarifications.md#k15) |
| No watcher | A changed file is left out until the next refresh | [G5](../docs/constraints/gaps.md#g5) |
| No semantic store | Paraphrases outside the synonym list are missed | [O1](../docs/constraints/gaps.md#o1) |
