# Read this first: an MVP, not a platform

This repository is a **minimum viable product built in about four to five hours**. Its goal is narrow: to show that one question can be answered under a given set of constraints.

> A selected engineering lead asks, in plain language, for a critical engineering parameter across 100+ project documents, and gets an answer in under 10 seconds, with the exact source, without opening a design file or a viewer, and without ever seeing information from a document they may not read.

The constraints come from [the brief](Starting_document.md) and from decisions made while the MVP was built. They are listed, one anchor each, in [constraints/](constraints/README.md). Every decision record in [adr/](adr/README.md) links to the constraints it serves. Both are generated from one SQLite database of design records ([design/records/](../design/records/README.md)), so the links cannot drift.

The reality is a far more complex system. Real repositories hold years of files in many formats and versions, with their own permissions, owners and approval workflows. Real users ask questions that no one wrote down in advance. And making a search service **highly available to a whole organisation**, so that any number of people get a trustworthy answer within 10 seconds, is its own engineering challenge, separate from proving that the answer can be found at all. The MVP does not attempt it. This page says what the MVP proves, what it does not, and what that challenge involves.

<a id="what-is-assumed-and-what-stands-in-for-it"></a>

## What is assumed, and what stands in for it

The brief says five things **already exist** ([C1–C5](constraints/environment.md)): an architecture direction, the repository, connectors and APIs that extract metadata, text and properties from supported files, structured and semantic stores, and a chat-agent shell. The MVP takes them as given and does not design or build them. To run end to end it needs something in each place, so it uses the simplest stand-in that proves the chain from question to cited answer ([ADR 0020](adr/0020-assume-the-environment-and-stand-in-for-it.md)):

