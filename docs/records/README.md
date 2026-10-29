# Design records

`design.sqlite` is the source of truth for the design of this project ([ADR 0021](../adr/0021-design-records-in-one-database.md)). It holds four pillars, each with every version it has had:

| Pillar | What it is | Where it is shown |
| --- | --- | --- |
| **Intent** | What the system is for. The direction that every decision flows from | [docs/constraints](../constraints/README.md) |
| **Constraints** | What the system must work within: the environment, the data, the rules it must keep | [docs/constraints](../constraints/README.md) |
| **Scope** | How far this work goes down the road | [docs/constraints](../constraints/README.md) |
| **Decisions** | The architecture decision records, each linked to the items it serves | [docs/adr](../adr/README.md) |

Decisions flow from intent and constraints. **Scope is the arbiter.** Intent and constraints may point further than this work goes; scope says how far it goes. Going beyond a scope item is acceptable, and is recorded: the decision links the scope item with *exceeds*, and the item's standing is *exceeded* (S5: the MVP's own readers go beyond "extraction is the connectors' job"). Falling short of a scope item is the failure to flag: `check` warns about any scope item that is *not met*.

The product does not read this database. It is for the people and agents who build the product.

## What is generated, and what is not

Generated from the database, at commit time, and never edited by hand:

- [docs/adr/](../adr/README.md): every decision record and the index;
- [docs/constraints/](../constraints/README.md): every item of intent, constraint and scope, with its decisions, its files and its history;
- [`index.html`](index.html): a self-contained view in a browser, with no network, of the pillars, the decisions, a timeline of every change, and a matrix of items against decisions. Open the file directly;
- `design.sql`: a dump of the database, so that each change can be reviewed in a diff.

Hand-written: this README, [the schema](../../design_records/schema.sql), and [the generator](../../design_records/records.py).

```bash
uv run --frozen python -m design_records generate
```

```bash
uv run --frozen python -m design_records check
```

The pre-commit hook in `.githooks/pre-commit` runs `generate`, stages the generated files, and then runs `check`; a commit fails if the records are inconsistent. Turn it on once per clone:

```bash
git config core.hooksPath .githooks
```

`tests/test_design_records.py` runs the same check in the suite, so a hand-edited page fails the tests even without the hook.

## The model

Each record has a stable identity and a list of versions. A version is *proposed* (a draft, which can be edited), *active* (at most one per record), *displaced* (replaced by a newer version) or *withdrawn* (the record no longer applies). Active and past versions cannot be edited or deleted: triggers refuse it. Nothing is overwritten.

| Table | Holds |
| --- | --- |
| `brief_sections` | [The brief](../Starting_document.md), verbatim, by section. The check compares it with the file |
| `sources` | Where an item comes from: the brief, the product owner, a decision during the MVP, the 29 October inputs, production needs |
| `constraint_groups` | Where items came from: B background, C environment, U use case, T task, S scope, R added during the MVP, P production |
| `constraints`, `constraint_versions` | Each item's ID, and its versions: pillar (*intent*, *constraint*, *scope*), statement, source, what it means for the design, standing, where the MVP stands, why the version exists, who made it, when it was active |
| `constraint_files` | Files that are a *stand-in* for an item, or *enforce*, *measure* or *deliver* it, per version |
| `decisions`, `decision_versions`, `decision_sections` | Each record's number and slug, and its versions: title, status, notes, and its Context, Decision, Consequences and Implementation |
| `decision_constraints` | Items a decision version *serves*, leaves *not met*, *exceeds* (scope) or *cites*, with a reason and the item version it was made under |
| `decision_relations` | Decisions that *supersede in part*, *amend* or *extend* others |
| `decision_files` | Files that *implement*, *test* or *measure* a decision |
| `decision_reviews` | A confirmation that a decision still holds under a newer version of an item it links |

Views give the current records (`constraint_current`, `decision_current`, `decision_section_current`, `decision_constraint_current`, …) and the questions the history answers: `history` (every version), `needs_review`, `drafts` and `reviews`.

The ID's letter says where an item came from; the pillar says what kind of item it is. R2 ("an answer, not a list of passages") came from the product owner during the MVP, and it is intent.

