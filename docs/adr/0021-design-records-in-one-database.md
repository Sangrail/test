---
status: accepted (to be evaluated after a few changes)
date: 2026-10-29
---
<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

# Keep the brief, the constraints and the decision records in one SQLite database, and generate their pages from it

**Serves:** [T1](../constraints/task.md#t1) (clarify the requirements), [R4](../constraints/requirements.md#r4) (the tests enforce the use case).

## Context

The constraints are cited by every decision record and by other documents. The links, the Serves column of the index and the lists of citing records were kept by hand, and they drifted: the index listed [R1](../constraints/requirements.md#r1) for [ADR 0018](0018-admission-control-and-the-time-budget.md) when the record did not, [ADR 0016](0016-structured-facts-and-client-written-sql.md) lacked [S4](../constraints/scope.md#s4), and a link pointed at a heading that had been removed. Code paths in records go stale when files move. An agent changing the code had no structured way to find the decisions that govern a file.

## Decision

- **One SQLite database**, `design/records/records.sqlite`, holds the brief verbatim by section, the constraint groups and constraints with their standing, the decision records (metadata, notes and sections), and the links between them: which constraints a decision serves, leaves unmet or cites; which decisions supersede, amend or extend which; which files implement, test or measure a decision; and which files stand in for, enforce, measure or deliver a constraint. It is only a tracking database for the design; the product does not read it.
- **It is the source.** `python -m design_records generate` writes every ADR page, the ADR index, the constraint pages and a SQL dump (`records.sql`) for review in diffs. Each generated page says so at the top. docs/README.md and the dated design inputs stay hand-written.
- **A check runs in the suite** ([`tests/test_design_records.py`](../../tests/test_design_records.py)). It fails when a generated page differs from what the database produces; a file named in the database does not exist; a decision mentions a constraint or a code file that it does not link; the brief in the database differs from docs/Starting_document.md; a link or anchor in a generated page is broken; or a foreign key is broken.
- **A read-only MCP server** (`python -m design_records mcp`) gives an agent the records during development: an overview, a constraint or a decision with its links, a search, the decisions and constraints that govern a file, the check, and read-only SQL. AGENTS.md tells agents to consult it before a design change. It is registered for Claude Code in `.mcp.json`.
- **A browser view** (`design/records/index.html`) reads the SQLite file directly with sql.js and shows the brief with its constraints, each constraint and decision with its links and files, and a matrix of constraints against decisions. It changes nothing.

## Consequences

- A change to a decision is an edit to the database, then `generate`. Editing a generated page by hand fails the test. The edit is less convenient than editing Markdown: the `sqlite3` shell's `edit()` function opens a text field in an editor.
- The database is binary in git. `records.sql` is the form to review; the check keeps it in step.
- Prose stays in text fields. The database checks that the structure, the links and the files are consistent, not that the words are right.
- To be evaluated after a few real changes. If editing prose in SQLite is too awkward, keep the structure in the database and move the prose to files that it references. Write tools for the MCP server are a later option; for now every write goes through `generate` and the check.
- **No history yet.** Rows are updated in place, so the database cannot say what a constraint said when a decision was made, which decisions rest on a constraint that has since changed, or which records are active and which displaced. Before the records become a living spec that features work within, they need append-only versions, links from decisions to the constraint versions they were made under, features as records, and proposals instead of writes for agents. The weaknesses and the design are in [design/records/README.md](../../design/records/README.md#weaknesses-and-what-comes-next).
- **A binary source does not merge.** Two branches that change records conflict on the database file. Making text files the source, with SQLite built from them as an index, is the likely next step and is to be decided before history is built.

## Implementation

Done. Schema, rendering and checks: [`design_records/records.py`](../../design_records/records.py). MCP server: [`design_records/mcp_server.py`](../../design_records/mcp_server.py). Database, dump, view and how to edit: [design/records/](../../design/records/README.md). Tests: [`tests/test_design_records.py`](../../tests/test_design_records.py) (the generated pages match the database, the records are consistent, and each check fails on a broken copy of the database; the MCP tools return the links from the database).
