---
status: accepted
date: 2026-10-28
---
# Check permissions before answers, counts and pages

**Serves:** R1 (no information from a document that the user cannot read), U1 (a *selected* manager or lead).

## Context

The use case is for selected users (U1), and documents in the repository have different readers. A user must never get information from a document that the user cannot read (R1). Information is more than text: a count, a file name, an empty result position or a page total can also show that a forbidden document matches. If the service picks a page of results first and removes forbidden passages after, the counts and the gaps leak information, and permitted results can be lost.

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

Done, with a known defect. `SearchService.search` and `SearchService.read` in [`service.py`](../../engineering_search/service.py). `POST /search` takes `page` and `limit` (at most 50). Tests: `tests/test_no_leaks.py` asks every evaluation question, and questions made from the text of each forbidden file, in each mode, for each user. It checks the first five pages of 50 passages, not every page. It also names forbidden files in follow-up questions and tries to read them directly. Also `tests/test_access.py`, `tests/test_pagination.py` and `tests/test_use_case.py`.

**Known defect.** The index lookup ([`store.py`](../../engineering_search/store.py), `CANDIDATE_LIMIT`) keeps the 1,000 best passages from all files before the permission check and before `within`. This breaks the context of this decision: forbidden passages that rank higher can push permitted passages out, so permitted results are lost and forbidden files change what a user sees. A response still contains no forbidden text, names or counts. The tests do not check that adding forbidden files leaves a user's results unchanged. See [TODO.md](../../TODO.md#known-defects-fix-first).