## Changing the records

Use the `sqlite3` shell on `docs/records/design.sqlite`. The views accept plain SQL and turn each change into a new version. Every change needs a `change_reason`. Then run `generate` (or commit, and the hook runs it).

**Change an item.** One statement adds a version and displaces the old one:

```sql
UPDATE constraint_current
   SET statement = 'The answer comes in under 5 seconds.',
       change_reason = 'The product owner tightened the budget', changed_by = 'sangrail'
 WHERE id = 'U3';
```

**Add an item.** It is active at once. The ID starts with its group's letter and is never reused:

```sql
INSERT INTO constraint_current (id, group_code, pillar, title, statement, source_id, meaning, standing, mvp, change_reason, changed_by)
VALUES ('S7', 'S', 'scope', 'No upload of documents', 'Users do not upload documents; the repository is the only source.',
        'owner', 'Upload is not built beyond the test page.', 'met', 'Upload accepts Markdown on the test page only.',
        'Added by the product owner', 'sangrail');
```

**Withdraw an item.** Its versions, its anchor and its history are kept:

```sql
DELETE FROM constraint_current WHERE id = 'S7';
```

**Change a decision.** A header field or one section, active at once:

```sql
UPDATE decision_current SET status = 'superseded in part by 0022', change_reason = 'ADR 0022 replaces the lock' WHERE number = 18;
UPDATE decision_section_current SET body = edit(body), change_reason = 'Measured on 400 files' WHERE number = 18 AND heading = 'Implementation';
```

`edit()` opens the text in `$EDITOR`. Change one section per statement: each row changed makes its own version.

**A larger change as a draft.** Copy the active version, change what you need, then activate it:

```sql
INSERT INTO drafts (kind, id, change_reason, changed_by) VALUES ('decision', '10', 'Link R8, folder authorisation', 'sangrail');
INSERT INTO decision_constraints (number, version, constraint_id, relation, position, reason)
SELECT 10, version, 'R8', 'serves', 21, 'no view inside unauthorised folders'
  FROM decision_versions WHERE number = 10 AND lifecycle = 'proposed';
UPDATE decision_versions SET lifecycle = 'active' WHERE number = 10 AND lifecycle = 'proposed';
```

`DELETE FROM drafts WHERE kind = 'decision' AND id = '10'` discards a draft instead.

**A new decision** starts as a draft with four empty sections. It cannot be activated until the sections are written and it serves at least one item:

```sql
INSERT INTO decision_current (number, slug, title, summary, change_reason, changed_by)
VALUES (22, 'answer-cache', 'Cache answers per user', 'Cache answers per user and version', 'New decision', 'sangrail');
```

**After an item changes**, `needs_review` lists the decisions made under its old wording. For each one, either give the decision a new version, or confirm it:

```sql
SELECT * FROM needs_review;
INSERT INTO reviews (number, constraint_id, note, reviewed_by)
VALUES (18, 'U3', 'The 8 s budget is inside the new 9 s limit; the decision stands.', 'sangrail');
```

A new assessment (standing, or where the MVP stands) does not need a review; a new statement, title, pillar or meaning does. A review holds across later versions of the decision.

## Asking the records

```sql
-- What changed, newest first
SELECT kind, id, version, lifecycle, change_reason, valid_from FROM history ORDER BY valid_from DESC LIMIT 20;
-- What an item said when a decision was made
SELECT v.statement FROM decision_constraint_current l
  JOIN constraint_versions v ON v.constraint_id = l.constraint_id AND v.version = l.constraint_version
 WHERE l.number = 18 AND l.constraint_id = 'U3';
-- Scope the work goes beyond, and scope it falls short of
SELECT id, title, standing FROM constraint_current WHERE pillar = 'scope' AND standing IN ('exceeded', 'not met');
-- Decisions that trace to no intent item directly
SELECT number, title FROM decision_current d WHERE NOT EXISTS (SELECT 1 FROM decision_constraint_current l
  JOIN constraint_current c ON c.id = l.constraint_id WHERE l.number = d.number AND c.pillar = 'intent' AND l.relation = 'serves');
```

