# Gaps and challenges (G)

What the MVP leaves unsolved ([T2](task.md#t2)), and what is out of scope but recorded. A gap is not a defect of the MVP: it is what a service for the whole organisation needs beyond it ([S2](scope.md#s2)).

The hardest of these is [G4](#g4): a retrieval system is only as good as its accuracy on real questions, and accuracy needs metrics that the organisation agrees on.

| ID | Gap or challenge | Affects |
| --- | --- | --- |
| [G1](#g1) | Identity management, and permissions wired correctly | [U1](use-case.md#u1), [K13](clarifications.md#k13) |
| [G2](#g2) | Durable audits | [U5](use-case.md#u5) |
| [G3](#g3) | Approved language-model use | [C5](constraints.md#c5) |
| [G4](#g4) | Quality on real questions: retrieval accuracy and its metrics | [U2](use-case.md#u2), [U5](use-case.md#u5) |
| [G5](#g5) | Any number of users, within 10 seconds | [U1](use-case.md#u1), [U4](use-case.md#u4) |
| [G6](#g6) | Consistent status values across sources: an ontology | [U2](use-case.md#u2) |
| [G7](#g7) | The service cannot tell who wrote a SQL statement | [B4](background.md#b4), [K9](clarifications.md#k9) |
| [G8](#g8) | What the stand-in readers cannot read | [C3](constraints.md#c3), [U6](use-case.md#u6) |

**Out of scope, recorded:**

| ID | Item | Why recorded |
| --- | --- | --- |
| [O1](#o1) | Semantic search (embeddings) | [C4](constraints.md#c4) allows a semantic store |
| [O2](#o2) | Analysis of slow queries | [K6](clarifications.md#k6) asks for instrumentation |

<a id="g1"></a>

## G1. Identity management, and permissions wired correctly

**The challenge:** knowing who is asking, and applying the repository's own access controls to every answer.

**In the MVP:** users choose a demo name to sign in (no password); the MCP server takes the user from its `--user` flag, unverified. Folder and file rules in [`access.py`](../../engineering_search/access.py) stand in for the repository's access controls. Permissions apply before ranking, limits and counts ([ADR 0004](../adr/0004-permissions-before-ranking-limits-and-counts.md)), and the leak tests attack that from many sides; they do not prove the rules match the real repository.

**Needed:** sign-in through the company's identity provider, a verified user on the MCP path, and permissions read from the repository (or its connector), with a test that they are wired correctly.

<a id="g2"></a>

## G2. Durable audits

**The challenge:** a record of who asked what and which evidence was released, that survives and cannot be altered.

**In the MVP:** every search, read and SQL query writes an audit event to a local SQLite file before evidence is released; no audit, no evidence. Requests refused before they reach the evidence (a question that is SQL, a busy service, a read the user may not make) are not audited. The file is not tamper-evident, not replicated and has no retention policy.

**Needed:** an append-only, central, retained audit store.

<a id="g3"></a>

## G3. Approved language-model use

**The challenge:** the chat shell sends questions and quoted evidence to a language model. Which models may see engineering documents is the company's decision.

**In the MVP:** the service itself uses no language model: answers are copied from the documents. The chat shell (Claude Code, Codex, Pi) is the user's choice, and nothing checks that its model is approved.

**Needed:** a list of approved models and deployments, and a shell that is held to it.

<a id="g4"></a>

## G4. Quality on real questions: retrieval accuracy and its metrics

**The challenge:** "100% confidence in the source" means every quoted value is right and comes from the right file. That can only be measured on real questions over real documents, with agreed metrics: whether the correct answer is given, whether the system refuses when it should, success@k, recall@k, MRR, and the accuracy of agent-written SQL.

**In the MVP:** the evaluation sets ([`evaluation/`](../../evaluation/README.md): 17 retrieval questions, 13 natural-language-to-SQL questions) score well, but the same team wrote the documents, the questions and the code, and the documents are clean and small. [docs/METRICS.md](../METRICS.md) explains why the scores do not predict real performance.

**Needed:** a set of real questions from the pilot group, with answers checked by engineers, scored on every release ([ADR 0009](../adr/0009-acceptance-tests-and-evaluation-sets.md)).

<a id="g5"></a>

## G5. Any number of users, within 10 seconds

**The challenge:** holding the 10-second target ([U4](use-case.md#u4)) for many users at once, over a repository far larger than the test set, with the index kept up to date.

**In the MVP:** one local process. Admission control refuses at once a request that cannot be answered within the 8-second budget, rather than letting it run late ([ADR 0008](../adr/0008-a-time-budget-and-admission-control.md)). The index is refreshed on start and on request ([K16](clarifications.md#k16)); nothing watches the repository. Admission does not know about a refresh: a request admitted while a refresh holds the index waits for it, and that wait is not in the estimate. [design/SCALING.md](../../design/SCALING.md) has the capacity experiment and what multiple machines would need.

**Needed:** horizontal scale for the query path, a shared index service, and automatic refresh as files change.

<a id="g6"></a>

## G6. Consistent status values across sources: an ontology

**The challenge:** the same idea is written differently in different documents: "Approved", "APPROVED FOR CONSTRUCTION", "Accepted"; "SWL", "safe working load", "load capacity". Comparing or counting across sources needs one vocabulary for them: an ontology of the documents. Building one over years (or terabytes) of existing documents is hard, and is not the MVP's job.

**In the MVP:** the fact rules map a few column names to parameters (load capacity, material grade, compliance status) and normalise units, not words. A status is compared as written, so `compliance_status <> 'Approved'` counts "APPROVED FOR CONSTRUCTION" as not approved.

**Needed:** an agreed ontology of parameters and status values, applied by the connectors. The way to it: profile the data, have subject matter experts write the quantitative and qualitative questions they need answered, and derive the model (the vocabulary, and a schema that suits those questions) from enough of them ([ADR 0011](../adr/0011-tables-land-in-one-fixed-schema.md)). Those questions are also the real-question set that [G4](#g4) needs.

<a id="g7"></a>

## G7. The service cannot tell who wrote a SQL statement

**The challenge:** the user never writes SQL ([K9](clarifications.md#k9)), but the chat agent may. A statement reaches `query_sql` from the agent either way.

**In the MVP:** a question that is a SQL statement is refused by `search_evidence` and `POST /search`, and the MCP instructions tell the agent not to pass the user's SQL on. The service cannot check that it obeys. The refusal recognises SQL by compiling it against the projection's tables ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)), so a SELECT over a table the projection does not have is searched as words rather than refused.

**Needed:** a shell that keeps the user's text and the agent's tool calls apart, or a policy layer in the shell.

<a id="g8"></a>

## G8. What the stand-in readers cannot read

**The challenge:** the brief assumes connectors for the supported files ([C3](constraints.md#c3)). The MVP's sample readers cover only enough formats to prove the flow.

**In the MVP:** scanned PDFs (no OCR), CAD geometry, binary DXF, DWG, JT and CATIA are not read. Each such file is listed in the coverage report with its reason, so a missing answer is never silent. The CSV reader cites one line per row, so a quoted cell that spans several lines is cited at the wrong lines.

**Needed:** the real connectors, behind the same reader interface.

<a id="o1"></a>

## O1. Semantic search (embeddings) — out of scope

Recorded because the brief allows a semantic store ([C4](constraints.md#c4)). The MVP chose lexical full-text search, which can show exactly why a passage matched ([ADR 0002](../adr/0002-structured-tables-and-full-text-search.md)). Semantic search may help with synonyms and paraphrase on real questions ([G4](#g4)).

<a id="o2"></a>

## O2. Analysis of slow queries — out of scope

Recorded because the 10-second target is measured ([K6](clarifications.md#k6)). The telemetry keeps timing distributions in memory; it does not keep the slow queries themselves for later analysis.
