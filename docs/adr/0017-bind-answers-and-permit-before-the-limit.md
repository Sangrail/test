---
status: accepted
date: 2026-10-29
version: 1
---

# Bind each answer to its subject, and apply permissions before the retrieval limit

Supersedes in part [ADR 0013](0013-no-answer-before-a-wrong-answer.md) (the whole-document word check) and [ADR 0006](0006-permissions-before-results.md) (permissions after the lookup). Amends [ADR 0009](0009-sqlite-fts5-index-and-answers.md) (list comparisons and paging).

**Serves:** [U4](../constraints/use-case.md#u4) (100% confidence in the source), [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [R2](../constraints/requirements.md#r2) (an answer, not passages), [R3](../constraints/requirements.md#r3) (lists by value).

## Context

An independent review on 28 October 2026 reproduced four errors in the text path:

1. **A wrong parameter was `found`.** ADR 0013 checked the question words against the whole document. "Roof load is not specified. Floor load limit is 5 kN/m²." answered "What is the roof load?" with the floor load, status `found`. A list comparison could also qualify a document by a floor load for a roof load filter. This is the wrong answer that ADR 0013 exists to prevent ([U4](../constraints/use-case.md#u4)).
2. **Forbidden files changed a user's results.** ADR 0006 checked permissions after the index lookup, and the lookup kept the 1,000 best passages from all files. Forbidden passages that ranked higher pushed permitted ones out. No forbidden text was shown, but a forbidden file changed what a user saw, which breaks [R1](../constraints/requirements.md#r1) in spirit.
3. **Signs were ignored.** "-2 kN/m²" compared as 2 kN/m².
4. **Lists stopped at 200 documents** and `page` did not page them.

## Decision

- **Bind the answer to the question words.** A question word is bound when it is in the selected sentence, its passage heading, the file path, or the document title. The title counts only if the first passage starts in the first three lines of the file or of its first page.
- **Statuses:**
  - `found`: every question word is bound to the sentence.
  - `unverified` (new): the document has every question word, but the sentence does not name some of them (`unbound_words`). The value may be about something else. The user and the chat agent must see the warning.
  - `partial`: some question words are not in the document (`missing_words`).
  - `not_found`: no sentence states a value that matches enough question words.
- **List comparisons need a bound line.** A document qualifies only if one line states a quantity that meets the comparison and every question word is bound to that line.
- **Permissions before the limit.** Find the files that contain a query word, evaluate permissions on them (and apply `within`), and pass the permitted set into the FTS5 query. The 1,000-passage limit applies to permitted passages only.
- **Signed numbers.** A leading minus is a sign. A hyphen inside a code (B-104) or a range (1-2 kN) is not.
- **Page lists** at 200 documents, with the total `count`, `document_pages` and `truncated`.

## Consequences

- Some answers that were `found` are now `unverified`. That costs apparent precision and gains trust: the service no longer presents an unbound value as the answer.
- Binding is a word check. A sentence that names the subject can still state a different parameter. Facts from tables ([ADR 0016](0016-structured-facts-and-client-written-sql.md)) bind value to subject structurally; prose still relies on words.
- The title rule is a heuristic until the readers return a title.
- Adding forbidden files can no longer change a user's results. The index query is a little more complex (a temporary scope table joined inside the FTS5 query).

## Implementation

Done. `pick_answer()`, `list_documents()` and `title()` in [`answer.py`](../../engineering_search/answer.py); signed numbers in [`units.py`](../../engineering_search/units.py); `document_matches()` and `candidates(query, files)` in [`store.py`](../../engineering_search/store.py); the order of steps in `SearchService.search` ([`service.py`](../../engineering_search/service.py)). Tests: [`tests/test_binding.py`](../../tests/test_binding.py) (floor load not the roof answer, heading binds, list filter, signed values, forbidden passages past the candidate limit, list page 2), [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py) (first five and last pages).

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-29 | now | Recorded when the decision was made. | sangrail |
