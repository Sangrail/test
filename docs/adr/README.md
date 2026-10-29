# Architecture decision records

These records explain the decisions of the MVP, and why each one serves the use case. **Accepted** means that the direction is agreed. It does not mean that every part is implemented: each record has an "Implementation" section that says what the code does now.

## The use case and the constraints

Each record cites the constraints it serves, linked to [docs/constraints](../constraints/README.md), where each one is stated with its source, what it means for the design and where the MVP stands. **Not met** names a production requirement that the record knowingly leaves open.

| Group | IDs |
| --- | --- |
| [Use case](../constraints/use-case.md) (from the brief) | U1–U6: find a critical parameter, across 100+ documents, in under 10 seconds, with 100% confidence in the source, without opening a file or viewer, without learning formats or query languages |
| [Constraints from the brief](../constraints/environment.md) | C1–C5: an existing architecture direction, an existing repository, connectors, structured and semantic stores, a chat-agent shell |
| [Scope](../constraints/scope.md) | S1–S4: an MVP only, the first formats, public test data, the 29 October design inputs |
| [Requirements added during the MVP](../constraints/requirements.md) | R1–R4: no information from forbidden documents, an answer not passages, lists with follow-ups, tests enforce the use case |
| [Production requirements](../constraints/production.md) (not met by the MVP) | P1–P6: any number of users within 10 seconds, verified identity, permissions from the repository, durable audit, approved language-model use, quality on real questions |

## Records

**Status** is the state of the decision: *accepted*, *amended* (still in force, with changes recorded in a later record) or *superseded in part* (the named part is replaced by a later record; the rest stands). No record is fully superseded.

