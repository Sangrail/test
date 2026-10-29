---
status: accepted (to be evaluated after a few changes)
date: 2026-10-29
version: 2
---
<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

# Keep intent, constraints, scope and decisions in one versioned SQLite database, the source of truth, and generate the documents from it

**Serves:** [T1](../constraints/task.md#t1) (clarify the requirements), [R4](../constraints/requirements.md#r4) (the tests enforce the use case).

## Context

The constraints are cited by every decision record and by other documents. The links, the Serves column of the index and the lists of citing records were kept by hand, and they drifted: the index listed [R1](../constraints/requirements.md#r1) for [ADR 0018](0018-admission-control-and-the-time-budget.md) when the record did not, [ADR 0016](0016-structured-facts-and-client-written-sql.md) lacked [S4](../constraints/scope.md#s4), and a link pointed at a heading that had been removed. Code paths in records go stale when files move. An agent changing the code had no structured way to find the decisions that govern a file.

## Decision

- **One SQLite database is the source of truth**, `docs/records/design.sqlite`, with its schema in [`design_records/schema.sql`](../../design_records/schema.sql). It holds the brief verbatim by section; the items of intent, constraint and scope, each with its pillar and standing; the decision records; and the links between them and to the files of the repository. It is a tracking database for the design; the product does not read it.
- **Every record is versioned and append-only.** An item or a decision has a stable ID and a list of versions: *proposed* (a draft), *active* (at most one), *displaced* or *withdrawn*, each with its reason, author and dates. Triggers refuse edits and deletes of active and past versions. Changes are plain SQL in the `sqlite3` shell, through views: an update of `constraint_current` or `decision_current` adds a version and displaces the old one; `drafts` holds versions being written; a delete withdraws a record and keeps its history.
- **A decision link records the item version it was made under.** When the wording or meaning of an item changes, or it is withdrawn, the `needs_review` view lists the decisions made under the old version until a review confirms them or a new version changes them. A new assessment (standing, where the MVP stands) does not.
- **The documents are build artefacts.** `python -m design_records generate` writes every ADR page, the ADR index, the constraint pages, a SQL dump (`docs/records/design.sql`) for review in diffs, and a self-contained browser view (`docs/records/index.html`) of the pillars, the decisions, a timeline of every change and a matrix. A pre-commit hook (`.githooks/pre-commit`) runs it and stages the result. Nobody edits these files.
- **A check runs in the suite** ([`tests/test_design_records.py`](../../tests/test_design_records.py)). It fails when a generated file differs from what the database produces; the database schema differs from schema.sql; a file named in the database does not exist; a decision mentions an item or a code file that it does not link; the brief differs from docs/Starting_document.md; a link is broken; or a foreign key is broken. Open drafts, decisions that need review and scope items not met are warnings.
- **An MCP server** (`python -m design_records mcp`) gives an agent the records while it works: the records that govern a file, an item or a decision with its history, what needs review, drafts, search, the check and read-only SQL. It can propose a change, which becomes a draft. It cannot activate one: a person does, so an agent cannot change the spec to fit its code.

## Consequences

- The database, not the git history, says what an item said when a decision was made, which decisions rest on items that have changed since, and what is active and what displaced.
- The database is binary in git, so two branches that change records conflict on it and git cannot merge them. `design.sql` makes a change reviewable but does not merge. The alternative, a text dump as the source with SQLite built from it, keeps merging but makes the database a derived copy; the product owner chose the database as the source. With one writer this holds; with several, it is the first thing to break.
- Prose is in text columns. The check keeps the structure, the links and the files consistent, not the words true. Standing is typed by hand, not derived from evidence.
- To be evaluated after a few real changes. The review of the approach, and what a living specification still needs, are in [docs/records/README.md](../records/README.md#weaknesses-and-what-comes-next).

## Implementation

Done. Schema: [`design_records/schema.sql`](../../design_records/schema.sql). Rendering and checks: [`design_records/records.py`](../../design_records/records.py), with the template of the browser view, [`design_records/viewer.html`](../../design_records/viewer.html). MCP server: [`design_records/mcp_server.py`](../../design_records/mcp_server.py). Database, dump, view and how to change the records: [docs/records/](../records/README.md). Tests: [`tests/test_design_records.py`](../../tests/test_design_records.py) (the generated files match the database; a change adds a version and cannot rewrite the past; a changed item flags the decisions made under it; each check fails on a broken copy; the viewer needs no network; the MCP server proposes drafts and cannot activate them).

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 2 | 2026-10-29 | now | The product owner made the database the source of truth, with history, generated documents, a pre-commit hook and an MCP server that proposes drafts. | sangrail (via Claude Code) |
| 1 | 2026-10-29 | 2026-10-29 (Displaced by version 2) | Recorded when the decision was made. | sangrail |
