# Scope (S)

> Initial scope is just an MVP and NOT the final platform or solution.

| ID | Item | Standing |
| --- | --- | --- |
| [S1](#s1) | An MVP | met |
| [S2](#s2) | Not the final platform or solution | met |

<a id="s1"></a>

## S1. An MVP

> "Initial scope is just an MVP"

**For the design:** prove the use case end to end ([T5](task.md#t5)) with the least that shows the flow: stand-ins for what already exists ([constraints](constraints.md)), and shortcuts written down where they hide a risk.

**In the MVP:** one local process ([ADR 0010](../adr/0010-a-local-single-process.md)), sample readers ([ADR 0001](../adr/0001-prove-the-use-case-with-stand-in-readers.md)), a synthetic and public test repository, and the shortcuts listed in [ARCHITECTURE.md](../../ARCHITECTURE.md).

<a id="s2"></a>

## S2. Not the final platform or solution

> "NOT the final platform or solution"

**For the design:** what a platform needs (identity, durable audit, scale, model governance, an ontology) is named on the [gaps page](gaps.md), not built.

**In the MVP:** the gaps [G1](gaps.md#g1)–[G8](gaps.md#g8) are recorded; semantic search and slow-query analysis are out of scope and recorded ([O1](gaps.md#o1), [O2](gaps.md#o2)).

## Features beyond the brief

The MVP has features that the brief does not ask for by name. Each is labelled with the item it serves or as *beyond the brief*. None has its own decision record.

| Feature | Where | Serves |
| --- | --- | --- |
| Answer status: found, unverified, partial, not found | [`answer.py`](../../engineering_search/answer.py) | [U5](use-case.md#u5): refuse rather than guess |
| Lists of documents, with number comparisons and "of those, which" follow-ups | [`answer.py`](../../engineering_search/answer.py) | [U2](use-case.md#u2), [U3](use-case.md#u3) ([K14](clarifications.md#k14)) |
| Paging of evidence and lists | [`service.py`](../../engineering_search/service.py) | [U3](use-case.md#u3) |
| Refusing a quote from a file changed since indexing | [`service.py`](../../engineering_search/service.py) | [U5](use-case.md#u5) ([K3](clarifications.md#k3)) |
| Constrained SQL written by the chat agent | [`sql.py`](../../engineering_search/sql.py) | [C4](constraints.md#c4), [C5](constraints.md#c5) ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)) |
| Content detection (a file whose content does not match its extension) | [`detect.py`](../../engineering_search/indexing/detect.py) | [C3](constraints.md#c3) stand-in; *beyond the brief* in depth |
| Coverage report: what was read, how fully, and why not | [`coverage.py`](../../engineering_search/indexing/coverage.py) | [T2](task.md#t2) |
| Admission control and timing telemetry (every search, SQL query and evidence read, over HTTP and MCP) | [`adapters.py`](../../engineering_search/adapters.py) | [U4](use-case.md#u4) ([ADR 0008](../adr/0008-a-time-budget-and-admission-control.md)) |
| Pretend sign-in with demo users, labelled on every page as an MVP, not production security | [`access.py`](../../engineering_search/access.py), [`static/`](../../engineering_search/static/) | [U1](use-case.md#u1) stand-in ([G1](gaps.md#g1)) |
| Sign-in cards showing the folders each demo user may read, with readable counts (`/auth/users`) | [`app.py`](../../engineering_search/app.py) | *beyond the brief*; a demo aid. A card never names a folder its user cannot read, or says how many files they cannot read ([K13](clarifications.md#k13)). A real deployment has no user picker ([G1](gaps.md#g1)) |
| The signed-in user's readable documents and counts (`/demo/documents`) | [`app.py`](../../engineering_search/app.py) | *beyond the brief*; a demo aid. Readable counts only ([K13](clarifications.md#k13)) |
| Access rules page for the index team (`/admin/access`) | [`app.py`](../../engineering_search/app.py) | *beyond the brief*; shows the [U1](use-case.md#u1) stand-in's rules |
| Refusing a question that is a SQL statement | [`sql.py`](../../engineering_search/sql.py) | [B4](background.md#b4) ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)) |
| Audit log and the audit page | [`adapters.py`](../../engineering_search/adapters.py), `/audit` | *beyond the brief*; a stand-in for [G2](gaps.md#g2) |
| Index operations page (scan, refresh, coverage, telemetry) | `/admin` | *beyond the brief*; operates the stand-ins |
| Web search page | `/search` | [C5](constraints.md#c5) test harness; not a chat shell |
| Lock for several processes sharing one index | [`adapters.py`](../../engineering_search/adapters.py) | *beyond the brief*; the MCP server and the web app share one index |
| Evaluation sets for retrieval and agent-written SQL | [`evaluation/`](../../evaluation/README.md) | [G4](gaps.md#g4) ([ADR 0009](../adr/0009-acceptance-tests-and-evaluation-sets.md)) |

## Inputs that are not requirements

[`docs/engineering_knowledge_search_design_notes.html`](../engineering_knowledge_search_design_notes.html) is a dated design input (29 October 2026). It informed the work; it does not add to the brief, and it is not edited. A dated Codex handoff was also an input; it was removed from the repository on 29 October 2026.
