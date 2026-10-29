# Requirements added during the MVP (R)

Requirements that the product owner added while the MVP was built.

| ID | Constraint |
| --- | --- |
| [R1](#r1) | No information from a forbidden document |
| [R2](#r2) | An answer, not a list of passages |
| [R3](#r3) | Lists of documents, with follow-ups |
| [R4](#r4) | The tests enforce the use case |

<a id="r1"></a>

## R1. No information from a forbidden document

> A user must never get information from a document that the user is not authorised to read. This is an absolute requirement.

**Source:** Added during the MVP.

**What it means for the design:** Information is more than text: a count, a file name, a ranking or a join can leak too. Permissions apply before any limit, ranking, count, join or aggregate.

**Where the MVP stands:** Met in the tests on both paths. It rests on pretend sign-in and an unverified MCP user, so it is a demonstration until [P2](production.md#p2) and [P3](production.md#p3) are met.

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

<a id="r2"></a>

## R2. An answer, not a list of passages

> The service must answer the question. A list of passages is not an answer.

**Source:** Added during the MVP.

**What it means for the design:** Select one value with its source, or say clearly that no readable document states it.

**Where the MVP stands:** One sentence or row with a status (found, unverified, partial, not found), or rows from SQL.

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0013](../adr/0013-no-answer-before-a-wrong-answer.md): Give no answer, or a partial answer, before a wrong answer
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit

<a id="r3"></a>

## R3. Lists of documents, with follow-ups

> Users can ask for lists of documents: by project, topic, material, approval status, or a value such as a load above 5 kN/m², with follow-up questions about a previous list.

**Source:** Added during the MVP.

**What it means for the design:** Lists must be complete within the user's permissions, paged, and filterable by value with units.

**Where the MVP stands:** Text lists with bound number comparisons and paging; complete filters over tables through SQL.

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository (cited)
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit

<a id="r4"></a>

## R4. The tests enforce the use case

> The tests must enforce the use case.

**Source:** Added during the MVP.

**What it means for the design:** Each part of the use case has a test that fails when it breaks. Quality is measured by evaluation, not by eye.

**Where the MVP stands:** Acceptance tests, a leak test, SQL and binding tests, a retrieval evaluation and an NL-to-SQL gold set. The live-client SQL evaluation is not built.

**Decisions:**

- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results
