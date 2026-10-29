# Use case (U)

> We want a selected engineering manager or lead to be able to find a critical engineering parameter (e.g., a load limit, a material specification, or a compliance approval status) across 100+ project documents in under 10 seconds, with 100% confidence in the source, without opening a single design file (CAD) or tool (PDF viewer).

The six parts are one use case ([K1](clarifications.md#k1)): an answer that is fast but unsourced, or sourced but slow, does not meet it. [`tests/test_use_case.py`](../../tests/test_use_case.py) checks all six together on the test repository.

| ID | Item | Standing |
| --- | --- | --- |
| [U1](#u1) | A selected engineering manager or lead | partly met |
| [U2](#u2) | Finds a critical engineering parameter: a load limit, a material specification or an approval status | met |
| [U3](#u3) | Across 100+ project documents | met |
| [U4](#u4) | In under 10 seconds | met for one process; see [G5](gaps.md#g5) |
| [U5](#u5) | With 100% confidence in the source | met on the test data; see [G4](gaps.md#g4) |
| [U6](#u6) | Without opening a design file (CAD) or a tool (PDF viewer) | met |

<a id="u1"></a>

## U1. A selected engineering manager or lead

> "a selected engineering manager or lead"

**For the design:** "selected" means an authorised pilot group ([K5](clarifications.md#k5)). Each user sees only the projects they may read, and gets nothing from the others ([K13](clarifications.md#k13)).

**In the MVP:** demo users JP and Kamal (readers of different projects) and Maya (index team) sign in by choosing a name. Permissions apply before ranking, limits and counts ([ADR 0004](../adr/0004-permissions-before-ranking-limits-and-counts.md)). **Missing:** verified identity and the repository's own access controls ([G1](gaps.md#g1)).

**Tested by:** [`tests/test_access.py`](../../tests/test_access.py), [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py), [`tests/test_sql.py`](../../tests/test_sql.py).

<a id="u2"></a>

## U2. Finds a critical engineering parameter

> "find a critical engineering parameter (e.g., a load limit, a material specification, or a compliance approval status)"

**For the design:** the answer is the value, not a list of passages ([K14](clarifications.md#k14)). The three examples are the three kinds the tests ask for.

**In the MVP:** one quoted sentence or table row with a status (found, unverified, partial, not found), a list of documents for "which documents" questions, or rows from agent-written SQL. Load limits, material grades and approval statuses are asked of Markdown, PDF, CSV, XLSX and the title block of a DXF drawing.

**Tested by:** [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_binding.py`](../../tests/test_binding.py), [`tests/test_dxf.py`](../../tests/test_dxf.py).

<a id="u3"></a>

## U3. Across 100+ project documents

> "across 100+ project documents"

**For the design:** every document the user may read, across all their projects, is searched in one question ([K10](clarifications.md#k10)).

**In the MVP:** the test repository has 145 files with a reader across several projects. A list answer is paged at 200 documents.

**Tested by:** [`tests/test_indexer.py`](../../tests/test_indexer.py) (counts), [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_pagination.py`](../../tests/test_pagination.py).

<a id="u4"></a>

## U4. In under 10 seconds

> "in under 10 seconds"

**For the design:** 10 seconds end to end, for 95% of queries, measured ([K6](clarifications.md#k6)). The service has a budget of 8 s and refuses at once a request it cannot answer in time, leaving 2 s for the network and the chat shell ([ADR 0008](../adr/0008-a-time-budget-and-admission-control.md)).

**In the MVP:** every acceptance question is answered in well under a second on the test repository; the telemetry reports p95. **Missing:** holding this for any number of users ([G5](gaps.md#g5)).

**Tested by:** [`tests/test_use_case.py`](../../tests/test_use_case.py) (each request under 10 s), [`tests/test_admission.py`](../../tests/test_admission.py); measured by [`scripts/load_test.py`](../../scripts/load_test.py).

<a id="u5"></a>

## U5. With 100% confidence in the source

> "with 100% confidence in the source"

**For the design:** every answer names the file, the location in it and the quoted evidence ([K3](clarifications.md#k3)). The quote is copied, never written. When the system cannot bind a value to the question, or the cited file has changed since it was indexed, it refuses rather than guesses ([ADR 0003](../adr/0003-quote-the-source-and-refuse-rather-than-guess.md)).

**In the MVP:** each source has file, page, lines, the quoted text and the file's content fingerprint. The tests read the files themselves and check that each cited line holds the quoted text. **Missing:** proof on real questions ([G4](gaps.md#g4)).

**Tested by:** [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_binding.py`](../../tests/test_binding.py), [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py).

<a id="u6"></a>

## U6. Without opening a design file (CAD) or a tool (PDF viewer)

> "without opening a single design file (CAD) or tool (PDF viewer)"

**For the design:** the answer carries enough evidence that the user does not need to open the file ([K4](clarifications.md#k4)).

**In the MVP:** the answer quotes the sentence or row, with the heading, page and lines. A PDF calculation and a DXF drawing's title block are answered without opening either.

**Tested by:** [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_dxf.py`](../../tests/test_dxf.py).
