# Constraints

<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

The background, constraints, use case, task and scope from [the brief](../Starting_document.md), the requirements added while the MVP was built, and the production requirements it does not meet. Each has a stable ID and anchor, so a decision record can link to it, and each page lists the decision records and the files linked to it. They are kept in the [design records database](../../design/records/README.md) with the decision records.

| Group | IDs | What it holds |
| --- | --- | --- |
| [Background](background.md) | B1–B2 | The problem as the brief states it |
| [Constraints from the brief](environment.md) | C1–C5 | The environment that already exists: the architecture direction, the repository, connectors, stores and the chat-agent shell. The MVP assumes them and uses stand-ins |
| [Use case](use-case.md) | U1–U6 | Who needs what, how fast and with what confidence. From the brief |
| [Task](task.md) | T1–T3 | What the brief asks to be delivered |
| [Scope](scope.md) | S1–S4 | What the MVP includes and excludes |
| [Requirements added during the MVP](requirements.md) | R1–R4 | Permissions, answers, lists and tests |
| [Production requirements](production.md) | P1–P6 | What a service for the whole organisation needs and **the MVP does not meet** |

## Each entry gives

- the statement, quoted or closely paraphrased from its source;
- its source and its standing;
- what it means for the design, and where the MVP stands;
- the files that stand in for it, enforce it or measure it;
- the decision records that serve it, leave it unmet, or cite it.

**Standing:**

- *context*: A fact about the problem, not a requirement to meet.
- *assumed*: The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.
- *met*: Met by the MVP, on the test data.
- *partly met*: Met in part. Where the MVP stands says what is missing.
- *not met*: Not met by the MVP.

## How to cite a constraint

Add a row to `decision_constraints` in the database (`serves`, `not met` or `cites`) and name the ID in the record's text. The generated pages link every ID to its anchor: the ID in lower case. Do not renumber an ID. If a constraint changes, edit its row and say what changed; if it no longer applies, keep the row and say so.
