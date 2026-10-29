# Task (T)

<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

What [the brief](../Starting_document.md) asks to be delivered, with its time boxes.

| ID | Item | Pillar | Standing | Version |
| --- | --- | --- | --- | --- |
| [T1](#t1) | Identify and clarify the requirements, gaps and challenges | scope | met | 1 |
| [T2](#t2) | Define the initial phase and a system design diagram | scope | met | 1 |
| [T3](#t3) | A working prototype of an MVP | scope | met | 1 |

<a id="t1"></a>

## T1. Identify and clarify the requirements, gaps and challenges

> Identify and clarify the requirements, and any critical gaps or challenges (5 minutes).

**Pillar:** scope. **Source:** [The brief](../../docs/Starting_document.md), task.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Write the requirements down where decisions can cite them, and keep the gaps visible.

**Where the MVP stands:** The requirements are these constraint pages; the gaps are the production requirements ([P1](production.md#p1)–[P6](production.md#p6)) and [TODO.md](../../TODO.md).

**Delivered by:** [`TODO.md`](../../TODO.md), [`docs/README.md`](../../docs/README.md).

**Decisions:**

- [ADR 0021](../adr/0021-design-records-in-one-database.md): Keep intent, constraints, scope and decisions in one versioned SQLite database, the source of truth, and generate the documents from it

**History:**

- Version 1, from 2026-10-29, active. Recorded from the task of the brief.

<a id="t2"></a>

## T2. Define the initial phase and a system design diagram

> Define the initial phase and create a system design diagram (10 minutes).

**Pillar:** scope. **Source:** [The brief](../../docs/Starting_document.md), task.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Show the parts, the flows and where the MVP stops.

**Where the MVP stands:** The [system design](../../design/SYSTEM-DESIGN.md) and its diagram, and the code architecture in [ARCHITECTURE.md](../../ARCHITECTURE.md).

**Delivered by:** [`ARCHITECTURE.md`](../../ARCHITECTURE.md), [`design/SYSTEM-DESIGN.md`](../../design/SYSTEM-DESIGN.md), [`design/system-design.svg`](../../design/system-design.svg).

**Decisions:** none yet.

**History:**

- Version 1, from 2026-10-29, active. Recorded from the task of the brief.

<a id="t3"></a>

## T3. A working prototype of an MVP

> Get a working prototype of an MVP (40 minutes).

**Pillar:** scope. **Source:** [The brief](../../docs/Starting_document.md), task.

**Standing:** *met*. Met by the MVP, on the test data. For a scope item: the MVP goes this far.

**What it means for the design:** Prove the chain from question to cited answer, running, with tests.

**Where the MVP stands:** Built in about four to five hours rather than 40 minutes, to prove the whole chain with tests and evaluation ([docs/README.md](../README.md)).

**Delivered by:** [`README.md`](../../README.md), [`engineering_search`](../../engineering_search).

**Decisions:** none yet.

**History:**

- Version 1, from 2026-10-29, active. Recorded from the task of the brief.
