# Design records

`records.sqlite` is a plain SQLite database that tracks, in one place and in a structured way, the brief, its constraints, use case and scope, the requirements added since, and the architecture decision records, with the links between them and to the files of the repository ([ADR 0021](../../docs/adr/0021-design-records-in-one-database.md)). The product does not read it.

It is the source of these pages, which are generated and must not be edited by hand:

- [docs/adr/](../../docs/adr/README.md): every decision record and the index;
- [docs/constraints/](../../docs/constraints/README.md): every constraint, with the decisions and files linked to it;
- `records.sql`: a dump of the database, so that changes can be reviewed in a diff.

## Commands

```bash
uv run --frozen python -m design_records generate
```

```bash
uv run --frozen python -m design_records check
```

`generate` writes the pages and the dump. `check` lists what differs or is broken; `tests/test_design_records.py` runs it in the suite, so a hand-edited page, a missing file or an unlinked mention fails the tests.

## The data model

| Table | Holds |
| --- | --- |
| `brief_sections` | [The brief](../../docs/Starting_document.md), verbatim, by section. The check compares it with the file |
| `sources` | Where a constraint comes from: the brief, a decision during the MVP, the 29 October design inputs, or production needs |
| `constraint_groups` | B background, C constraints from the brief, U use case, T task, S scope, R requirements added during the MVP, P production requirements |
| `constraints` | One row per ID: statement, source, standing (*context*, *assumed*, *met*, *partly met*, *not met*), what it means for the design, where the MVP stands |
| `decisions`, `decision_sections` | Each record's number, title, status, date, notes, and its Context, Decision, Consequences and Implementation |
| `decision_constraints` | Which constraints a decision *serves*, leaves *not met* or *cites*, with a reason |
| `decision_relations` | Which decisions *supersede in part*, *amend* or *extend* which |
| `decision_files` | Which files *implement*, *test* or *measure* a decision |
| `constraint_files` | Which files are a *stand-in* for a constraint, or *enforce*, *measure* or *deliver* it |

Constraint IDs in the text are written bare (`U3`); the generator links them. A decision that mentions an ID or a code path must have the matching row, or the check fails.

## Changing a record

Use the `sqlite3` shell. Its `edit()` function opens a text field in `$EDITOR`:

```bash
sqlite3 design/records/records.sqlite "UPDATE decision_sections SET body = edit(body) WHERE number = 18 AND heading = 'Consequences'"
```

A new decision is a row in `decisions`, four rows in `decision_sections`, and its links. Then run `generate` and `check`, and commit the database, the dump and the pages together.

## Looking at it

**In a browser.** `index.html` reads `records.sqlite` directly (with sql.js) and shows the brief with its constraints, each constraint and decision with its links and files, and a matrix of constraints against decisions. Serve the repository root on the local machine only, then open <http://127.0.0.1:8012/design/records/>:

```bash
uv run --frozen python -m http.server 8012 --bind 127.0.0.1
```

**From an agent.** A read-only MCP server gives an agent the records while it works: `overview`, `get_constraint`, `get_decision`, `governing_records` (the decisions and constraints linked to a file or folder), `search_records`, `check` and `query_records` (read-only SQL). It is registered for Claude Code in [`.mcp.json`](../../.mcp.json) as `design-records`. For another client:

```bash
uv run --frozen python -m design_records mcp
```

## Weaknesses and what comes next

This is a first cut, built in an hour, and it should be judged as one. What it does well: one structured place for the brief, the constraints and the decisions; links that are checked rather than trusted; and an agent can ask which decisions govern a file before it changes it. What it does badly:

1. **No history.** Rows are updated in place. The database cannot say what a constraint said when a decision was made, which decisions rest on a constraint that has since changed, or which records are active and which displaced. Git keeps the old files, but not as data an agent can query. Supersession is a free-text status plus `decision_relations`; constraints, use cases and scope have no versions at all. An ADR log is meant to be append-only, and `UPDATE` breaks that.
2. **A binary source does not merge.** Two branches that change records conflict on `records.sqlite`, and git cannot resolve it; `records.sql` helps review, not merging. With more than one person or agent writing, this is the first thing to break.
3. **Standing is a claim, not evidence.** *met* is typed by hand. Nothing ties it to the tests listed under *enforced by*, so the database can say *met* while the test fails or does not exist.
4. **Links are coarse.** A folder path matches everything under it (T3 covers all of `engineering_search/`), a rename breaks a path, and there are no links to a test by name or to a symbol. *cites* is inferred from words in the prose, which ties the structure to the wording.
5. **No governance.** Nothing records who changed a constraint, why, or who approved it. The brief, the product owner and production needs are different authorities, and an agent with write access could change the spec to fit the code: drift in reverse.
6. **No features.** The work to come is features that operate within constraints and produce decisions. There is no table for them.
7. **Prose in text columns** is awkward to edit and to review, and the check cannot say whether the words are true.
8. **Weight.** For a 4–5 hour MVP this is a lot of machinery. It pays only if the records are kept up as the project grows.

**What a living spec needs.** If the records are to become the spec that features and agents work within:

- **Versions, append-only.** A stable identity per record (`U3`, ADR 18), and a version table per kind: the statement, a status (*proposed*, *active*, *displaced*, *withdrawn*), `valid_from`, `valid_to`, `displaced_by`, the reason, the author and the approver. Old versions are never updated; triggers refuse it. The current spec is a view: active versions with no `valid_to`.
- **Links to versions, not to identities.** A decision records the versions of the constraints it was made under. When a constraint gets a new version, one query lists the decisions made under the old one: *needs review*. This is the main payoff.
- **Features** as records: a feature names the constraints it must operate within and the decisions it produced, so an agent starting a feature gets its constraints from the database.
- **Proposals, not writes.** MCP write tools create *proposed* versions only. A person accepts them, and the check runs. An agent can suggest a change to the spec but cannot make it alone.
- **Evidence for standing.** Derive *met* from the named tests passing in the suite, not from a typed word.
- **Decide the source of truth first.** Either keep SQLite as the source, append-only, and accept that branches cannot merge, or make text files the source (one file per record, holding its versions) and build SQLite from them as an index for queries, the view and the MCP server. The second keeps git review and merging and still gives agents structured data. Recommended, before building history.

[ADR 0021](../../docs/adr/0021-design-records-in-one-database.md) records the decision and the evaluation; [TODO.md](../../TODO.md) has the follow-up.
