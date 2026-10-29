# Use case (U)


The use case in the brief: who needs what, how fast and with what confidence. Each item is quoted or closely paraphrased from [the brief](../Starting_document.md).

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [U1](#u1) | Find a critical engineering parameter | intent | partly met | 1 |
| [U2](#u2) | Across 100+ project documents | intent | met | 1 |
| [U3](#u3) | In under 10 seconds | intent | partly met | 1 |
| [U4](#u4) | With 100% confidence in the source | intent | partly met | 1 |
| [U5](#u5) | Without opening a design file or viewer | intent | met | 1 |
| [U6](#u6) | No formats, schema, query languages or jargon | intent | met | 1 |

<a id="u1"></a>

## U1. Find a critical engineering parameter

> A selected engineering manager or lead can find a critical engineering parameter: a load limit, a material specification or a compliance approval status.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), use case.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** The questions are about specific parameters, not general reading. Values must be bound to the element they describe. *Selected* means the users are known and their access differs.

**Where the MVP stands:** Load limits, materials and approval statuses are answered from text (with a binding status) and from table facts through SQL. Only a small, fixed set of parameters is recognised.

**Enforced by:** [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Measured by:** [`evaluation/questions.json`](../../evaluation/questions.json), [`scripts/evaluate.py`](../../scripts/evaluate.py).

**Decisions:**

- [ADR 0006](../adr/0006-permissions-before-results.md): Check permissions before answers, counts and pages
- [ADR 0008](../adr/0008-index-team-and-audit-viewer.md): Keep search users and the index team separate
- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0013](../adr/0013-no-answer-before-a-wrong-answer.md): Give no answer, or a partial answer, before a wrong answer
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="u2"></a>

## U2. Across 100+ project documents

> The parameter is found across 100 or more project documents.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), use case.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Search must not depend on the user knowing which file to open. The system needs an index, not a scan.

**Where the MVP stands:** Met on 148 test files. Not measured on a real repository, which may hold hundreds of thousands of files.

**Enforced by:** [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="u3"></a>

## U3. In under 10 seconds

> The answer comes in under 10 seconds.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), use case.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** The time includes the network and the chat agent's language model, not only the search. It must hold for every user, not only for one.

**Where the MVP stands:** About 80 ms median per question for one user. Under load, admission control answers within 8 s or refuses at once with a retry time. One process answers about 10 requests a second. Holding 10 s for any number of users is [P1](production.md#p1).

**Enforced by:** [`tests/test_admission.py`](../../tests/test_admission.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Measured by:** [`scripts/load_test.py`](../../scripts/load_test.py).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (cited)
- [ADR 0004](../adr/0004-persistent-evidence.md): Store extracted passages with their source version
- [ADR 0007](../adr/0007-telemetry-and-audit.md): Measure from the start, and audit before evidence is released
- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="u4"></a>

## U4. With 100% confidence in the source

> The user has 100% confidence in the source of the answer.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), use case.

**Standing:** *partly met*. Met in part. Where the MVP stands says what is missing.

**What it means for the design:** Every answer cites the exact file, location and version, and the cited text must really be in the file. The system must prefer no answer to a wrong one, and say how well the value is bound to the question.

**Where the MVP stands:** Every answer and row carries file, page or sheet, lines and SHA-256 version, checked against the files by tests. The source is proven; that the value is the current, approved one is not.

**Enforced by:** [`tests/test_binding.py`](../../tests/test_binding.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Measured by:** [`scripts/evaluate.py`](../../scripts/evaluate.py).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF (cited)
- [ADR 0003](../adr/0003-versioned-reader-selection.md): Select a tested reader for each format and version, and record it
- [ADR 0004](../adr/0004-persistent-evidence.md): Store extracted passages with their source version
- [ADR 0005](../adr/0005-coverage-and-reader-gaps.md): Report the files that cannot be read
- [ADR 0007](../adr/0007-telemetry-and-audit.md): Measure from the start, and audit before evidence is released
- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0011](../adr/0011-one-search-service.md): Put all search logic in one service, used by the web page and the chat agent
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (cited)
- [ADR 0013](../adr/0013-no-answer-before-a-wrong-answer.md): Give no answer, or a partial answer, before a wrong answer
- [ADR 0014](../adr/0014-defer-facts-store-and-embeddings.md): Defer the facts store and embeddings until the questions and the data are known (cited)
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0017](../adr/0017-bind-answers-and-permit-before-the-limit.md): Bind each answer to its subject, and apply permissions before the retrieval limit
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="u5"></a>

## U5. Without opening a design file or viewer

> The user does not open a single design file (CAD) or tool (PDF viewer).

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), use case.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** The answer must carry its evidence: the exact text or row, with enough context to trust it.

**Where the MVP stands:** The answer shows the exact text or row and its location. There is no viewer for the context around a value, and no CAD content is read.

**Enforced by:** [`tests/test_use_case.py`](../../tests/test_use_case.py).

**Decisions:**

- [ADR 0001](../adr/0001-mvp-format-scope.md): Start with Markdown and simple text-layer PDF
- [ADR 0004](../adr/0004-persistent-evidence.md): Store extracted passages with their source version
- [ADR 0015](../adr/0015-acceptance-tests-enforce-the-use-case.md): Enforce the use case with acceptance tests on a public test repository

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.

<a id="u6"></a>

## U6. No formats, schema, query languages or jargon

> Users do not want to learn file formats, schema details, query languages or system-specific jargon.

**Pillar:** intent. **Source:** [The brief](../../docs/Starting_document.md), background.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Questions are in plain language. If a query language is needed, something other than the user writes it.

**Where the MVP stands:** Plain-language questions. For table questions, the chat agent's language model writes the SQL, not the user.

**Enforced by:** [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py).

**Measured by:** [`evaluation/sql_questions.json`](../../evaluation/sql_questions.json).

**Decisions:**

- [ADR 0009](../adr/0009-sqlite-fts5-index-and-answers.md): Use a SQLite FTS5 inverted index, and answer with exact text
- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only
- [ADR 0016](../adr/0016-structured-facts-and-client-written-sql.md): Read tables into typed facts at index time, and let the MCP client write constrained SQL
- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results

**History:**

- Version 1, from 2026-10-28, active. First recorded with the use case and the constraints of the brief.
