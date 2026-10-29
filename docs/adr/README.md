# Decision records

Decisions that are hard to reverse, surprising without context, and the result of a real trade-off. Each cites the [brief items](../constraints/README.md) it serves (B, C, U, T, S), the clarifications (K) and the gaps (G) it leaves open, and the files that implement and test it.

**What the IDs mean.** Each ID is an item from [the brief, item by item](../constraints/README.md), and links to its definition:

| Prefix | Page | What the items are |
| --- | --- | --- |
| B | [Background](../constraints/background.md) | The problem as the brief states it |
| C | [Constraints](../constraints/constraints.md) | What already exists in the company; the MVP uses labelled stand-ins |
| U | [Use case](../constraints/use-case.md) | Who needs what, how fast, with what confidence |
| T | [Task](../constraints/task.md) | What the brief asks to be delivered |
| S | [Scope](../constraints/scope.md) | An MVP, not the platform |
| K | [Clarifications](../constraints/clarifications.md) | The product owner's answers where the brief is open |
| G, O | [Gaps and challenges](../constraints/gaps.md) | What the MVP leaves unsolved (G), and what is out of scope but recorded (O) |

The central decision is the first: the MVP builds sample stand-in readers so that it can prove the use case.

| ADR | Decision | Serves |
| --- | --- | --- |
| [0001](0001-prove-the-use-case-with-stand-in-readers.md) | Prove the use case with sample stand-in readers, not real connectors | [C3](../constraints/constraints.md#c3), [K7](../constraints/clarifications.md#k7), [U2](../constraints/use-case.md#u2), [U6](../constraints/use-case.md#u6) |
| [0002](0002-structured-tables-and-full-text-search.md) | Store structured tables and a lexical full-text index; leave semantic search out | [C4](../constraints/constraints.md#c4), [K8](../constraints/clarifications.md#k8) |
| [0003](0003-quote-the-source-and-refuse-rather-than-guess.md) | Answer with a sentence copied from the source, and refuse rather than guess | [U5](../constraints/use-case.md#u5), [U6](../constraints/use-case.md#u6), [K3](../constraints/clarifications.md#k3), [K4](../constraints/clarifications.md#k4) |
| [0004](0004-permissions-before-ranking-limits-and-counts.md) | Apply permissions before ranking, limits and counts; folder rules stand in for the repository's controls | [U1](../constraints/use-case.md#u1), [K5](../constraints/clarifications.md#k5), [K13](../constraints/clarifications.md#k13) |
| [0005](0005-one-search-service-behind-tools.md) | One search service behind MCP tools and HTTP; the chat shell owns the conversation | [C5](../constraints/constraints.md#c5), [C1](../constraints/constraints.md#c1) |
| [0006](0006-the-user-never-writes-sql.md) | The user never writes SQL; the chat agent may write constrained SQL | [B4](../constraints/background.md#b4), [K9](../constraints/clarifications.md#k9) |
| [0007](0007-the-source-is-the-file-on-disc.md) | The source is the file on disc; a content fingerprint detects change | [C2](../constraints/constraints.md#c2), [U5](../constraints/use-case.md#u5), [K3](../constraints/clarifications.md#k3) |
| [0008](0008-a-time-budget-and-admission-control.md) | Hold 10 seconds end to end with a time budget and admission control | [U4](../constraints/use-case.md#u4), [K6](../constraints/clarifications.md#k6) |
| [0009](0009-acceptance-tests-and-evaluation-sets.md) | Enforce the use case with acceptance tests and evaluation sets | [T5](../constraints/task.md#t5), [U2](../constraints/use-case.md#u2)–[U6](../constraints/use-case.md#u6) |
| [0010](0010-a-local-single-process.md) | A local single process that reads the repository in place | [S1](../constraints/scope.md#s1), [S2](../constraints/scope.md#s2), [C2](../constraints/constraints.md#c2) |
| [0011](0011-tables-land-in-one-fixed-schema.md) | Tables land in one fixed schema; the questions, not the files, shape the model | [C3](../constraints/constraints.md#c3), [C4](../constraints/constraints.md#c4), [G6](../constraints/gaps.md#g6) |

**Format:** a short title, one to three sentences, then status, what it serves, the options considered, the consequences, and the files. A new decision gets the next number; a decision that replaces one says so, and the old one is marked superseded, not deleted.
