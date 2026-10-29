# Production requirements (P)

What a service for a whole organisation needs and **the MVP does not meet**. They are out of scope by [S1](scope.md#s1), and recorded so that no one mistakes the MVP for a platform. [docs/README.md](../README.md#making-it-available-to-an-organisation) explains why each is its own engineering work.

| ID | Constraint |
| --- | --- |
| [P1](#p1) | Any number of users, each answered within 10 seconds |
| [P2](#p2) | Verified identity |
| [P3](#p3) | Permissions from the repository |
| [P4](#p4) | Durable, protected audit |
| [P5](#p5) | Approved use of language models |
| [P6](#p6) | Quality measured on real questions |

<a id="p1"></a>

## P1. Any number of users, each answered within 10 seconds

> An arbitrary number of people can ask at the same time, and each gets an answer within 10 seconds. The service stays available when a process, a machine or a zone fails.

**Source:** Follows from U3 at organisational scale.

**What it means for the design:** No single process, lock, connection or machine on the query path. Reads scale out; writes do not block reads; the store is replicated and fails over; capacity is planned and load-tested.

**Where the MVP stands:** **Not met.** One process, one lock, one SQLite connection, about 10 requests a second, on one machine. Admission control refuses the excess at once rather than answering late. See [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md).

**Decisions:**

- [ADR 0002](../adr/0002-independent-local-instances.md): Run independent instances with local data (not met)
- [ADR 0018](../adr/0018-admission-control-and-the-time-budget.md): Answer within the time budget or refuse at once, and record what does not scale (not met)

<a id="p2"></a>

## P2. Verified identity

> The service knows who is asking from the company identity provider. It never takes the user from a flag, a setting or a tool argument.

**Source:** Follows from R1.

**What it means for the design:** Company sign-in for the web app; a remote MCP server with OAuth, taking the user from the verified token.

**Where the MVP stands:** **Not met.** Pretend sign-in on the web; the MCP server trusts `--user`. This is a known security hole ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).

**Decisions:**

- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (not met)

<a id="p3"></a>

## P3. Permissions from the repository

> Each user's file permissions come from the repository itself, current at query time.

**Source:** Follows from R1 and C2.

**What it means for the design:** Effective permissions (including inheritance and deny entries) synced or queried through the connector.

**Where the MVP stands:** **Not met.** Path rules in `access.py` ([ADR 0010](../adr/0010-path-based-access-rules.md)).

**Decisions:**

- [ADR 0010](../adr/0010-path-based-access-rules.md): Index the whole repository, and control access with folder and file rules (not met)

<a id="p4"></a>

## P4. Durable, protected audit

> The audit log survives the loss of a machine, is protected against change, and has retention and backup rules.

**Source:** Follows from U4 and R1.

**What it means for the design:** A managed audit store with retention, tamper evidence and access control.

**Where the MVP stands:** **Not met.** A local SQLite file ([ADR 0007](../adr/0007-telemetry-and-audit.md)).

**Decisions:**

- [ADR 0007](../adr/0007-telemetry-and-audit.md): Measure from the start, and audit before evidence is released (not met)

<a id="p5"></a>

## P5. Approved use of language models

> The company approves which document text may be sent to which language model provider.

**Source:** Follows from C5.

**What it means for the design:** A data-governance decision per repository or classification, enforced by the service.

**Where the MVP stands:** **Not met.** The chat client sends permitted tool results to its provider ([ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md)).

**Decisions:**

- [ADR 0012](../adr/0012-mcp-server-for-the-chat-agent.md): Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only (not met)

<a id="p6"></a>

## P6. Quality measured on real questions

> Answer quality is measured on real questions from engineering leads, with a held-back set, and releases are gated on it.

**Source:** Follows from U4 and R4.

**What it means for the design:** Profile the real repository; collect real questions with expected answers and sources; score retrieval, SQL and replies.

**Where the MVP stands:** **Not met.** Scores come from synthetic data written with the questions ([ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md)).

**Decisions:**

- [ADR 0019](../adr/0019-evaluate-retrieval-and-nl-to-sql.md): Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results (not met)
