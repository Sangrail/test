# Intent, constraints and scope

<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

The background, constraints, use case, task and scope from [the brief](../Starting_document.md), what the product owner added while the MVP was built, and the production requirements that it does not meet. They are kept, with every earlier version, in the design records database ([docs/records](../records/README.md)), with the [decision records](../adr/README.md), the fourth pillar.

| Pillar | What it is | Items |
| --- | --- | --- |
| **Intent** | What the system is for: the direction that every decision flows from. | B1, B2, R2, R3, U1, U2, U3, U4, U5, U6 |
| **Constraint** | What the system must work within: the environment, the data, the rules it must keep. | C1, C2, C3, C4, C5, P1, P2, P3, P4, P5, P6, R1, R4, R5, R6, R7, R8 |
| **Scope** | How far this work goes down the road. The arbiter. | S1, S2, S3, S4, S5, S6, T1, T2, T3 |

Decisions flow from the intent and the constraints. Scope is the arbiter of how far this work goes: going beyond a scope item is acceptable, and is recorded with an *exceeds* link; falling short of one is the failure to flag. The group in an ID (B, C, U, …) says where the item came from; the pillar says what kind of item it is.

| Group | IDs | What it holds |
| --- | --- | --- |
| [Background](background.md) | B1–B2 | The problem as the brief states it |
| [Constraints from the brief](environment.md) | C1–C5 | The environment that already exists: the architecture direction, the repository, connectors, stores and the chat-agent shell. The MVP assumes them and uses stand-ins |
| [Use case](use-case.md) | U1–U6 | Who needs what, how fast and with what confidence. From the brief |
| [Task](task.md) | T1–T3 | What the brief asks to be delivered |
| [Scope](scope.md) | S1–S6 | How far down the road the MVP goes. The arbiter: exceeding scope is acceptable and recorded; falling short of it is a failure |
| [Requirements and constraints added during the MVP](requirements.md) | R1–R8 | Permissions, answers, lists, tests, response time, several users, project folders and folder authorisation |
| [Production requirements](production.md) | P1–P6 | What a service for the whole organisation needs and **the MVP does not meet** |

## Each entry gives

- the statement, its pillar and its source;
- its standing, what it means for the design, and where the MVP stands;
- the files that stand in for it, enforce it, measure it or deliver it;
- the decision records that serve it, leave it unmet, go beyond it, or cite it;
- its history: each version, when it was active, and why it changed.

**Standing:**

- *context*: A fact about the problem, not a requirement to meet.
- *assumed*: The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.
- *met*: Met by the MVP, on the test data. For a scope item: the MVP goes this far.
- *partly met*: Met in part. Where the MVP stands says what is missing.
- *not met*: Not met by the MVP. For a scope item, this is the failure to flag.
- *exceeded*: The MVP goes beyond this scope item, knowingly. Acceptable, and recorded.

## Changing an item

Change the database, never these pages: [docs/records/README.md](../records/README.md) shows how, with plain SQL in the `sqlite3` shell. IDs are never renumbered or reused; a withdrawn item keeps its anchor and its history.
