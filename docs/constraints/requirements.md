# Requirements and constraints added during the MVP (R)

<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

Requirements and constraints that the product owner added while the MVP was built. Each is marked with its pillar: intent or constraint.

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [R1](#r1) | No information from a forbidden document | constraint | partly met | 1 |
| [R2](#r2) | An answer, not a list of passages | intent | met | 1 |
| [R3](#r3) | Lists of documents, with follow-ups | intent | met | 1 |
| [R4](#r4) | The tests enforce the use case | constraint | partly met | 1 |
| [R5](#r5) | Answers in under 10 seconds across hundreds of files | constraint | met | 1 |
| [R6](#r6) | Several users at the same time | constraint | partly met | 1 |
| [R7](#r7) | Project data lives on a file system, in project folders | constraint | met | 1 |
| [R8](#r8) | Users cannot see inside folders they are not authorised for | constraint | partly met | 1 |

<a id="r1"></a>

## R1. No information from a forbidden document

> A user must never get information from a document that the user is not authorised to read. This is an absolute requirement.

**Pillar:** constraint. **Source:** A decision during the MVP.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** Information is more than text: a count, a file name, a ranking or a join can leak too. Permissions apply before any limit, ranking, count, join or aggregate.

**Where the MVP stands:** Met in the tests on both paths. It rests on pretend sign-in and an unverified MCP user, so it is a demonstration until [P2](production.md#p2) and [P3](production.md#p3) are met.

**Enforced by:** [`tests/test_access.py`](../../tests/test_access.py), [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py), [`tests/test_sql.py`](../../tests/test_sql.py).

**Decisions:**

- [ADR 0006](../adr/0006-permissions-before-results.md): Check permissions before answers, counts and pages
- [ADR 0007](../adr/0007-telemetry-and-audit.md): Measure from the start, and audit before evidence is released
- [ADR 0008](../adr/0008-index-team-and-audit-viewer.md): Keep search users and the index team separate
- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules
- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0013](../adr/0013-no-answer-before-a-wrong-answer.md): Give no answer, or a partial answer, before a wrong answer
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results
- [ADR 0021](../adr/0021-design-records-in-one-database.md): Keep intent, constraints, scope and decisions in one versioned SQLite database, the source of truth, and generate the documents from it (cited)

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="r2"></a>

## R2. An answer, not a list of passages

> The service must answer the question. A list of passages is not an answer.

**Pillar:** intent. **Source:** A decision during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Select one value with its source, or say clearly that no readable document states it.

**Where the MVP stands:** One sentence or row with a status (found, unverified, partial, not found), or rows from SQL.

**Enforced by:** [`tests/test_binding.py`](../../tests/test_binding.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0013](../adr/0013-no-answer-before-a-wrong-answer.md): Give no answer, or a partial answer, before a wrong answer
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="r3"></a>

## R3. Lists of documents, with follow-ups

> Users can ask for lists of documents: by project, topic, material, approval status, or a value such as a load above 5 kN/m², with follow-up questions about a previous list.

**Pillar:** intent. **Source:** A decision during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Lists must be complete within the user's permissions, paged, and filterable by value with units.

**Where the MVP stands:** Text lists with bound number comparisons and paging; complete filters over tables through SQL.

**Enforced by:** [`tests/test_pagination.py`](../../tests/test_pagination.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository (cited)
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="r4"></a>

## R4. The tests enforce the use case

> The tests must enforce the use case.

**Pillar:** constraint. **Source:** A decision during the MVP.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** Each part of the use case has a test that fails when it breaks. Quality is measured by evaluation, not by eye.

**Where the MVP stands:** Acceptance tests, a leak test, SQL and binding tests, a retrieval evaluation and an NL-to-SQL gold set. The live-client SQL evaluation is not built.

**Enforced by:** [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Decisions:**

- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results
- [ADR 0021](../adr/0021-design-records-in-one-database.md): Keep intent, constraints, scope and decisions in one versioned SQLite database, the source of truth, and generate the documents from it

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="r5"></a>

## R5. Answers in under 10 seconds across hundreds of files

> The response time must be under 10 seconds when the repository holds hundreds of files.

**Pillar:** constraint. **Source:** The product owner, during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Search must not scan files per question: an index, built ahead of the question, and a time budget per request.

**Where the MVP stands:** About 80 ms median per question on 148 files in one process; under load, admission control answers within 8 s or refuses at once (ADR 0018). Not measured on hundreds of real files.

**Decisions:**

- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: response time is a constraint, not only a use-case wish.

<a id="r6"></a>

## R6. Several users at the same time

> The system must allow several users to use it at the same time.

**Pillar:** constraint. **Source:** The product owner, during the MVP.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** Requests from different users must not block each other indefinitely, and each must be answered within the time limit or told when to retry.

**Where the MVP stands:** One process answers about 10 requests a second, one at a time. Admission control answers each request within 8 s or refuses it at once with a retry time. Serving any number of users is [P1](production.md#p1), and a distributed system is out of scope ([S6](scope.md#s6)).

**Decisions:**

- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: concurrent use is a constraint.

<a id="r7"></a>

## R7. Project data lives on a file system, in project folders

> The data lives on a file system, and projects are organised in folders.

**Pillar:** constraint. **Source:** The product owner, during the MVP.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Files are found by walking folders; a file is identified by its path; the folder is the natural unit of permission and of project.

**Where the MVP stands:** The test repository is a folder per project, file IDs are paths, and access rules apply to folders and their files (ADR 0010). A local folder stands in for the real file system ([C2](environment.md#c2)).

**Decisions:**

- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: where the data lives is a real constraint.

<a id="r8"></a>

## R8. Users cannot see inside folders they are not authorised for

> Users are not permitted to see within folders that they are not authorised to see, so the system needs authorisation.

**Pillar:** constraint. **Source:** The product owner, during the MVP.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** Every result, count, list and join is limited to the folders the user may read, before any limit or ranking (with [R1](requirements.md#r1)). The user must be known ([P2](production.md#p2)), and the permissions must be the file system's own ([P3](production.md#p3)).

**Where the MVP stands:** Folder rules in access.py are applied before search, counts, SQL and evidence, and the tests prove no leak. They stand in for the file system's permissions, and the user is not verified.

**Decisions:**

- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules

**History:**

- Version 1, from 2026-10-29, active. Added by the product owner: folder authorisation is a real constraint.
