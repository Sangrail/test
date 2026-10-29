# Architecture decision records

These records explain the decisions of the MVP, and why each one serves the use case. **Accepted** means that the direction is agreed. It does not mean that every part is implemented: each record has an "Implementation" section that says what the code does now.

## The use case and the constraints

Each record cites the parts of the brief that it serves, with these IDs.

**The problem.** The company has years of engineering and infrastructure design information in design files and project documents. Users often do not know which files hold the information that they need.

**Use case**

| ID | Requirement from the brief |
| --- | --- |
| **U1** | A selected engineering manager or lead finds a critical engineering parameter: a load limit, a material specification or a compliance approval status |
| **U2** | Across 100+ project documents |
| **U3** | In under 10 seconds |
| **U4** | With 100% confidence in the source |
| **U5** | Without opening a single design file (CAD) or tool (PDF viewer) |
| **U6** | Users do not want to learn file formats, schema details, query languages or system-specific jargon |

**Constraints**

| ID | Constraint from the brief |
| --- | --- |
| **C1** | A broader architecture direction already exists |
| **C2** | The files live in an existing repository |
| **C3** | Connectors and APIs can extract metadata, text and properties from supported files |
| **C4** | Extracted information can be stored in structured and/or semantic stores |
| **C5** | A chat-agent shell can call backend APIs or tools to expose a conversational plane for users |

**Scope**

| ID | Scope decision |
| --- | --- |
| **S1** | The first scope is an MVP, not the final platform or solution |
| **S2** | Markdown and simple PDF only. No OCR. No DXF, DWG, JT or CATIA |
| **S3** | The repository will be published, so the test documents must be synthetic or publicly shareable |
| **S4** | The 29 October design inputs ([handoff](../CODEX_ENGINEERING_SEARCH_HANDOFF.md), [design notes](../engineering_knowledge_search_design_notes.html)) add CSV and XLSX, detection from content, a coverage report, and SQL written by the MCP client over tables. CAD content stays out of scope |

**Requirements added during the MVP**

| ID | Requirement |
| --- | --- |
| **R1** | A user must never get information from a document that the user is not authorised to read. This is an absolute requirement |
| **R2** | The service must answer the question. A list of passages is not an answer |
| **R3** | Users can ask for lists of documents: by project, by topic, by material, by approval status, or by a value such as a load above 5 kN/m², with follow-up questions about a previous list |
| **R4** | The tests must enforce the use case |

## Records

**Status** is the state of the decision: *accepted*, *amended* (still in force, with changes recorded in a later record) or *superseded in part* (the named part is replaced by a later record; the rest stands). No record is fully superseded.

| Record | Decision | Serves | Status | Implementation |
| --- | --- | --- | --- | --- |
| [0001](0001-mvp-format-scope.md) | Markdown and text-layer PDF are the MVP formats | S1, S2, U5 | Superseded in part by 0016 | Done. CSV and XLSX added by 0016 |
| [0002](0002-independent-local-instances.md) | Each tester runs an independent local instance | S1, S3, C2 | Accepted (MVP; a shared service needs 0018's scaling work) | Done |
| [0003](0003-versioned-reader-selection.md) | Select and record a tested reader for each format and version | C2, C3, U4 | Accepted | Mostly done. Content detection, reader registry, reader version stored. No CAD reader |
| [0004](0004-persistent-evidence.md) | Store extracted passages with their source version | U3, U4, U5 | Accepted | Done |
| [0005](0005-coverage-and-reader-gaps.md) | Report files that cannot be read | C2, C3, U4 | Accepted | Done. Stored statuses and a coverage report for the index team |
| [0006](0006-permissions-before-results.md) | Check permissions before answers, counts and pages | R1, U1 | Superseded in part by 0017 | Done |
| [0007](0007-telemetry-and-audit.md) | Telemetry and an audit record before evidence is released | U3, U4, R1 | Accepted | Done |
| [0008](0008-index-team-and-audit-viewer.md) | Search users and the index team are separate roles | R1, U1 | Accepted | Done |
| [0009](0009-sqlite-fts5-index-and-answers.md) | SQLite FTS5 inverted index. Answers are exact text | U2, U3, U4, U6, R2, R3 | Amended by 0017 | Done |
| [0010](0010-path-based-access-rules.md) | Index the whole repository. Folder and file access rules | R1, C2, U2 | Accepted | Done |
| [0011](0011-one-search-service.md) | One search service for the web page, the API and the MCP server | C1, C5, R1, U4 | Accepted | Done |
| [0012](0012-mcp-server-for-the-chat-agent.md) | A stdio MCP server is the chat-agent interface | C5, U6, S1, R1 | Superseded in part by 0016 and 0018 | Done. Verified with Claude Code, Codex and Pi. Identity is a known security hole |
| [0013](0013-no-answer-before-a-wrong-answer.md) | Give no answer before a wrong answer | U4, R2, R1 | Superseded in part by 0017 | Done |
| [0014](0014-defer-facts-store-and-embeddings.md) | Defer the facts store and embeddings | C3, C4, S1, U1 | Superseded in part by 0016 | Embeddings and facts from prose still deferred |
| [0015](0015-acceptance-tests-enforce-the-use-case.md) | Acceptance tests enforce the use case on a public test repository | R4, U1 to U5, R1, S3 | Superseded in part by 0019 | Done |
| [0016](0016-structured-facts-and-client-written-sql.md) | Read tables into typed facts at index time. The MCP client writes constrained SQL | U1, U2, U4, U6, R1, R3, C3, C4, C5 | Accepted | Done for CSV, XLSX and Markdown tables |
| [0017](0017-bind-answers-and-permit-before-the-limit.md) | Bind each answer to its subject. Apply permissions before the retrieval limit | U4, R1, R2, R3 | Accepted | Done |
| [0018](0018-admission-control-and-the-time-budget.md) | Answer within the time budget or refuse at once. Record what does not scale | U3, U4, R1, C5 | Accepted | Admission control done. Scaling work not started |
| [0019](0019-evaluate-retrieval-and-nl-to-sql.md) | Evaluate retrieval, natural language to SQL and the agent's reply. Gate releases on them | U1, U4, U6, R1, R4 | Accepted | Partial. Retrieval evaluation and the SQL gold set. No live-client harness |

## Related documents

[TODO](../../TODO.md) tracks delivery and gaps. [ARCHITECTURE](../../ARCHITECTURE.md) describes the code as it runs. [GLOSSARY](../../GLOSSARY.md) defines the terms. The [system design](../../design/SYSTEM-DESIGN.md) holds proposals, not shipped features.

When a decision changes, add the next numbered record and mark the old one "superseded", with a link. Keep the reasons and the implementation status separate. Do not erase earlier trade-offs. An accepted future extension does not bring CAD into the MVP scope.
