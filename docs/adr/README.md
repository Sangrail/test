# Architecture decision records


These records explain the decisions of the MVP, and how each one serves the intent, the constraints and the scope. They are generated from the design records database, [docs/records/design.sqlite](../records/README.md), which is the source of truth and keeps every version of every record ([ADR 0021](0021-design-records-in-one-database.md)). **Accepted** means that the direction is agreed. It does not mean that every part is implemented: each record has an "Implementation" section that says what the code does now.

## Intent, constraints and scope

Each record links the items it serves, those it knowingly leaves unmet, and the scope items it goes beyond. The items are in [docs/constraints](../constraints/README.md), each with its pillar (intent, constraint or scope), its source, where the MVP stands and its history.

| Group | Items |
| --- | --- |
| [Background](../constraints/background.md) | [B1](../constraints/background.md#b1)–[B2](../constraints/background.md#b2): Years of design information in files and documents; Users do not know which files hold the answer |
| [Constraints from the brief](../constraints/environment.md) | [C1](../constraints/environment.md#c1)–[C5](../constraints/environment.md#c5): A broader architecture direction already exists; The files live in an existing repository; Connectors extract metadata, text and properties; Structured and/or semantic stores; A chat-agent shell calls backend APIs or tools |
| [Use case](../constraints/use-case.md) | [U1](../constraints/use-case.md#u1)–[U6](../constraints/use-case.md#u6): Find a critical engineering parameter; Across 100+ project documents; In under 10 seconds; With 100% confidence in the source; Without opening a design file or viewer; No formats, schema, query languages or jargon |
| [Task](../constraints/task.md) | [T1](../constraints/task.md#t1)–[T3](../constraints/task.md#t3): Identify and clarify the requirements, gaps and challenges; Define the initial phase and a system design diagram; A working prototype of an MVP |
| [Scope](../constraints/scope.md) | [S1](../constraints/scope.md#s1)–[S6](../constraints/scope.md#s6): An MVP, not the final platform; Markdown and simple PDF, no OCR, no CAD; Synthetic or public test documents; The 29 October design inputs; Extraction is the connectors' job; Not a distributed system |
| [Requirements and constraints added during the MVP](../constraints/requirements.md) | [R1](../constraints/requirements.md#r1)–[R8](../constraints/requirements.md#r8): No information from a forbidden document; An answer, not a list of passages; Lists of documents, with follow-ups; The tests enforce the use case; Answers in under 10 seconds across hundreds of files; Several users at the same time; Project data lives on a file system, in project folders; Users cannot see inside folders they are not authorised for |
| [Production requirements](../constraints/production.md) | [P1](../constraints/production.md#p1)–[P6](../constraints/production.md#p6): Any number of users, each answered within 10 seconds; Verified identity; Permissions from the repository; Durable, protected audit; Approved use of language models; Quality measured on real questions |

## Records

**Status** is the state of the decision: *accepted*, *amended* (still in force, with changes recorded in a later record) or *superseded in part* (the named part is replaced by a later record; the rest stands). **Version** counts the changes to the record; each page ends with its history.

| Record | Decision | Links | Status | Version | Implementation |
| --- | --- | --- | --- | --- | --- |
| [0001](0001-mvp-format-scope.md) | Markdown and text-layer PDF are the MVP formats | [S1](../constraints/scope.md#s1)–[S2](../constraints/scope.md#s2), [U5](../constraints/use-case.md#u5); exceeds scope: [S5](../constraints/scope.md#s5) | Superseded in part by 0016 (CSV and XLSX are read); amended by 0020 (the readers are stand-ins for connectors) | 3 | Done. CSV and XLSX added by 0016. The readers are stand-ins (0020) |
| [0002](0002-independent-local-instances.md) | Each tester runs an independent local instance | [S1](../constraints/scope.md#s1), [S3](../constraints/scope.md#s3), [C2](../constraints/environment.md#c2), [S6](../constraints/scope.md#s6); not met: [P1](../constraints/production.md#p1) | Accepted | 2 | Done |
| [0003](0003-versioned-reader-selection.md) | Select and record a tested reader for each format and version | [C2](../constraints/environment.md#c2)–[C3](../constraints/environment.md#c3), [U4](../constraints/use-case.md#u4); exceeds scope: [S5](../constraints/scope.md#s5) | Accepted, amended by 0020 (the readers are stand-ins for connectors) | 3 | Mostly done. Content detection, reader registry, reader version stored. No CAD reader |
| [0004](0004-persistent-evidence.md) | Store extracted passages with their source version | [U3](../constraints/use-case.md#u3)–[U5](../constraints/use-case.md#u5) | Accepted | 1 | Done |
| [0005](0005-coverage-and-reader-gaps.md) | Report files that cannot be read | [C2](../constraints/environment.md#c2)–[C3](../constraints/environment.md#c3), [U4](../constraints/use-case.md#u4) | Accepted, amended by 0020 (the readers are stand-ins for connectors) | 2 | Done. Stored statuses and a coverage report for the index team |
| [0006](0006-permissions-before-results.md) | Check permissions before answers, counts and pages | [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Superseded in part by 0017 (permissions apply inside the lookup, before the limit) | 1 | Done |
| [0007](0007-telemetry-and-audit.md) | Telemetry and an audit record before evidence is released | [U3](../constraints/use-case.md#u3)–[U4](../constraints/use-case.md#u4), [R1](../constraints/requirements.md#r1); not met: [P4](../constraints/production.md#p4) | Accepted | 1 | Done |
| [0008](0008-index-team-and-audit-viewer.md) | Search users and the index team are separate roles | [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Accepted | 1 | Done |
| [0009](0009-sqlite-fts5-index-and-answers.md) | SQLite FTS5 inverted index. Answers are exact text | [U1](../constraints/use-case.md#u1)–[U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R2](../constraints/requirements.md#r2)–[R3](../constraints/requirements.md#r3) | Accepted, amended by 0017 (bound list comparisons, signed numbers, list paging) | 1 | Done |
| [0010](0010-path-based-access-rules.md) | Index the whole repository. Folder and file access rules | [R1](../constraints/requirements.md#r1), [C2](../constraints/environment.md#c2), [U2](../constraints/use-case.md#u2), [R7](../constraints/requirements.md#r7)–[R8](../constraints/requirements.md#r8); not met: [P3](../constraints/production.md#p3) | Accepted | 2 | Done |
| [0011](0011-one-search-service.md) | One search service for the web page, the API and the MCP server | [C1](../constraints/environment.md#c1), [C5](../constraints/environment.md#c5), [R1](../constraints/requirements.md#r1), [U4](../constraints/use-case.md#u4) | Accepted | 1 | Done |
| [0012](0012-mcp-server-for-the-chat-agent.md) | A stdio MCP server is the chat-agent interface | [C5](../constraints/environment.md#c5), [U6](../constraints/use-case.md#u6), [S1](../constraints/scope.md#s1), [R1](../constraints/requirements.md#r1); not met: [P2](../constraints/production.md#p2), [P5](../constraints/production.md#p5) | Superseded in part by 0016 (the tools) and 0018 (admission); stdio and the identity hole stand | 1 | Done. Verified with Claude Code, Codex and Pi. Identity is a known security hole |
| [0013](0013-no-answer-before-a-wrong-answer.md) | Give no answer before a wrong answer | [U4](../constraints/use-case.md#u4), [R2](../constraints/requirements.md#r2), [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Superseded in part by 0017 (binding and the unverified status) | 1 | Done |
| [0014](0014-defer-facts-store-and-embeddings.md) | Defer the facts store and embeddings | [S1](../constraints/scope.md#s1), [C3](../constraints/environment.md#c3)–[C4](../constraints/environment.md#c4), [U1](../constraints/use-case.md#u1) | Superseded in part by 0016 | 1 | Embeddings and facts from prose still deferred |
| [0015](0015-acceptance-tests-enforce-the-use-case.md) | Acceptance tests enforce the use case on a public test repository | [R4](../constraints/requirements.md#r4), [U1](../constraints/use-case.md#u1)–[U5](../constraints/use-case.md#u5), [R1](../constraints/requirements.md#r1), [S3](../constraints/scope.md#s3) | Superseded in part by 0019 (evaluation); the acceptance tests stand | 1 | Done |
| [0016](0016-structured-facts-and-client-written-sql.md) | Read tables into typed facts at index time. The MCP client writes constrained SQL | [U1](../constraints/use-case.md#u1)–[U2](../constraints/use-case.md#u2), [U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R1](../constraints/requirements.md#r1), [R3](../constraints/requirements.md#r3), [C3](../constraints/environment.md#c3)–[C5](../constraints/environment.md#c5), [S4](../constraints/scope.md#s4); exceeds scope: [S5](../constraints/scope.md#s5) | Accepted | 2 | Done for CSV, XLSX and Markdown tables |
| [0017](0017-bind-answers-and-permit-before-the-limit.md) | Bind each answer to its subject. Apply permissions before the retrieval limit | [U4](../constraints/use-case.md#u4), [R1](../constraints/requirements.md#r1)–[R3](../constraints/requirements.md#r3) | Accepted | 1 | Done |
| [0018](0018-admission-control-and-the-time-budget.md) | Answer within the time budget or refuse at once. Record what does not scale | [U3](../constraints/use-case.md#u3)–[U4](../constraints/use-case.md#u4), [C5](../constraints/environment.md#c5), [S1](../constraints/scope.md#s1), [R5](../constraints/requirements.md#r5)–[R6](../constraints/requirements.md#r6), [S6](../constraints/scope.md#s6); not met: [P1](../constraints/production.md#p1) | Accepted (MVP; the scaling work is open) | 2 | Admission control done. Scaling work not started |
| [0019](0019-evaluate-retrieval-and-nl-to-sql.md) | Evaluate retrieval, natural language to SQL and the agent's reply. Gate releases on them | [U1](../constraints/use-case.md#u1), [U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R1](../constraints/requirements.md#r1), [R4](../constraints/requirements.md#r4); not met: [P6](../constraints/production.md#p6) | Accepted (partly implemented) | 1 | Partial. Retrieval evaluation and the SQL gold set. No live-client harness |
| [0020](0020-assume-the-environment-and-stand-in-for-it.md) | The environment in the brief exists. The readers, folder, stores and chat clients in the MVP are stand-ins for it | [C1](../constraints/environment.md#c1)–[C5](../constraints/environment.md#c5), [S1](../constraints/scope.md#s1) | Accepted | 1 | Done in the documents. No code change |
| [0021](0021-design-records-in-one-database.md) | One versioned SQLite database is the source of truth for intent, constraints, scope and decisions. The pages and a browser view are generated from it at commit time; an MCP server reads it and proposes drafts | [T1](../constraints/task.md#t1), [R4](../constraints/requirements.md#r4) | Accepted (to be evaluated after a few changes) | 2 | Done. Versioned database, generator, pre-commit hook, check in the suite, MCP server that proposes drafts, self-contained browser view |

## Needs review

None: every decision has been made, or reviewed, under the current wording of the items it links.

## Recent changes

| Date | Record | Version | Change |
| --- | --- | --- | --- |
| 2026-10-29 | ADR 0021 | 2 | The product owner made the database the source of truth, with history, generated documents, a pre-commit hook and an MCP server that proposes drafts. |
| 2026-10-29 | [R5](../constraints/requirements.md#r5) | 1 | Added by the product owner: response time is a constraint, not only a use-case wish. |
| 2026-10-29 | [R6](../constraints/requirements.md#r6) | 1 | Added by the product owner: concurrent use is a constraint. |
| 2026-10-29 | [R7](../constraints/requirements.md#r7) | 1 | Added by the product owner: where the data lives is a real constraint. |
| 2026-10-29 | [R8](../constraints/requirements.md#r8) | 1 | Added by the product owner: folder authorisation is a real constraint. |
| 2026-10-29 | [S5](../constraints/scope.md#s5) | 1 | Added by the product owner: the readers go beyond the scope, because the brief says connectors exist. |
| 2026-10-29 | [S6](../constraints/scope.md#s6) | 1 | Added by the product owner: scope says how far down the road the MVP goes, and it stops short of a distributed system. |
| 2026-10-29 | ADR 0001 | 3 | Record that the stand-in readers exceed scope [S5](../constraints/scope.md#s5). |
| 2026-10-29 | ADR 0002 | 2 | Link [S6](../constraints/scope.md#s6) (not a distributed system), which this decision serves. |
| 2026-10-29 | ADR 0003 | 3 | Record that reader selection for stand-in readers exceeds scope [S5](../constraints/scope.md#s5). |
| 2026-10-29 | ADR 0010 | 2 | Link [R7](../constraints/requirements.md#r7) (project folders) and [R8](../constraints/requirements.md#r8) (folder authorisation), which this decision serves. |
| 2026-10-29 | ADR 0016 | 2 | Record that extracting typed facts from tables exceeds scope [S5](../constraints/scope.md#s5). |
| 2026-10-29 | ADR 0018 | 2 | Link [R5](../constraints/requirements.md#r5) (under 10 s), [R6](../constraints/requirements.md#r6) (several users) and [S6](../constraints/scope.md#s6) (not distributed), which this decision serves. |
| 2026-10-29 | [B1](../constraints/background.md#b1) | 1 | Recorded from the background of the brief. |
| 2026-10-29 | [B2](../constraints/background.md#b2) | 1 | Recorded from the background of the brief. |

## Related documents

[docs/README.md](../README.md) says what the MVP is and is not. [docs/records/index.html](../records/index.html) shows the records and their history in a browser. [TODO](../../TODO.md) tracks delivery and gaps. [ARCHITECTURE](../../ARCHITECTURE.md) describes the code as it runs.

## Changing a decision

Change the database, never these pages: [docs/records/README.md](../records/README.md) shows how, with plain SQL in the `sqlite3` shell. The pre-commit hook regenerates the pages. Each change adds a version with its reason; earlier versions are kept. When a later decision replaces part of an earlier one, link the two and give the earlier one a new version with its new status.