| In the brief (exists) | Stand-in in the MVP | In a real deployment |
| --- | --- | --- |
| [C1](constraints/environment.md#c1) An architecture direction | One search service behind an HTTP API, a web page and an MCP server | The existing architecture calls the same service |
| [C2](constraints/environment.md#c2) An existing repository | A local folder of 148 test files; folder rules for permissions | The repository, its versions and its permissions, through its connector |
| [C3](constraints/environment.md#c3) Connectors extract metadata, text and properties | Readers for Markdown, PDF text layer, CSV and XLSX | The existing connectors, each plugged in behind the reader interface |
| [C4](constraints/environment.md#c4) Structured and semantic stores | SQLite: an FTS5 index, tables and typed facts | The company's stores |
| [C5](constraints/environment.md#c5) A chat-agent shell | Claude Code, Codex and Pi over a local MCP server | The company's shell, over remote MCP or its tool API |

So the PDF and Markdown extraction in this repository is a **placeholder**, not a proposal to build extraction. The work that is the MVP's own sits between these parts: knowing the questions, what to take from tables and how to type it, permissions before limits, binding an answer to its subject, citations, constrained SQL, the time budget, and the tests and evaluation.

## What the MVP proves

- A question in plain language can be answered from a mixed repository (Markdown, PDF with a text layer, CSV, XLSX) with the exact file, location and version of the source ([U1](constraints/use-case.md#u1), [U4](constraints/use-case.md#u4), [U5](constraints/use-case.md#u5), [U6](constraints/use-case.md#u6)).
- There are two ways in, chosen from the data: word search over passages for values in prose, and SQL written by the chat agent over typed facts from tables, constrained and scoped by the server ([C4](constraints/environment.md#c4), [C5](constraints/environment.md#c5), [S4](constraints/scope.md#s4)).
- Permissions are applied before any limit, ranking, count, join or aggregate, on both paths, and a test asks every evaluation question as every user ([R1](constraints/requirements.md#r1)).
- The service says when it does not know, and how well a value is bound to the question, rather than guessing ([U4](constraints/use-case.md#u4), [R2](constraints/requirements.md#r2)).
- The same service works from a web page and from three chat clients (Claude Code, Codex and Pi) over a local MCP server ([C1](constraints/environment.md#c1), [C5](constraints/environment.md#c5)).
- One user gets an answer in about 80 ms. Under load, every user gets an answer within 8 s or an immediate "busy, retry in n s" ([U3](constraints/use-case.md#u3)).

## What the MVP does not prove

- **That it works on real data.** The 148 test files are synthetic or public, written together with the questions ([S3](constraints/scope.md#s3)). The scores are optimistic until real, held-back questions exist ([P6](constraints/production.md#p6)).
- **That it is secure.** Sign-in on the web page is pretend; the MCP server trusts the user named on its command line ([P2](constraints/production.md#p2)). Permissions are folder rules in a Python file, not the repository's own ([P3](constraints/production.md#p3)). The permission tests prove the logic, not the deployment.
- **That it serves an organisation.** See the next section ([P1](constraints/production.md#p1)).
- **That the chat agent's SQL is right.** The server makes the SQL safe, not correct. A gold set checks the reference queries; the live evaluation of each client's model is designed, not built ([ADR 0019](adr/0019-evaluate-retrieval-and-nl-to-sql.md)).
- **Anything about extraction quality.** Reading files is the connectors' job ([C3](constraints/environment.md#c3)). The stand-in readers have no OCR, no tables from PDF files and no CAD ([S2](constraints/scope.md#s2)), and facts come only from table cells; what the real connectors return must be profiled on the real repository.

The full list of production requirements the MVP does not meet is in [constraints/production.md](constraints/production.md).

<a id="making-it-available-to-an-organisation"></a>

## Making it available to an organisation

**This is the largest area of future work.** The MVP answers one user quickly. It does not answer many users at once, and it has no redundancy. The requirement for a real service ([P1](constraints/production.md#p1)) is that an arbitrary number of people can ask at the same time and each gets an answer within 10 seconds, and that the service stays up when a process, a machine or a data centre fails.

### Where the MVP stands

Every search, read and SQL query goes through **one lock and one SQLite connection in one process on one machine**:

- `SearchService.lock` is held from the file match to the audit write, so requests run one at a time. On the test data that is about **10 requests a second**, whatever the hardware.
- The SQL path builds an in-memory copy of every fact the user may read, **for every request**, under that lock. That is about 3 s at a million facts, and the SQL step budget stops even the standard query at about 200,000 facts.
- The index, the audit log and the telemetry are SQLite files on the local disk. If the machine or the disk fails, the service and its audit history are gone.
- Writes (indexing) take the same index lock as reads.

Measured on a laptop (one process, 29 October 2026): with 100 requests at once, the slowest answer took 10.3 s; with 1,000, it took 102 s.

The MVP's answer is **admission control** ([ADR 0018](adr/0018-admission-control-and-the-time-budget.md)): predict each request's wait and refuse it at once, with a retry time, if it cannot finish within 8 s. Every answered request now finishes within 5.7 s and every refusal comes back within 0.25 s. This keeps the promise to the users it answers and is honest with the rest. **It adds no capacity.** With 1,000 people asking at once, about 950 are told to try again. That is acceptable for a demonstration and not for a service.

### What high availability needs

A shared service must remove every single point on the query path: one process, one lock, one connection, one file, one machine. The work below is in rough order of value. The technologies named are **candidates to evaluate, not decisions**; each choice needs its own ADR, measured on the real repository.

1. **Concurrent reads in one process.** One read connection per thread and one read transaction (a WAL snapshot) per request, with no global lock for searches. Writers keep the index lock. This is the cheapest step and lifts the ceiling from one request at a time to the number of cores, within the limits of Python's GIL.
2. **A stateless query tier that scales out.** Several worker processes on several machines behind a load balancer, with no session, upload queue or cache held in process memory. Add workers to add capacity; lose one and the others carry on.
3. **A resilient, replicated store.** Replace the local SQLite files with a search store and a database that replicate across machines and zones and fail over automatically: for example a managed PostgreSQL with full-text search and read replicas, or a search engine such as OpenSearch alongside a relational database for facts. The index must survive the loss of any one machine, and reads must keep working while it is rebuilt.
4. **Permissions enforced in the store, not by copying.** Row-level security or views over a permitted-file table, keyed to the user's verified identity ([P2](constraints/production.md#p2)) and the repository's own permissions ([P3](constraints/production.md#p3)), so the SQL path no longer copies data per request. Make `components` an indexed table, not a grouping view, and scale the step budget with the data. Keep the guarantee that forbidden data is absent, not filtered ([R1](constraints/requirements.md#r1)).
5. **Separate the indexing pipeline from the query path.** Indexing becomes a durable, queued, retryable pipeline that reads from the repository's connectors ([C3](constraints/environment.md#c3)), builds a new index version beside the live one, and switches over when it is complete (blue/green). Readers never wait for writers.
6. **Load shedding and fairness at the edge.** An API gateway with per-user and per-client quotas, so one script or one runaway agent cannot use the capacity of everyone else. Admission control stays as the last line, in each worker, and the "busy" message stays visible to users and agents.
7. **Remote MCP with verified identity.** A remote MCP server over HTTP with OAuth, behind the same gateway, so chat clients share the service rather than each running a local copy ([ADR 0012](adr/0012-mcp-server-for-the-chat-agent.md)).
8. **Durable audit and telemetry.** A managed, append-only audit store with retention, backups and tamper evidence ([P4](constraints/production.md#p4)); metrics, traces and logs in the company's monitoring.
9. **Service-level objectives and capacity planning.** Define the target (for example, 99% of questions answered within 10 s, measured end to end including the chat agent), alert on it, and size the tiers from measured cost per request on the real repository. A rough sizing at the test-data cost of 0.1 s a request: 1,000 users asking one question a minute is about 17 requests a second, or 3 to 4 workers at 60% load. Real documents and real SQL will cost more.
10. **Load tests in CI.** Run `scripts/load_test.py`, or its successor against a deployed environment, at the expected size and concurrency on every release, with the 10 s target as a gate.
11. **Backups, recovery and failure drills.** Tested restore of the index and the audit, documented recovery time and recovery point, and regular tests that kill a worker, a replica and a zone.

None of this changes what the MVP proved: the questions, the extraction, the two paths, the permission rule and the citations stay. It changes where they run and how many copies there are. [design/SCALING.md](../design/SCALING.md) and [ADR 0018](adr/0018-admission-control-and-the-time-budget.md) give the measurements and the first steps; [TODO.md](../TODO.md) tracks them as milestones.

## Map of this folder

| Document | What it is |
| --- | --- |
| [constraints/](constraints/README.md) | The background, constraints, use case, task and scope from the brief, the requirements added during the MVP, and the production requirements the MVP does not meet, one anchor each. Generated |
| [adr/](adr/README.md) | The architecture decision records, each linked to the constraints it serves. Generated |
| [design/records/](../design/records/README.md) | The SQLite database that holds the brief, the constraints and the decision records, and generates the two folders above. With a browser view and an MCP server for agents |
| [MCP.md](MCP.md) | How to connect a chat client to the MCP server, the tools, example SQL and what was verified |
| [METRICS.md](METRICS.md) | What is measured, how, and why the scores are optimistic |
| [Starting_document.md](Starting_document.md) | The original brief |
| [CODEX_ENGINEERING_SEARCH_HANDOFF.md](CODEX_ENGINEERING_SEARCH_HANDOFF.md), [engineering_knowledge_search_design_notes.html](engineering_knowledge_search_design_notes.html) | Dated design inputs (29 October 2026). Kept as received; decisions are recorded in the ADRs |

Outside this folder: [README.md](../README.md) (quick start), [ARCHITECTURE.md](../ARCHITECTURE.md) (the code as it runs), [TODO.md](../TODO.md) (milestones and gaps), [GLOSSARY.md](../GLOSSARY.md) (terms) and [design/](../design/SYSTEM-DESIGN.md) (proposals, not shipped features).
