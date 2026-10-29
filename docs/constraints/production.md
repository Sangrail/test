# Production requirements (P)


What a service for a whole organisation needs and **the MVP does not meet**. They are out of scope by [S1](scope.md#s1), and recorded so that no one mistakes the MVP for a platform. [docs/README.md](../README.md#making-it-available-to-an-organisation) explains why each is its own engineering work.

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [P1](#p1) | Any number of users, each answered within 10 seconds | constraint | not met | 1 |
| [P2](#p2) | Verified identity | constraint | not met | 1 |
| [P3](#p3) | Permissions from the repository | constraint | not met | 1 |
| [P4](#p4) | Durable, protected audit | constraint | not met | 1 |
| [P5](#p5) | Approved use of language models | constraint | not met | 1 |
| [P6](#p6) | Quality measured on real questions | constraint | not met | 1 |

<a id="p1"></a>

## P1. Any number of users, each answered within 10 seconds

> An arbitrary number of people can ask at the same time, and each gets an answer within 10 seconds. The service stays available when a process, a machine or a zone fails.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [U3](use-case.md#u3) at organisational scale.

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** No single process, lock, connection or machine on the query path. Reads scale out; writes do not block reads; the store is replicated and fails over; capacity is planned and load-tested.

**Where the MVP stands:** **Not met.** One process, one lock, one SQLite connection, about 10 requests a second, on one machine. Admission control refuses the excess at once rather than answering late. See [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md).

**Measured by:** [`scripts/load_test.py`](../../scripts/load_test.py).

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data (not met)
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.

<a id="p2"></a>

## P2. Verified identity

> The service knows who is asking from the company identity provider. It never takes the user from a flag, a setting or a tool argument.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [R1](requirements.md#r1).

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** Company sign-in for the web app; a remote MCP server with OAuth, taking the user from the verified token.

**Where the MVP stands:** **Not met.** Pretend sign-in on the web; the MCP server trusts `--user`. This is a known security hole ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).

**Decisions:**

- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.

<a id="p3"></a>

## P3. Permissions from the repository

> Each user's file permissions come from the repository itself, current at query time.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [R1](requirements.md#r1) and [C2](environment.md#c2).

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** Effective permissions (including inheritance and deny entries) synced or queried through the connector.

**Where the MVP stands:** **Not met.** Path rules in `access.py` ([ADR 0010](../adr/0010-path-based-access-rules.md)).

**Decisions:**

- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.

<a id="p4"></a>

## P4. Durable, protected audit

> The audit log survives the loss of a machine, is protected against change, and has retention and backup rules.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [U4](use-case.md#u4) and [R1](requirements.md#r1).

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** A managed audit store with retention, tamper evidence and access control.

**Where the MVP stands:** **Not met.** A local SQLite file ([ADR 0007](../adr/0007-telemetry-and-audit.md)).

**Decisions:**

- [ADR 0007](../adr/0007-telemetry-and-audit.md): Measure from the start, and audit before evidence is released (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.

<a id="p5"></a>

## P5. Approved use of language models

> The company approves which document text may be sent to which language model provider.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [C5](environment.md#c5).

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** A data-governance decision per repository or classification, enforced by the service.

**Where the MVP stands:** **Not met.** The chat client sends permitted tool results to its provider ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).

**Decisions:**

- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.

<a id="p6"></a>

## P6. Quality measured on real questions

> Answer quality is measured on real questions from engineering leads, with a held-back set, and releases are gated on it.

**Pillar:** constraint. **Source:** Required of a service for the whole organisation. Follows from [U4](use-case.md#u4) and [R4](requirements.md#r4).

**Standing:** *not met*. Not met by the MVP. For a scope item, this is the failure to flag.

**What it means for the design:** Profile the real repository; collect real questions with expected answers and sources; score retrieval, SQL and replies.

**Where the MVP stands:** **Not met.** Scores come from synthetic data written with the questions ([ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md)).

**Decisions:**

- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results (not met)

**History:**

- Version 1, from 2026-10-29, active. Recorded as a production requirement that the MVP does not meet.
