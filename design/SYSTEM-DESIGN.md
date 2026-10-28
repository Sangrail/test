# Engineering evidence search: gaps, phases and system design

**Planning status (2026-10-28):** This is a broader design proposal, not a list of shipped features or commitments to every phase. [ADRs](../docs/adr/README.md) record accepted scope and decisions; [TODO](../TODO.md) tracks delivery and gaps, and separates planned capabilities from the running prototype. The reader-version, persistent evidence and coverage decisions apply to later complex formats without bringing CAD into MVP scope. Database details, deep-search tools and numerical targets below remain proposals unless explicitly accepted in an ADR.

**Use case.** A selected engineering manager or lead finds a critical parameter (load limit, material specification, compliance approval status) across 100+ project documents in under 10 seconds. They get 100% confidence in the source and never open a design file or a PDF viewer.

**Scope of this MVP.** Markdown and PDFs with a text layer. No OCR. PDF tables are best effort. DXF, DWG, JT and CATIA come later.

![System design](system-design.png)

Source: [system-design.svg](system-design.svg). Solid boxes are the MVP. Dashed boxes are optional or later. Grey boxes are existing systems named in the brief. [code-architecture.png](code-architecture.png) shows the modules of the code, their layers and their imports.

## The MVP in one paragraph

The user asks the **existing chat-agent shell** a question in plain language. The shell's LLM calls one tool we provide, `search_evidence`. We:
1. Normalise the question: remove stop words, stem, expand synonyms.
2. Look the terms up in an inverted index (SQLite FTS5, the same technique as dtSearch or Lucene). Each term maps directly to the list of passages that contain it, so no document or passage is scanned at query time. Rank the matches with BM25 and apply the user's file permissions *before* any limit.
3. Select the answer: the exact sentence or table row that states the value, or, for a list question, one exact line for each matching document. Apply number comparisons ("greater than 5 kN/m²") with unit conversion.
4. Return the answer and the supporting passages, each with file, page, line range and version hash.

The shell quotes the answer; it never computes or infers a value. That is the whole MVP: **find** a parameter, or **list** every document that states it, with proof of source.

**Status (2026-10-28):** steps 1 to 4 are implemented, for the web page, the HTTP API and an MCP server. [design/EXTRACTION.md](EXTRACTION.md) maps each kind of question to the metadata and properties that later phases must extract, and to the stores that hold them.

## How the design uses the brief's constraints

| Constraint in the brief | Where it appears |
| --- | --- |
| Files live in an existing repository | **Document repository** is the source of truth. We read from it and never write into it. Change detection feeds the queue. |
| Connectors and APIs extract metadata, text and properties | **Extraction connectors** are called by the indexer workers. Our code only normalises their output into passages. |
| Structured and/or semantic stores | `index.sqlite3` is the structured store: documents, passages, section trees, ACL. It also holds the keyword index (FTS5). A semantic store (`vectors`) is an improvement area, not MVP. |
| A chat-agent shell calls backend APIs or tools | **Chat-agent shell** calls `search_evidence`, `get_evidence` and `verify_citations`. Its own LLM turns the question into a tool call, so we need no LLM of our own. |
| A users-to-files permissions database exists | **Permissions DB** is synced into the `acl` table. Retrieval joins on it *before* `LIMIT`. |

## The chat-agent shell and the search tool

### Tool contract

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

### No query language and no keyword-extraction API

The shell can pass the user's sentence unchanged, and our normalisation turns it into a query:
1. Stop words ("what is the …") are dropped.
2. Word forms are stemmed.
3. An SME-owned synonym list expands "UDL" to "imposed load" and "live load".
4. BM25 matches any of the words and ranks passages that contain more of them higher.

This replaces the current prototype's "every word must match" rule, which returns nothing for `roof loads` or `what is the maximum roof load`.

### API key

- **The real system:** the shell is existing, with its own LLM. We register the tools (OpenAPI or MCP), so **we need no key**.
- **The 40-minute prototype:** a minimal chat page stands in for the shell. It sends the message straight to `search_evidence` and shows evidence cards. **No key is needed.** If one is configured, an LLM can write a one-line answer above the cards, checked with `verify_citations`.

### Why numbers stay as quoted text

We do **not** extract every number into a database. A value is returned the way the source states it: the table row or sentence containing "5 kN/m²", at an exact location in a hashed file version.

That's what makes the source 100% traceable. Nothing is parsed, converted or computed, so no conversion step can be wrong.

