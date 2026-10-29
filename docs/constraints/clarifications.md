# Clarifications (K)

Where the brief is open, the product owner's answers. [K1](#k1)–[K12](#k12) and [K16](#k16) come from the questions on the brief (October 2026); [K13](#k13)–[K15](#k15) were set while the MVP was built. Each names the brief items it clarifies.

| ID | Clarification | Clarifies |
| --- | --- | --- |
| [K1](#k1) | The speed, the scale and the confidence are one use case | [U3](use-case.md#u3), [U4](use-case.md#u4), [U5](use-case.md#u5) |
| [K2](#k2) | The time boxes are not targets; the outcome is | [T1](task.md#t1)–[T5](task.md#t5) |
| [K3](#k3) | A source is the file on disc as it is now; an answer names the file, the location and the quoted evidence | [U5](use-case.md#u5), [C2](constraints.md#c2) |
| [K4](#k4) | The answer carries enough evidence not to open the file | [U6](use-case.md#u6) |
| [K5](#k5) | "Selected" means an authorised pilot group | [U1](use-case.md#u1) |
| [K6](#k6) | 10 seconds end to end, for 95% of queries, measured | [U4](use-case.md#u4) |
| [K7](#k7) | The readers and extraction rules are labelled sample stand-ins | [C3](constraints.md#c3) |
| [K8](#k8) | Structured tables and lexical full-text search; semantic search is out of scope | [C4](constraints.md#c4) |
| [K9](#k9) | The user never writes SQL; the chat agent may | [B4](background.md#b4), [C5](constraints.md#c5) |
| [K10](#k10) | 100+ documents across all the projects the user may read | [U3](use-case.md#u3) |
| [K11](#k11) | The initial phase is a potential solution; the diagram comes from it | [T3](task.md#t3), [T4](task.md#t4), [T5](task.md#t5) |
| [K12](#k12) | Files are read from the repository, never uploaded | [C2](constraints.md#c2) |
| [K13](#k13) | A user never gets information from a document they may not read | [U1](use-case.md#u1) |
| [K14](#k14) | An answer, not a list of passages; lists only for "which documents" | [U2](use-case.md#u2) |
| [K15](#k15) | Project data is in project folders on a file system | [C2](constraints.md#c2) |
| [K16](#k16) | The index is refreshed on start and on request, re-reading only changed files | [C2](constraints.md#c2), [U5](use-case.md#u5) |

<a id="k1"></a>

## K1. The speed, the scale and the confidence are one use case

Under 10 seconds, across 100+ documents, with 100% confidence in the source, are all part of the use case, not additions to it.

<a id="k2"></a>

## K2. The time boxes are not targets

The minutes in the task (5, 10, 40) are ignored. The goal is the outcome: the MVP.

<a id="k3"></a>

## K3. A source is the file on disc as it is now

Every answer names the file, the location in it and the quoted evidence. There is no versioning system: the file on disc is what it is, and the system never decides whether it is a "current" or "approved" revision. What "refuses rather than guesses" means: if a cited file has changed (or gone) since it was indexed, its evidence is refused, not quoted, until the index is refreshed. The content fingerprint (a SHA-256 of the file's bytes) shows the change.

**Implemented by:** `SearchService.changed_on_disc` in [`service.py`](../../engineering_search/service.py). **Tested by:** [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py). **Decisions:** [ADR 0003](../adr/0003-quote-the-source-and-refuse-rather-than-guess.md), [ADR 0007](../adr/0007-the-source-is-the-file-on-disc.md).

<a id="k4"></a>

## K4. The answer carries enough evidence not to open the file

The quoted sentence or row, with its heading, page and lines, is enough to act on.

<a id="k5"></a>

## K5. "Selected" means an authorised pilot group

Not one named person: a group allowed to use the pilot. JP and Kamal are example users with access to different projects.

<a id="k6"></a>

## K6. 10 seconds end to end, for 95% of queries, measured

The target is end to end, as the user sees it. Everything is instrumented; 95% of queries must finish within 10 seconds. Recording slow queries for later analysis is out of scope ([O2](gaps.md#o2)).

<a id="k7"></a>

## K7. The readers and extraction rules are labelled sample stand-ins

The readers and the fact rules stand in for the connectors' output, to prove the use case. They are recorded in one decision ([ADR 0001](../adr/0001-prove-the-use-case-with-stand-in-readers.md)).

<a id="k8"></a>

## K8. Structured tables and lexical full-text search

"and/or" is our choice. The MVP uses structured tables and lexical full-text search. Semantic search (embeddings) is out of scope ([O1](gaps.md#o1)).

<a id="k9"></a>

## K9. The user never writes SQL; the chat agent may

The user does not write SQL. A question that is a SQL statement is refused, by `POST /search` and by the MCP tool `search_evidence`, with a request for a plain-language question. The rule binds the user only: the chat agent may write constrained SQL ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)). The MCP instructions tell the agent never to pass SQL written by the user into `query_sql`; the service cannot check who wrote a statement ([G7](gaps.md#g7)).

**Implemented by:** `is_sql_statement` in [`sql.py`](../../engineering_search/sql.py), [`mcp_server.py`](../../engineering_search/mcp_server.py) instructions. **Tested by:** [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py).

<a id="k10"></a>

## K10. 100+ documents across all the projects the user may read

One question searches every document the user may read, across projects. The test set has at least 100 documents across several projects.

<a id="k11"></a>

## K11. The initial phase is a potential solution

"Define the initial phase" means a potential solution, given the background, the use case and the constraints. The system design diagram is drawn from it. The MVP is the working prototype of it.

<a id="k12"></a>

## K12. Files are read from the repository, never uploaded

The files live in the existing repository ([C2](constraints.md#c2)). The system reads them there; it has no upload path.

<a id="k13"></a>

## K13. A user never gets information from a document they may not read

An absolute requirement. Information includes a count, a file name, a ranking or a join, not only text. Permissions apply before limits, ranking, counts, joins and aggregates ([ADR 0004](../adr/0004-permissions-before-ranking-limits-and-counts.md)).

**Tested by:** [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py), [`tests/test_access.py`](../../tests/test_access.py), [`tests/test_sql.py`](../../tests/test_sql.py).

<a id="k14"></a>

## K14. An answer, not a list of passages

The service answers the question: one value with its source, or a clear statement that no readable document states it. "Which documents…" questions get a list of documents, each with the line that qualifies it, and can be followed up ("of those, which…").

<a id="k15"></a>

## K15. Project data is in project folders on a file system

The repository is a file system with a folder per project. Access is granted by folder and file ([G1](gaps.md#g1)).

<a id="k16"></a>

## K16. The index is refreshed on start and on request

The indexer hashes every file and re-reads only new and changed files; files deleted from disc are removed from the index. It runs when the service starts and when the index team asks. There is no timer: with [K3](#k3), a changed file is refused rather than quoted stale. Automatic refresh is part of [G5](gaps.md#g5).
