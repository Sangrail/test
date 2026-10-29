# Engineering evidence search: gaps, phases and system design

**How to read this document (updated 2026-10-29).** It has two parts.

- [Part 1](#part-1-what-is-built-now) describes what the code does now, in summary. [ARCHITECTURE.md](../ARCHITECTURE.md) is the full description.
- [Part 2](#part-2-proposed-design) is a design proposal. Nothing in Part 2 is built unless a line says **Built**. The proposal is not a commitment to every phase. The numbers in it are proposed targets, not results.

[ADRs](../docs/adr/README.md) record the accepted decisions. [TODO](../TODO.md) tracks delivery, gaps and defects.

**Use case.** A selected engineering manager or lead finds a critical parameter (load limit, material specification, compliance approval status) across 100+ project documents in under 10 seconds. They get 100% confidence in the source and never open a design file or a PDF viewer.

**Scope of this MVP.** Markdown, PDFs with a text layer, CSV and XLSX. Markdown pipe tables, CSV files and workbook sheets are read as tables, and fixed rules extract typed facts from them. No OCR. PDF tables come out as text lines only. DXF, DWG, JT and CATIA come later: the detector reads the version in a JT header, and nothing more.

![System design](system-design.png)

Source: [system-design.svg](system-design.svg). Solid boxes are the MVP. Dashed boxes are optional or later. Grey boxes are existing systems named in the brief. [code-architecture.png](code-architecture.png) shows the modules of the code, their layers and their imports.

The diagram was redrawn on 29 October 2026 for the current design: both question paths, the permission check before the index lookup limit, tables and facts in the index, the index lock, admission control and the current scores. It is a summary. Part 1 and [ARCHITECTURE.md](../ARCHITECTURE.md) give the detail. Where they differ, they are correct.

## Part 1: What is built now

### One question, as built

There are two ways in. Both use one `SearchService`, one index, one set of permissions and one audit log.

**Unstructured (text).** The user asks a question on the web page, through the HTTP API, or through a chat agent that calls the MCP tool `search_evidence`. All three call one function, `SearchService.search`.

1. **Normalise.** Remove stop words, expand a small synonym list, and make words with digits into prefix searches. Decide if the question asks for one value or a list, and find a number comparison ("greater than 5 kN/m²").
2. **Check permissions.** Find every file that contains a query word. Apply `within`. Apply path rules from `access.py` (a Python dictionary, not a database table) to those files.
3. **Look up.** Query a persistent SQLite FTS5 inverted index (`index-<id>.sqlite3`), over the permitted files only. The file filter is inside the index query, so it applies before the limit. Rank passages that contain more question words first, then by BM25. Keep the best 1,000 passages.
4. **Answer.** For one value: from the 8 best permitted passages, select one sentence or table row that states a value, copied exactly. Its status is `found` only if every question word is in the sentence, its heading, the file path or the document title. Otherwise it is `unverified` (the document has the word elsewhere) or `partial` (the document does not have it). For a list: read every passage of each readable document that contains every question word, apply the number comparison at query time with unit conversion and signs, and return a page of 200 documents.
5. **Audit, then return.** Write the audit record. If that fails, return no evidence. The response has the answer and the supporting passages, each with file, page, line range and SHA-256 version.

**Structured (tables and facts).** A chat agent calls `describe_schema`, writes one SQL `SELECT`, and calls `query_sql`. The agent writes the SQL, not the service.

1. **Check permissions** on every indexed file.
2. **Build a projection:** a new SQLite database in memory, with the tables, rows and facts of the permitted files only.
3. **Run the statement** under limits: one `SELECT`, an authoriser that allows only the projection tables and plain functions, a read-only connection, a step budget, at most 500 rows and 4,000 characters.
4. **Audit** the SHA-256 of the statement, the scope counts and the files in the result, never the rows. Then return the rows. Each row has its file, table, row, line and page. `get_document_evidence` returns the exact row and its passage.

The chat agent writes the reply. Nothing checks that its reply matches the tool result.

### The MCP tools, as built

```text
search_evidence(question, mode?: "auto" | "answer" | "list", within?: [file_id], limit?: 1..50, page?)
  → answer (one value with its status and source, or a page of up to 200 documents),
    searched_for, supporting passages (file, page, lines, SHA-256 version, exact text), paging fields

read_evidence(file_id, page?)
  → all passages of one file, or of one PDF page, if the user may read it

describe_schema() · list_tables() · describe_table(table)
  → the tables of the projection, their columns, units and citation notes

query_sql(sql, limit?: 1..500)
  → columns, rows, row_count, truncated; rows only from files the user may read

get_document_evidence(file_id, table_no, row_no)
  → the row as read, its facts, line, page, SHA-256 version and the passage that holds it

get_index_coverage(gaps_limit?)       # registered only for an index-team --user
  → coverage by type, format version, status, folder and capability, with each gap
```

`page` pages the supporting passages, and the document list of a list answer.

The server runs on local stdio only. Claude Code, Codex and Pi were connected to it by hand, and each answered the structured question with citations. `tests/test_mcp_stdio.py` runs a real MCP client session.

### Proposed items that are not built

| Proposed in Part 2 | Built now |
| --- | --- |
| `get_evidence(evidence_id)` | `read_evidence(file_id, page)` returns a whole file or page. `get_document_evidence` returns one table row |
| `verify_citations(answer, evidence_ids)` | Not built. Nothing checks the agent's reply |
| An `acl` table, joined before `LIMIT` | Path rules in `access.py`. The permitted files are passed into the index query, before the limit, and into the SQL projection |
| `section_trees` and full section paths | Each passage has only its nearest heading |
| Page + bounding-box locators | Page (or sheet) and line range (or sheet row) |
| One ingestion path through the queue | Two paths: full refresh and the Markdown upload queue |

Built since the last update: scanned PDFs are reported as `NO_TEXT_LAYER` in a coverage report, and a file lock coordinates index refreshes between processes that share a state folder.

### Defects fixed

The review of 2026-10-28 found six defects. All six are fixed: a wrong parameter is now `unverified`, not `found`; permissions apply before the retrieval limit; signs are read in number comparisons; lists are paged; two processes take turns to publish the index; PDFs without text are reported. [ARCHITECTURE.md](../ARCHITECTURE.md#defects-fixed-since-the-review) lists each fix with its test.

### How the built system uses the brief's constraints

| Constraint in the brief | Built now | Proposed |
| --- | --- | --- |
| Files live in an existing repository | A local folder stands in for it. The service reads it and never writes into it, except Markdown uploads | Read from the repository through its connector. Change detection feeds the queue |
| Connectors and APIs extract metadata, text and properties | The indexer (`engineering_search/indexing/`): file type and format version detection from the content, a reader registry, and built-in readers for Markdown, text-layer PDF, CSV and XLSX. Fixed rules extract typed facts from tables. Other files are listed in a coverage report with their status | **Extraction connectors**, called by the indexer workers. Our code only normalises their output into passages, tables and facts |
| Structured and/or semantic stores | `index-<id>.sqlite3`: `documents`, `passages`, `passages_fts` (keyword index), `files` (inventory), `source_tables`, `table_rows`, `facts` and `meta` | Add section trees, metadata, and facts from text ([EXTRACTION.md](EXTRACTION.md)). A semantic store (`vectors`) only if the questions show a gain |
| A chat-agent shell calls backend APIs or tools | A stdio MCP server with text search, constrained SQL and evidence tools, checked by hand with Claude Code, Codex and Pi. The user comes from an unverified `--user` flag | A remote MCP server behind company sign-in. Add `verify_citations` |
| A users-to-files permissions database exists | Path rules in `access.py`, evaluated per request and applied inside retrieval, before the limit, and before the SQL projection is built | Sync the permissions from the repository into the index |

## Part 2: Proposed design

### Proposed tool contract

```text
search_evidence(question: str, project?: str, mode: "find" | "list" = "find")
  → request_id
    searched_for: terms, synonyms applied, project, mode   # the shell echoes this to the user
    results[]:    evidence_id, file, section_path, locator (lines | page + bbox),
                  version (SHA-256), revision, approval_status, text (verbatim)
    matched_documents, truncated

get_evidence(evidence_id)                → the passage plus surrounding context
verify_citations(answer, evidence_ids[]) → every number and unit in the answer, each
                                           marked as found or not found in the cited text
```

- **find** returns the top 10 sections.
- **list** returns every permitted document with a matching passage, one row per document, paged.

**Built:** `search_evidence` with a different signature, and `read_evidence` in place of `get_evidence` (see [Part 1](#the-mcp-tools-as-built)). The document list is paged, with `count` and `truncated`. Not built: `project`, `section_path`, bbox locators, `revision`, `approval_status` and `verify_citations`.

### No query language and no keyword-extraction API

The shell can pass the user's sentence unchanged, and normalisation turns it into a query:

1. Stop words ("what is the …") are dropped.
2. Word forms are stemmed.
3. An SME-owned synonym list expands "UDL" to "imposed load" and "live load".
4. BM25 matches any of the words and ranks passages that contain more of them higher.

**Built**, with a small synonym list in `query.py` that the developers wrote, not an SME-owned list. It replaced the first prototype's rule that every word must match.

**Built, in addition:** for questions over tables, the shell does use a query language. Its LLM writes one SQL `SELECT`, and the service runs it under limits over the permitted rows only (see [Part 1](#one-question-as-built)). This is a choice to let the shell form structured queries. The service constrains the SQL. It does not write it or check that it matches the question.

### API key

The shell is existing, with its own LLM. We register the tools (OpenAPI or MCP), so **we need no key**.

**Built:** the MCP server needs no key. The web page has no chat box and uses no language model. A chat box on the web page would need a server-side language model that calls the same search function. It is not built.

### Answer text and numbers

**Built:** the answer text is a verbatim quote: the table row or sentence that contains the value, at an exact location in a hashed file version. The service never writes, rounds or converts the answer text.

**Built:** list questions with a comparison ("roof load greater than 5 kN/m²") parse value and unit from the lines of the matching documents at query time, convert units, keep signs, and compare in code (`answer.py`). Every question word must be bound to the qualifying line. Known limits: binding is a word check, not a check of meaning; only what word search finds is compared; a unit in a table header is not read on this path.

**Built:** index-time facts from table cells, for a short fixed list of parameters, with SI values ([EXTRACTION.md](EXTRACTION.md)). The shell filters them with SQL. A value in free text is not a fact.

**Proposed:** `verify_citations`, so that the shell may only restate a number that is in the cited text.

The quote makes the source traceable. It does not prove that the quoted value answers the question.

### Questions to clarify with the business

1. **What does "100% confidence" mean?** We propose: every value shown is a verbatim quote from a cited passage, at a hashed file version and an exact location. It is not a guarantee that the engineering value is correct or current, or that the quoted value is the asked parameter. Is that acceptable?
2. **Which document is authoritative?** When an approved revision and a draft disagree, do the connectors expose revision and approval status? If not, we show both and label them.
3. **What do the connectors return for PDFs?** Page numbers, text block coordinates, bookmarks, document properties? This decides the evidence locator and the section path.
4. **How fresh does the index need to be?** Under 10 s is query latency. Separately, how soon after a file changes must it be searchable?
5. **Can the shell register our tools, and what may its LLM see?** The LLM receives passages the user is permitted to read. Is the shell's model provider approved for that content?
6. **Are find, list and simple numeric comparison enough for the MVP?** The MVP now includes a query-time comparison with the limits above, and SQL filters over facts from tables. SQL can count and sum, but the service does not check a calculation that the shell makes. Calculations ("total load on…") are out of scope.

### Critical gaps and challenges

1. **"100% confidence" is about provenance, not truth.**
   - **Built:** the source: file, version hash, exact location and verbatim text.
   - **Built:** the status `found` needs every question word in the sentence, its heading, the file path or the document title. A sentence that does not name some of them is `unverified`, with the words it lacks. This is a word check: it does not prove that the value is the asked parameter.
   - **Proposed:** `verify_citations` rejects any number in an answer that is not in the cited text. Then the shell says "not found".
   - Still open: whether that document is the authoritative or current one. That needs revision and approval metadata.
2. **Users and documents use different words.** "Load limit" vs "maximum uniformly distributed load" vs "imposed load" vs "UDL". **Built:** stemming, a small synonym list and BM25 any-word matching. Recall@k measures what is still missed.
3. **Parameters often live in tables.**
   - **Built:** Markdown pipe tables, CSV files and workbook sheets are read as tables, with the line of each row, and fixed rules make typed facts from their cells.
   - **Built:** PDF tables come out as lines of text. Table structure is lost.
   - **Built:** scanned PDFs have the status `NO_TEXT_LAYER`, and the coverage report lists them as gaps. There is no OCR.
4. **Permissions must apply before any limit.**
   - Filtering an already-limited result list loses permitted results, and lets forbidden documents change what a user sees.
   - **Built:** the permitted files are passed into the index query, before the 1,000-passage limit. For SQL, the projection holds only the permitted rows, before any filter, join, count or limit.
   - **Built:** the shell's LLM only sees permitted text and rows. If the permission check fails, the system fails closed. The audit log records the permission version.
   - **Proposed:** permissions synced from the repository into the index.
5. **Some questions need computation, not search.** **Built:** query-time comparison for list questions, and SQL filters over facts, with the limits in [Answer text and numbers](#answer-text-and-numbers). Calculations ("total load on…") are out of scope.
6. **Ingestion.**
   - **Built:** one persistent SQLite index in the state folder. The indexer (`engineering_search/indexing/`) lists every file, detects its type and format version from the content, reads and hashes the files that have a reader, and extracts only new and changed files (and files whose reader version changed). Changes apply in one transaction. A file lock lets one process at a time plan and publish, so processes that share a state folder take turns.
   - **Now:** two ingestion paths (full refresh and the upload queue). Uploads are written into the document folder.
   - **Proposed:** one ingestion path through the queue.
7. **Scale.**
   - The index lookup does not scan the documents or the passages. A query reads the lists of passages for its few terms, so its cost grows with how many passages contain those terms, not with how many files exist. **Now:** the answer step then reads passage text, and a list question reads all passages of each matching document. This is fast at 148 files, but grows with the number of matches. A SQL request copies the permitted structured rows into memory, which also grows with the repository.
   - Extraction happens once per document version, when it changes. **Now:** every refresh also reads and hashes every file.
   - One SQLite FTS5 node handles millions of passages. Beyond that, or with many concurrent users, move to a sharded Lucene-based engine such as OpenSearch. Licensing dtSearch is also a valid "buy" option, and it reads PDF natively.
   - The real cost is the initial crawl of a decade of documents. Track it as freshness, separately from query latency.
   - See [SCALING.md](SCALING.md).
8. **There is no gold set from real users yet, so quality claims cannot be made.** The current 17 questions (16 scored) were written by the developers. This needs SME time to write questions and label answers.

### Phases

| Phase | Delivers | Exit criteria (proposed) | Status |
| --- | --- | --- | --- |
| **0** | First local Markdown prototype. Verbatim evidence with versions. Audit gate that fails closed. Durable queue and worker pool. Telemetry. Simulated users with a per-file permission store (`access.py`). | Exists | Done. Superseded by phase 1 |
| **1: MVP** | Persistent `index.sqlite3` with FTS5, `documents`, `passages`, `section_trees` and `acl`. One ingestion path: change detection → queue → workers → connectors → publish. Markdown and text-PDF passages with full section paths and locators. Normalisation and BM25 any-word matching, with permissions applied before any limit. The `search_evidence`, `get_evidence` and `verify_citations` tools. Gold set v1 and an evaluation harness. | find: Success@10 ≥ 0.95, MRR@10 ≥ 0.70. list: set recall ≥ 0.95. Citation precision = 100%. Permission leaks = 0. Search API p95 < 1 s. End-to-end p95 < 10 s. | Partly built. See below |

The numbers are proposals. Agree them with the business once a real gold set gives a baseline.

**Phase 1 status (2026-10-29).**

- **Built:** the persistent FTS5 index; Markdown, text-PDF, CSV and XLSX passages with page or sheet locators; content detection and a reader registry; a coverage report; query normalisation; one-value answers with binding statuses, and paged document lists; query-time number comparison; permissions before the retrieval limit; tables and facts from tables; constrained SQL; the MCP tools listed in [Part 1](#the-mcp-tools-as-built); a cross-process index lock; 17 developer-written questions (16 scored); use-case acceptance tests; a real stdio MCP client test.
- **Not built:** `section_trees` (each passage has only its nearest heading); an `acl` table (rules are in `access.py`); `get_evidence`; `verify_citations`; one ingestion path; facts from free text; metadata from a connector.
- **Measured on the test data:** Success@1 0.88, MRR@10 0.90, Recall@10 0.90, correct answer 1.00, permission leaks 0 in the evaluation, search service p50 about 79 ms and p95 about 330 ms. End-to-end latency through a chat agent is not measured. List set recall, SQL answers and citation precision are not scored. See [METRICS.md](../docs/METRICS.md).

### Areas for improvement (outside the MVP)

| Area | Why it matters | Approach when needed | Cost and risk |
| --- | --- | --- | --- |
| **Numeric comparison** ("above 5 kN/m²") | Users will ask it | **Built at query time** in `answer.py`, with signs and word binding, limited by recall. **Built at index time** for table cells: facts with SI values, filtered with SQL. Later: facts from free text | Query-time parsing is limited by retrieval recall. Index-time extraction needs unit normalisation and has its own error rate. The shell's SQL can be wrong |
| **Value-to-element binding** | A document states several parameters | **Built:** answers whose sentence does not name every question word are `unverified`. Facts from tables have a subject and a role. Later: subjects for values in free text | Rules miss notations. Word binding is not a check of meaning |
| **Typo tolerance** | "rooof laod" returns nothing | FTS5 trigram index, or "did you mean" from the index vocabulary | Low |
| **Semantic search** | Paraphrases the synonym list misses | Embeddings per passage, combined with BM25 via reciprocal rank fusion. Only if the gold set shows a recall gap. | Matches are harder to justify as evidence; numbers and IDs embed poorly |
| **Deep section search** | Long documents (400-page reports) | PageIndex tree search over the top 3 long, permitted documents, triggered by `deep:` or a low score | LLM cost, results that vary between runs, document text sent to a provider |
| **PDF tables** | Parameters live in tables | Table-aware extraction (pdfplumber, docling) that keeps table rows with their headers | Extraction errors in complex layouts |
| **Authority** | Draft vs approved, superseded revisions | Rank or label by revision and approval status from connector metadata | Depends on how good the metadata is |
| **OCR and CAD** | Scanned PDFs, DXF/DWG/JT/CATIA | OCR connector. CAD title blocks and properties via connectors. | Extraction quality, licensing |
| **Scale-out** | A decade of documents, many users | Postgres or OpenSearch, a broker with leases, multiple hosts ([SCALING.md](SCALING.md)) | Operations |

### Measuring retrieval (proposed)

**Built:** `scripts/evaluate.py` scores 16 questions with Success@k, MRR@10, Recall@10, a zero-result rate, a lenient "correct answer" check (expected file and expected text) and a permission-leak count. It does not use ranx, graded labels, confidence intervals or CI gates. The rest of this section is proposed.

#### Gold set

- **Size.** 60–100 questions written the way users ask them, split across load limits, material specifications and approval status, and across Markdown and PDF.
- **Graded labels per passage.**
  - **2:** the passage contains the parameter value.
  - **1:** right section or document, but not the value.
  - **0:** not relevant.
- **Answer key.** For each question, an expected value, unit, file and location. For list questions, the complete set of documents that should be returned.
- **Special cases.**
  - "Not in corpus" questions, to test abstention.
  - Documents that state several parameters, to test that the answer is the asked one.
  - Questions with conflicting answers, such as an approved revision vs a draft.
  - Test users with restricted permissions, to test for leaks, and restricted documents that rank above permitted ones, to test that permitted results do not change.
- **Format.** Stored in TREC qrels format so standard tools can score it.

#### find: ranked retrieval metrics (before the LLM)

| Metric | Definition | Why it matters here |
| --- | --- | --- |
| **Success@k** (Hit@k) | Share of questions with at least one grade-2 passage in the top k | Directly answers "can the lead find the parameter?" |
| **Recall@k** | Share of all grade-2 passages that appear in the top k | Conflicting values (5 vs 7 kN/m²) must *all* surface |
| **MRR@10** | Mean of 1 / rank of the first grade-2 passage | How far down the list the answer sits |
| **nDCG@10** | Gain from graded labels, discounted by position, normalised against the ideal ranking | Standard comparable score (BEIR reports nDCG@10). Uses the 0/1/2 grades. |
| **Zero-result rate** | Share of questions that return nothing | Catches failures like `roof loads` → 0 |

#### list: set metrics

List questions should return *every* matching document, so they are scored as sets, not ranked lists:

- Precision = correct returned ÷ returned
- Recall = correct returned ÷ all correct

Recall matters more here, because a missed document is a missed value.

#### Evidence and answer metrics (after the shell)

| Metric | Definition | Target |
| --- | --- | --- |
| **Value exact match** | The value and unit the shell states equal the answer key | ≥ 0.90 |
| **Citation precision** | Share of cited passages that contain the stated value verbatim. Checked by `verify_citations`, not by an LLM. | 100% (hard gate) |
| **Citation recall** | Share of stated values that have a supporting citation | 100% (hard gate) |
| **Abstention accuracy** | On "not in corpus" questions, the share that answer "not found" | ≥ 0.90 |
| **Faithfulness / context precision** | RAGAS metrics scored by an LLM judge | Secondary signal only. Scores move when the judge model changes. |

#### Safety and operations

- **Permission leaks = 0.** A leak is any file ID, passage, snippet or match count from a file the user cannot read. It counts whether it appears in a response, a log the user can see, or text sent to the shell's LLM. Also: a user's permitted results must not change when restricted documents are added. This is a hard gate.
- **Latency.** p50, p95 and p99 end to end and for each stage (normalisation, retrieval with permissions, audit, shell). Measured under concurrent queries *and* while indexing is running.
- **Freshness and coverage.**
  - Time to searchable (p95).
  - Extraction failure rate.
  - Index coverage: indexed files ÷ eligible files, with "PDF without a text layer" reported separately.

#### Method

- Score runs with **ranx**, which reads TREC qrels and is validated against `trec_eval`.
- Report a bootstrap 95% confidence interval. With 15–100 questions, the intervals are wide.
- Compare variants with a paired significance test, for example all-words match vs BM25 any-word vs BM25 + synonyms.
- Break every metric down by parameter type and file type.
- Run the harness in CI so that a change that lowers Success@10 or causes any leak fails the build.

## History: from the first prototype

The first prototype kept passages in memory and rebuilt them at each start, needed every question word to match, and had two ingestion paths. Phase 1 replaced the in-memory index with a persistent SQLite FTS5 index, and all-words matching with normalisation and any-word matching. It kept the `Passage` evidence model, the audit gate that withholds evidence if it cannot record the release, the job and worker semantics, the `SearchIndex` and `AuditStore` interfaces, and the simulated users in `access.py`. Still to do from that plan: one ingestion path, section paths, and page + bbox locators.

## Sources

- ranx: ranking evaluation and comparison, validated against TREC Eval: <https://pypi.org/project/ranx/>
- RAGAS metrics (faithfulness, context precision and recall): <https://docs.ragas.io/en/latest/concepts/metrics/>
- Gao et al., *Enabling Large Language Models to Generate Text with Citations* (ALCE), EMNLP 2023: <https://arxiv.org/abs/2305.14627>
- Thakur et al., *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models*, 2021 (nDCG@10 as the standard score): <https://arxiv.org/abs/2104.08663>
- Järvelin and Kekäläinen, *Cumulated gain-based evaluation of IR techniques*, ACM TOIS 2002 (nDCG): <https://doi.org/10.1145/582415.582418>
- PageIndex: <https://github.com/VectifyAI/PageIndex>