For a question like "where is roof load above 5 kN/m²?", **list** mode returns the roof-load passage from each permitted document. The lead reads the values in one view, and the shell may only restate a number that `verify_citations` confirms. Automatic comparison is an [area for improvement](#areas-for-improvement-outside-the-mvp).

## Questions to clarify with the business

1. **What does "100% confidence" mean?** We propose: every value shown is a verbatim quote from a cited passage, at a hashed file version and an exact location. It is not a guarantee that the engineering value is correct or current. Is that acceptable?
2. **Which document is authoritative?** When an approved revision and a draft disagree, do the connectors expose revision and approval status? If not, we show both and label them.
3. **What do the connectors return for PDFs?** Page numbers, text block coordinates, bookmarks, document properties? This decides the evidence locator and the section path.
4. **How fresh does the index need to be?** Under 10 s is query latency. Separately, how soon after a file changes must it be searchable?
5. **Can the shell register our tools, and what may its LLM see?** The LLM receives passages the user is permitted to read. Is the shell's model provider approved for that content?
6. **Is "find and list" enough for the MVP?** We assume numeric comparisons ("above 5 kN/m²") and calculations are out of scope.

## Critical gaps and challenges

1. **"100% confidence" is about provenance, not truth.**
   - We guarantee the source: file, version hash, exact location and verbatim text.
   - `verify_citations` rejects any number in an answer that doesn't appear in the cited text. In that case the shell says "not found".
   - Still open: whether that document is the authoritative or current one. That needs revision and approval metadata.
2. **Users and documents use different words.** "Load limit" vs "maximum uniformly distributed load" vs "imposed load" vs "UDL". The MVP uses stemming, a synonym list and BM25 any-word matching. Recall@k measures what's still missed.
3. **Parameters often live in tables.**
   - Markdown tables are kept whole, header included.
   - PDF table structure is best effort, which is a known recall gap reported separately in the metrics.
   - Scanned PDFs count as "not searchable" in the coverage metric. They are never silently skipped.
4. **Permissions must apply before ranking.**
   - Filtering an already-limited result list loses permitted results and can leak counts.
   - The shell's LLM only ever sees permitted text.
   - If the ACL can't be checked, the system fails closed.
   - The audit log records which version of the permissions data was used, because the `acl` copy can lag the source.
5. **Some questions need computation, not search.** "Above 5 kN/m²" or "total load on…" can't be answered by retrieval alone. The MVP answers with **list** mode and quoted values. Automatic comparison is out of scope.
6. **The current prototype's storage doesn't survive restarts.**
   - The search index is in memory and is rebuilt by re-extracting every file at startup.
   - There are two ingestion paths: a full rebuild and an upload queue.
   - Uploads are written into the document folder.
   - The queue database's file name is an opaque hash of the folder path.
   - Fix: one `DATA_DIR`, one persistent `index.sqlite3`, and one ingestion path through the queue.
7. **Scale.**
   - Search never scans documents. Ingestion builds an inverted index once, as dtSearch did. A query reads the lists of passages for its few terms, so cost grows with how many passages contain those terms, not with how many files exist.
   - Indexing happens once per document version, when it changes. That is where the work for hundreds of thousands of documents goes.
   - One SQLite FTS5 node comfortably handles millions of passages. Beyond that, or with many concurrent users, move to a sharded Lucene-based engine such as OpenSearch. Licensing dtSearch is also a valid "buy" option, and it reads PDF natively.
   - The real cost is the initial crawl of a decade of documents. It's tracked as freshness, separately from query latency.
   - See [SCALING.md](SCALING.md).
8. **There is no gold set yet, so quality claims can't be made.** This needs SME time to write questions and label answers.

## Initial phase

| Phase | Delivers | Exit criteria (proposed) |
| --- | --- | --- |
| **0: done** | Local Markdown prototype. Verbatim evidence with versions. Audit gate that fails closed. Durable queue and worker pool. Telemetry. Simulated users with a per-file permission store (`access.py`). | Exists in `engineering_search/` |
| **1: MVP (implemented, except where noted below)** | `DATA_DIR` with a persistent `index.sqlite3`: FTS5, `documents`, `passages`, `section_trees` and `acl`. One ingestion path: change detection → queue → workers → connectors → publish. Markdown and text-PDF passages with full section paths and locators. Normalisation (stop words, stemming, synonyms) and BM25 any-word matching, with permissions applied first. The `search_evidence`, `get_evidence` and `verify_citations` tools. Gold set v1 and an evaluation harness. | find: Success@10 ≥ 0.95, MRR@10 ≥ 0.70. list: set recall ≥ 0.95. Citation precision = 100%. Permission leaks = 0. Search API p95 < 1 s. End-to-end p95 < 10 s. |

The numbers are proposals. Agree them with the business once gold set v1 gives a baseline.

**Phase 1 status (2026-10-28).** Implemented: the persistent FTS5 index, Markdown and text-PDF passages with page locators, query normalisation, answers and document lists, number comparisons, the MCP tools `search_evidence` and `read_evidence`, 17 scored questions and the use-case acceptance tests. Not implemented: `section_trees` (each passage has only its nearest heading), an `acl` table (rules are in `access.py`), `verify_citations`, and one ingestion path (the full rebuild and the upload queue are still separate). Current scores are in [README.md](../README.md#measure-search-quality).

### 40-minute prototype slice

1. **Store.** `index.sqlite3` with FTS5 (porter stemmer), plus `documents`, `passages` and `acl` tables. Reuse the simulated users and permissions from `access.py`.
2. **Extraction.** The existing Markdown extractor, plus page-level PDF text extraction as a stand-in for the connectors. Each passage gets a section path and a locator.
3. **Search.** Normalisation and a small synonym list, then BM25 with the `acl` join before `LIMIT`. Two modes, find and list.
4. **Interface.** The `search_evidence` and `get_evidence` endpoints. A minimal chat page with a user switcher, standing in for the shell, that shows evidence cards.
5. **Measurement.** About 15 gold questions over the demo Markdown and two text PDFs. A script that reports Success@3, MRR@10, list recall and permission leaks.

**Not in the slice:** changes to the queue, deep search, and any LLM.

## Areas for improvement (outside the MVP)

| Area | Why it matters | Approach when needed | Cost and risk |
| --- | --- | --- | --- |
| **Numeric comparison** ("above 5 kN/m²") | Users will ask it | **Done at query time:** parse value + unit from the lines of the matching documents and compare in code (`answer.py`). No new store. Later, if needed, extract facts at index time for a short fixed list of parameters. | Query-time parsing is limited by retrieval recall. Index-time extraction means a big store, unit normalisation and its own error rate. |
| **Typo tolerance** | "rooof laod" returns nothing | FTS5 trigram index, or "did you mean" from the index vocabulary | Low |
| **Semantic search** | Paraphrases the synonym list misses | Embeddings per passage, combined with BM25 via reciprocal rank fusion. Only if the gold set shows a recall gap. | Matches are harder to justify as evidence; numbers and IDs embed poorly |
| **Deep section search** | Long documents (400-page reports) | PageIndex tree search over the top 3 long, permitted documents, triggered by `deep:` or a low score | LLM cost, results that vary between runs, document text sent to a provider |
| **PDF tables** | Parameters live in tables | Table-aware extraction (pdfplumber, docling) that keeps table rows with their headers | Extraction errors in complex layouts |
| **Authority** | Draft vs approved, superseded revisions | Rank or label by revision and approval status from connector metadata | Depends on how good the metadata is |
| **OCR and CAD** | Scanned PDFs, DXF/DWG/JT/CATIA | OCR connector. CAD title blocks and properties via connectors. | Extraction quality, licensing |
| **Scale-out** | A decade of documents, many users | Postgres or OpenSearch, a broker with leases, multiple hosts ([SCALING.md](SCALING.md)) | Operations |

## Measuring retrieval

### Gold set

- **Size.** 60–100 questions written the way users ask them, split across load limits, material specifications and approval status, and across Markdown and PDF. Start with about 15 for the prototype.
- **Graded labels per passage.**
  - **2:** the passage contains the parameter value.
  - **1:** right section or document, but not the value.
  - **0:** not relevant.
- **Answer key.** For each question, an expected value, unit, file and location. For list questions, the complete set of documents that should be returned.
- **Special cases.**
  - "Not in corpus" questions, to test abstention.
  - Questions with conflicting answers, such as an approved revision vs a draft.
  - Test users with restricted permissions, to test for leaks.
- **Format.** Stored in TREC qrels format so standard tools can score it.

### find: ranked retrieval metrics (before the LLM)

| Metric | Definition | Why it matters here |
| --- | --- | --- |
| **Success@k** (Hit@k) | Share of questions with at least one grade-2 passage in the top k | Directly answers "can the lead find the parameter?" |
| **Recall@k** | Share of all grade-2 passages that appear in the top k | Conflicting values (5 vs 7 kN/m²) must *all* surface |
| **MRR@10** | Mean of 1 / rank of the first grade-2 passage | How far down the list the answer sits |
| **nDCG@10** | Gain from graded labels, discounted by position, normalised against the ideal ranking | Standard comparable score (BEIR reports nDCG@10). Uses the 0/1/2 grades. |
| **Zero-result rate** | Share of questions that return nothing | Catches failures like `roof loads` → 0 |

### list: set metrics

List questions should return *every* matching document, so they're scored as sets, not ranked lists:
- Precision = correct returned ÷ returned
- Recall = correct returned ÷ all correct

Recall matters more here, because a missed document is a missed value.

### Evidence and answer metrics (after the shell)

| Metric | Definition | Target |
| --- | --- | --- |
| **Value exact match** | The value and unit the shell states equal the answer key | ≥ 0.90 |
| **Citation precision** | Share of cited passages that contain the stated value verbatim. Checked by `verify_citations`, not by an LLM. | 100% (hard gate) |
| **Citation recall** | Share of stated values that have a supporting citation | 100% (hard gate) |
| **Abstention accuracy** | On "not in corpus" questions, the share that answer "not found" | ≥ 0.90 |
| **Faithfulness / context precision** | RAGAS metrics scored by an LLM judge | Secondary signal only. Scores move when the judge model changes. |

### Safety and operations

- **Permission leaks = 0.** A leak is any file ID, passage, snippet or match count from a file the user can't read. It counts whether it appears in a response, a log the user can see, or text sent to the shell's LLM. This is a hard gate.
- **Latency.** p50, p95 and p99 end to end and for each stage (normalisation, retrieval with the ACL join, audit, shell). Measured under concurrent queries *and* while indexing is running.
- **Freshness and coverage.**
  - Time to searchable (p95).
  - Extraction failure rate.
  - Index coverage: indexed files ÷ eligible files, with "PDF without a text layer" reported separately.

### Method

- Score runs with **ranx**, which reads TREC qrels and is validated against `trec_eval`.
- Report a bootstrap 95% confidence interval. With 15–100 questions, the intervals are wide.
- Compare variants with a paired significance test, for example all-words match vs BM25 any-word vs BM25 + synonyms.
- Break every metric down by parameter type and file type.
- Run the harness in CI so that a change that lowers Success@10 or causes any leak fails the build.

## What carries over from the current prototype

**Keep**
- The `Passage` evidence model: verbatim text, version hash, location.
- The audit gate that withholds evidence if it can't record the release.
- The job and worker semantics, and the scaling rules in [SCALING.md](SCALING.md).
- The `SearchIndex` and `AuditStore` interfaces.
- The simulated users and permission store in `access.py`.

**Change**
- Replace `InMemorySearchIndex` with `index.sqlite3` under `DATA_DIR`.
- Replace all-words matching with normalisation plus BM25 any-word matching.
- Route every file through the queue and remove the separate full-rebuild path.
- Treat uploads as a test or admin path only; the real input is the repository connector.
- Store a full section path on each passage, and generalise the locator to support page + bbox.

Done: the SQLite FTS5 index replaced `InMemorySearchIndex`, and normalisation with any-word matching replaced all-words matching. Still to do: one ingestion path, section paths, and page + bbox locators. [ARCHITECTURE.md](../ARCHITECTURE.md) describes the code as it runs now.

## Sources

- ranx: ranking evaluation and comparison, validated against TREC Eval: <https://pypi.org/project/ranx/>
- RAGAS metrics (faithfulness, context precision and recall): <https://docs.ragas.io/en/latest/concepts/metrics/>
- Gao et al., *Enabling Large Language Models to Generate Text with Citations* (ALCE), EMNLP 2023: <https://arxiv.org/abs/2305.14627>
- Thakur et al., *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models*, 2021 (nDCG@10 as the standard score): <https://arxiv.org/abs/2104.08663>
- Järvelin and Kekäläinen, *Cumulated gain-based evaluation of IR techniques*, ACM TOIS 2002 (nDCG): <https://doi.org/10.1145/582415.582418>
- PageIndex: <https://github.com/VectifyAI/PageIndex>
