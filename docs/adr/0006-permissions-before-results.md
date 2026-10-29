---
status: superseded in part by 0017 (permissions apply inside the lookup, before the limit)
date: 2026-10-28
---
<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

# Check permissions before answers, counts and pages

> **Superseded in part** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): permissions now apply inside the index lookup, before the 1,000-passage limit, not after it. The rest of this record stands.

**Serves:** [R1](../constraints/requirements.md#r1) (no information from a document that the user cannot read), [U1](../constraints/use-case.md#u1) (a *selected* manager or lead).

## Context

The use case is for selected users ([U1](../constraints/use-case.md#u1)), and documents in the repository have different readers. A user must never get information from a document that the user cannot read ([R1](../constraints/requirements.md#r1)). Information is more than text: a count, a file name, an empty result position or a page total can also show that a forbidden document matches. If the service picks a page of results first and removes forbidden passages after, the counts and the gaps leak information, and permitted results can be lost.

## Decision

- After the index lookup and before anything else, decide which matched files the user can read. Everything after that step uses permitted files only: the answer, the "also stated in" list, the document list, the counts, the pages and the file overview.
- Check permissions again on every request, including each page. A page number is not permission to read.
- Reading one file gives the same reply for "does not exist" and "not permitted", so file names do not leak.
- If the permission check fails, return no evidence (fail closed).
- A search match that is excluded by permissions is recorded in the audit log. It is a different event from a deliberate attempt to open a forbidden file.

## Consequences

- Counts and pages are correct for each user and show nothing about forbidden files.
- Pages are live views. If the index or the permissions change between two pages, results can move. The service never freezes permissions to keep pages stable.
- Two exceptions are recorded in [`access.py`](../../engineering_search/access.py): the sign-in screen shows folder counts for each demo user (no names, no text), and the audit log shows file names to the index team ([ADR 0008](0008-index-team-and-audit-viewer.md)).

## Implementation

Done. `SearchService.search` and `SearchService.read` in [`service.py`](../../engineering_search/service.py). The service finds the matching files, evaluates permissions on them, and gives the index lookup the set of permitted files (and `within`). The lookup ([`store.py`](../../engineering_search/store.py)) applies that set inside the FTS5 query, before the 1,000-candidate limit, so forbidden passages cannot push permitted ones out. The SQL path builds a projection of permitted files only ([ADR 0016](0016-structured-facts-and-client-written-sql.md)). `POST /search` takes `page` and `limit` (at most 50). Tests: `tests/test_no_leaks.py` asks every evaluation question, and questions made from the text of each forbidden file, in each mode, for each user, and checks the first five pages and the last page. Also `test_forbidden_passages_cannot_push_a_permitted_passage_past_the_candidate_limit` in `tests/test_binding.py`, `tests/test_sql.py`, `tests/test_access.py`, `tests/test_pagination.py` and `tests/test_use_case.py`.