**From an agent.** The MCP server, registered for Claude Code in [`.mcp.json`](../../.mcp.json) as `design-records`, gives an agent `overview`, `governing_records` (the records that govern a file), `get_constraint` and `get_decision` (with history, and earlier versions), `history`, `needs_review`, `drafts`, `search_records`, `check` and `query_records` (read-only SQL). `propose_change` writes a draft version; it cannot activate one. A person reads the draft and activates it, so an agent cannot change the spec to fit its code. For another client:

```bash
uv run --frozen python -m design_records mcp
```

## Weaknesses and what comes next

[LIVING-SPEC-PLAN.md](LIVING-SPEC-PLAN.md) plans how to answer these, in phases.

A first cut, built in a few hours of an MVP, and it should be judged as one. An independent review of the approach (29 October 2026) found the core sound (append-only versions, links pinned to the item version, `needs_review`) and these weaknesses, most important first:

1. **The source does not merge.** The database is binary in git. Two branches that change records conflict on it, and git cannot resolve the conflict; `design.sql` helps review, not merging. The review recommends a deterministic text dump as the source, with SQLite built from it, and decision numbers allocated at merge time. The product owner chose the database as the source. With one writer this holds; with several, it is the first thing to break.
2. **Standing is a claim, not evidence.** *met* is typed by hand. R5–R8 claim *met* or *partly met* with no file that *enforces* them, and R5 claims *met* while saying it was not measured on hundreds of real files. Standing should be split from the statement into an assessment derived from tests that passed.
3. **Change sets and authority are missing.** Nothing ties a change to a commit or says what kind it is (a correction, a clarification, new information, a requirement change, a scope change) or who approved it. Narrowing scope should need more authority than widening it, and a change that narrows scope as an item's standing drops should be flagged. A `Records-Change:` trailer on each commit, and a CI check that past versions in the dump never change, would close this; the triggers prevent accidents, not tampering.
4. **There are no links between items.** "P1 follows from U3" and "S6 limits P1" are prose. With *derives from*, *refines*, *limits*, *defers* and *conflicts with*, these become checkable: every decision traces to intent; every intent item is served by a decision or limited by a scope item; every item *not met* is limited or deferred by scope. Scope items also need a direction: a *ceiling* (S5, S6: "not X") can be exceeded; a *floor* (S2: "deliver X") can fall short. Hard constraints (R1, R8) are outside scope's reach: scope can never excuse them.
5. **Some classification is wrong or missing.** C1–C5 are assumptions and need, each, the consequence if false and how to validate it. P items are deferred scope rather than limits on this work. T items are the developer's assignment, not the system's specification. R7 is an environment fact. The S4 inputs asked for CSV, XLSX and content detection, which conflicts with C3; ADR 0020 resolves it, but the conflict is not recorded as one. There is no table for capabilities (scope as a list mapped to code), non-goals, or evidence.
6. **Some tables are not versioned**: the brief, the sources, the groups and the slugs. `valid_from` can be set by hand, so a version can be backdated.
7. **It is not yet a portable specification.** The records give the rationale and the state of one implementation. Rebuilding or verifying the system also needs the contracts (the reader interface, the HTTP and MCP schemas), the acceptance tests and gold sets linked by name, the semantics of the access rules, and a glossary.

**Bounding the problem.** A design session ("grill me") should end when a fixed set of invariants holds, each a SQL query that returns the rows that break it, and every judgement that cannot be checked is assigned to a named person. Today, for example, ADRs 2, 20 and 21 trace to no intent item, and B1 and B2 are served by no decision; with links between items both would resolve through the use case. Formal proof is worth it on the one absolute property, that permissions apply before limits, counts and joins (R1, R8): a non-interference property small enough to model in Alloy, TLA+ or Lean, backed by property-based tests. For intent, decisions and scope, whose atoms are sentences, a proof would show only that the labels agree.

**What an LLM can and cannot check.** Mechanical gates come first: the queries above, an empty `needs_review` and `drafts` on `main`, every ID in a commit's `Constraints:` line active. An LLM judge can say whether a change contradicts a decision's words, or whether intent is thin, but it agrees with the framing it is given and varies from run to run. Keep it advisory, in a separate context, with a file and line and a record ID for every finding.
