---
status: accepted
date: 2026-10-28
---
# Defer the facts store and embeddings until the questions and the data are known

**Serves:** S1 (MVP only), C3 (connectors extract metadata, text and properties), C4 (structured and/or semantic stores), U1 (load limit, material or approval status).

## Context

The constraints offer connectors that extract properties (C3), and structured and semantic stores (C4). A structured store of engineering facts (element, parameter, value, unit, status, source) would answer "the roof load limit at Northgate" directly. Embeddings in a semantic store would find passages that use different words from the question. Both need decisions that the MVP cannot make yet:

- Which questions do users ask? Which parameters (U1) and which words?
- Which document types hold the answers, and in which form: sentences, tables, title blocks or drawings?
- Which readers and extractors can get the values reliably, with their source?

There is no one design that suits all repositories. A facts store made without this research extracts the wrong properties. Embeddings without tests can rank a similar but wrong passage first, which breaks U4.

## Decision

- For the MVP (S1), use word search and exact text answers only ([ADR 0009](0009-sqlite-fts5-index-and-answers.md)).
- Do not build a facts store or embeddings yet.
- First, profile the repository and collect real questions and answers ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). Then design the extractors and stores from those questions ([design/EXTRACTION.md](../../design/EXTRACTION.md)).
- Keep the index schema and the source fields (file, page, lines, version) so that a later facts store or embedding index can cite the same sources.

## Consequences

- The MVP finds words, not meanings. Synonyms are a small fixed list. The metrics on the test data are high because the questions, the synonyms and the documents were made together ([docs/METRICS.md](../METRICS.md)).
- Hybrid search (words and embeddings) and the facts store are phase 2 and 3 work ([TODO.md](../../TODO.md#next-phase-2)).
- The question set and the acceptance tests ([ADR 0015](0015-acceptance-tests-enforce-the-use-case.md)) will measure whether the later stores are better.

## Implementation

Deferred. The design is in [design/EXTRACTION.md](../../design/EXTRACTION.md) and [design/DATA-PROFILE.md](../../design/DATA-PROFILE.md). The README section "This is a basic method" explains the limit to users.