| Record | Decision | Serves | Status | Implementation |
| --- | --- | --- | --- | --- |
| [0001](0001-mvp-format-scope.md) | Markdown and text-layer PDF are the MVP formats | [S1](../constraints/scope.md#s1), [S2](../constraints/scope.md#s2), [U5](../constraints/use-case.md#u5) | Superseded in part by 0016 | Done. CSV and XLSX added by 0016 |
| [0002](0002-independent-local-instances.md) | Each tester runs an independent local instance | [S1](../constraints/scope.md#s1), [S3](../constraints/scope.md#s3), [C2](../constraints/environment.md#c2); not met: [P1](../constraints/production.md#p1) | Accepted (MVP; a shared service needs 0018's scaling work) | Done |
| [0003](0003-versioned-reader-selection.md) | Select and record a tested reader for each format and version | [C2](../constraints/environment.md#c2), [C3](../constraints/environment.md#c3), [U4](../constraints/use-case.md#u4) | Accepted | Mostly done. Content detection, reader registry, reader version stored. No CAD reader |
| [0004](0004-persistent-evidence.md) | Store extracted passages with their source version | [U3](../constraints/use-case.md#u3), [U4](../constraints/use-case.md#u4), [U5](../constraints/use-case.md#u5) | Accepted | Done |
| [0005](0005-coverage-and-reader-gaps.md) | Report files that cannot be read | [C2](../constraints/environment.md#c2), [C3](../constraints/environment.md#c3), [U4](../constraints/use-case.md#u4) | Accepted | Done. Stored statuses and a coverage report for the index team |
| [0006](0006-permissions-before-results.md) | Check permissions before answers, counts and pages | [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Superseded in part by 0017 | Done |
| [0007](0007-telemetry-and-audit.md) | Telemetry and an audit record before evidence is released | [U3](../constraints/use-case.md#u3), [U4](../constraints/use-case.md#u4), [R1](../constraints/requirements.md#r1); not met: [P4](../constraints/production.md#p4) | Accepted | Done |
| [0008](0008-index-team-and-audit-viewer.md) | Search users and the index team are separate roles | [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Accepted | Done |
| [0009](0009-sqlite-fts5-index-and-answers.md) | SQLite FTS5 inverted index. Answers are exact text | [U1](../constraints/use-case.md#u1), [U2](../constraints/use-case.md#u2), [U3](../constraints/use-case.md#u3), [U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R2](../constraints/requirements.md#r2), [R3](../constraints/requirements.md#r3) | Amended by 0017 | Done |
| [0010](0010-path-based-access-rules.md) | Index the whole repository. Folder and file access rules | [R1](../constraints/requirements.md#r1), [C2](../constraints/environment.md#c2), [U2](../constraints/use-case.md#u2); not met: [P3](../constraints/production.md#p3) | Accepted | Done |
| [0011](0011-one-search-service.md) | One search service for the web page, the API and the MCP server | [C1](../constraints/environment.md#c1), [C5](../constraints/environment.md#c5), [R1](../constraints/requirements.md#r1), [U4](../constraints/use-case.md#u4) | Accepted | Done |
| [0012](0012-mcp-server-for-the-chat-agent.md) | A stdio MCP server is the chat-agent interface | [C5](../constraints/environment.md#c5), [U6](../constraints/use-case.md#u6), [S1](../constraints/scope.md#s1), [R1](../constraints/requirements.md#r1); not met: [P2](../constraints/production.md#p2), [P5](../constraints/production.md#p5) | Superseded in part by 0016 and 0018 | Done. Verified with Claude Code, Codex and Pi. Identity is a known security hole |
| [0013](0013-no-answer-before-a-wrong-answer.md) | Give no answer before a wrong answer | [U4](../constraints/use-case.md#u4), [R2](../constraints/requirements.md#r2), [R1](../constraints/requirements.md#r1), [U1](../constraints/use-case.md#u1) | Superseded in part by 0017 | Done |
| [0014](0014-defer-facts-store-and-embeddings.md) | Defer the facts store and embeddings | [S1](../constraints/scope.md#s1), [C3](../constraints/environment.md#c3), [C4](../constraints/environment.md#c4), [U1](../constraints/use-case.md#u1) | Superseded in part by 0016 | Embeddings and facts from prose still deferred |
| [0015](0015-acceptance-tests-enforce-the-use-case.md) | Acceptance tests enforce the use case on a public test repository | [R4](../constraints/requirements.md#r4), [U1](../constraints/use-case.md#u1)–[U5](../constraints/use-case.md#u5), [R1](../constraints/requirements.md#r1), [S3](../constraints/scope.md#s3) | Superseded in part by 0019 | Done |
| [0016](0016-structured-facts-and-client-written-sql.md) | Read tables into typed facts at index time. The MCP client writes constrained SQL | [U1](../constraints/use-case.md#u1), [U2](../constraints/use-case.md#u2), [U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R1](../constraints/requirements.md#r1), [R3](../constraints/requirements.md#r3), [C3](../constraints/environment.md#c3), [C4](../constraints/environment.md#c4), [C5](../constraints/environment.md#c5), [S4](../constraints/scope.md#s4) | Accepted | Done for CSV, XLSX and Markdown tables |
| [0017](0017-bind-answers-and-permit-before-the-limit.md) | Bind each answer to its subject. Apply permissions before the retrieval limit | [U4](../constraints/use-case.md#u4), [R1](../constraints/requirements.md#r1), [R2](../constraints/requirements.md#r2), [R3](../constraints/requirements.md#r3) | Accepted | Done |
| [0018](0018-admission-control-and-the-time-budget.md) | Answer within the time budget or refuse at once. Record what does not scale | [U3](../constraints/use-case.md#u3), [U4](../constraints/use-case.md#u4), [C5](../constraints/environment.md#c5), [S1](../constraints/scope.md#s1); not met: [P1](../constraints/production.md#p1) | Accepted | Admission control done. Scaling work not started |
| [0019](0019-evaluate-retrieval-and-nl-to-sql.md) | Evaluate retrieval, natural language to SQL and the agent's reply. Gate releases on them | [U1](../constraints/use-case.md#u1), [U4](../constraints/use-case.md#u4), [U6](../constraints/use-case.md#u6), [R1](../constraints/requirements.md#r1), [R4](../constraints/requirements.md#r4); not met: [P6](../constraints/production.md#p6) | Accepted | Partial. Retrieval evaluation and the SQL gold set. No live-client harness |

## Related documents

[TODO](../../TODO.md) tracks delivery and gaps. [ARCHITECTURE](../../ARCHITECTURE.md) describes the code as it runs. [GLOSSARY](../../GLOSSARY.md) defines the terms. The [system design](../../design/SYSTEM-DESIGN.md) holds proposals, not shipped features.

When a decision changes, add the next numbered record and mark the old one "superseded", with a link. Keep the reasons and the implementation status separate. Do not erase earlier trade-offs. An accepted future extension does not bring CAD into the MVP scope.
