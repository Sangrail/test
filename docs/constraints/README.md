# Constraints

The use case, constraints, scope and requirements that the MVP's decisions answer to. Each has a stable ID and anchor, so a decision record can link to it, and each page lists the decision records that cite it.

| Group | IDs | What it holds |
| --- | --- | --- |
| [Use case](use-case.md) | U1–U6 | Who needs what, how fast and with what confidence. From the brief |
| [Constraints from the brief](environment.md) | C1–C5 | The environment that already exists: the architecture direction, the repository, connectors, stores and the chat-agent shell |
| [Scope](scope.md) | S1–S4 | What the MVP includes and excludes |
| [Requirements added during the MVP](requirements.md) | R1–R4 | Permissions, answers, lists and tests |
| [Production requirements](production.md) | P1–P6 | What a service for the whole organisation needs and **the MVP does not meet** |

## Each entry gives

- the statement, quoted or closely paraphrased from its source;
- the source: [the brief](../Starting_document.md), a decision during the MVP, or the dated design inputs;
- what it means for the design;
- where the MVP stands;
- the decision records that cite it.

## How to cite a constraint

In a decision record, link the ID to its anchor: `[U3](../constraints/use-case.md#u3)`. The anchor is the ID in lower case. Give a short reason in brackets after it, as the records do in their **Serves** line. Use **Not met:** for a production requirement that a decision knowingly leaves open.

Do not renumber an ID. If a constraint changes, edit its entry and say what changed; if it no longer applies, mark it withdrawn and keep the anchor.
