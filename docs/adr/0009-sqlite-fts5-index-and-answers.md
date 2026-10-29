---
status: accepted, amended by 0017 (bound list comparisons, signed numbers, list paging)
date: 2026-10-28
---
# Use a SQLite FTS5 inverted index, and answer with exact text

> **Amended** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): list comparisons need a bound line, numbers keep their sign, and lists are paged. Filters over tables use SQL ([ADR 0016](0016-structured-facts-and-client-written-sql.md)).

**Serves:** U1 (find a parameter), U2 (100+ documents), U3 (under 10 seconds), U4 (100% confidence in the source), U6 (plain language), R2 (an answer, not passages), R3 (lists of documents).

## Context

The first prototype kept passages in memory and needed every question word to match exactly. Plain-language questions (U6) found nothing for 76% of the test questions. Search across 100+ documents in under 10 seconds (U2, U3) needs an index, not a scan of the passages, as dtSearch and Lucene do. The first prototype also returned passages. The user asked for an answer (R2), and for lists of documents (R3). Confidence in the source (U4) means that the service must not write or change the answer text.

## Decision

1. Store documents and passages in SQLite, with an FTS5 inverted index over the heading, the text and the words of the file path. Use the `porter unicode61` tokenizer, so "loads" matches "load".
2. Change each question into an index query: remove common words, add a small synonym list, and make words with digits into prefix searches ("S355" finds "S355J2+N"). Show the user what was searched for.
3. Match any word. Rank passages that contain more of the question words first, then by BM25 (heading 3, text 1, file path 0.5).
4. Answer with text copied from a passage: one sentence or table row for a value question, or one line for each document in a list question. Never write or change the answer text.
5. For list questions, find the documents that contain every question word. Apply number comparisons ("greater than 5 kN/m²") at query time, with unit conversion.
6. Update the index incrementally by SHA-256, in one transaction ([ADR 0004](0004-persistent-evidence.md)).

## Consequences

- A question takes about 16 ms on the 138 test files, far below the 10-second limit.
- Each answer has a file, page, line range and version. Tests check it against the file.
- This is a basic method. It finds words, not meanings. It does not know which element a value belongs to, and number filters see only what word search finds. [ADR 0014](0014-defer-facts-store-and-embeddings.md) records why facts and embeddings are deferred.
- At a larger scale, the same design moves to OpenSearch or Elasticsearch ([design/SCALING.md](../../design/SCALING.md)).

## Implementation

Done. [`store.py`](../../engineering_search/store.py) (index, up to 1,000 candidates from permitted files), [`query.py`](../../engineering_search/query.py) (query plan), [`answer.py`](../../engineering_search/answer.py) (answer and list), [`units.py`](../../engineering_search/units.py) (quantities, with sign, in SI units). A list comparison counts a quantity only in a sentence bound to the question words. A list is paged at 200 documents, with the total count. Measured by `scripts/evaluate.py`. Enforced by `tests/test_use_case.py`, `tests/test_index.py` and `tests/test_binding.py`.

Limits: the incremental update reads and hashes every file; only extraction is incremental. Filters over tables now use SQL ([ADR 0016](0016-structured-facts-and-client-written-sql.md)); the text path stays for values in prose.
