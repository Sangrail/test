# Plan: from design records to a living specification

29 October 2026. A plan, not a decision. When a phase is agreed, it becomes a decision record in the database.

## What this has become

The project set out to prove one search question. Along the way it grew a second system: a database that holds the **intent**, the **constraints**, the **scope** and the **decisions** of the first, with their history, and drives the documents, the checks and the agent from it. This plan is about that second system.

The aim is a specification that an agent can develop and test against. It mixes three kinds of information:

| Kind | Examples | What it gives |
| --- | --- | --- |
| **Structure** | IDs, pillars, versions, links between items, links to code, scope direction, hard or soft | Traceability, and checks that a machine can run |
| **Sentences** | Statements, reasons, the sections of a decision | Meaning, for people and for the model |
| **Executable criteria** | Acceptance tests, gold sets, properties, contracts | Proof that the code does what an item says |

Be clear about the limit. The sentences stay sentences: structure does not make them true. What becomes formal is the *graph* (what serves, limits or contradicts what), the *invariants* over it, and the *executable criteria* attached to it. That is where the less natural language and the less guesswork come from. A specification is complete enough when the invariants hold and every judgement that cannot be checked has a named owner.

## Where we are

- One versioned SQLite database is the source of truth (ADR 0021): 10 intent items, 17 constraints, 9 scope items, 21 decisions, every version kept.
- Decision links pin the item version they were made under; `needs_review` flags decisions whose items changed.
- The pages and a self-contained viewer are generated; a pre-commit hook regenerates them; the suite fails if they differ.
- The MCP server reads everything and can only propose drafts.

The review (summarised in [README.md](README.md#weaknesses-and-what-comes-next)) found the core sound and these gaps: no links between items, standing that is claimed rather than evidenced, no change sets or authority, a classification that mixes origin with kind, no capabilities or evidence tables, and no way yet to say when the specification is complete.

## Phase 0. Artefacts that cannot be edited by hand

The check already fails when a page differs from the database. It cannot tell *why*: a hand edit and a database change look the same. Stamps tell them apart.

1. **Stamp each generated file.** The first line carries two hashes:

   ```
   <!-- Generated from docs/records/design.sqlite. Do not edit. spec=3f9a…c2 body=81d0…7e -->
   ```

   `body` is the SHA-256 of the rest of the file. `spec` is the fingerprint of the database: the SHA-256 of its deterministic dump. The same stamp goes in `index.html` and, as a SQL comment, in `design.sql`.
2. **Classify each file** on `check`:
   - *current*: the body matches its hash and the spec matches the database;
   - *stale*: the body matches its hash, but the database has moved on. Regenerate;
   - *tampered*: the body does not match its own hash. Someone edited it;
   - *orphan*: a file in `docs/adr/` or `docs/constraints/` with no stamp, or that the database no longer produces.
3. **On tamper**, the hook prints the hand edit as a diff, saves it to `.records/rejected/<file>.<time>.diff` (ignored by git), regenerates the file, and stops the commit with a message: make this change in the database, here is how. The edit is not lost, and it does not land.
4. **The spec fingerprint becomes the version of the specification.** Commit messages carry `Spec: 3f9a…c2`; evidence (phase 2) is recorded against it.
5. Mark the artefacts as generated in `.gitattributes` (`linguist-generated=true`), so reviews collapse them and look at `design.sql` instead.
6. Tests: editing a generated page is reported as *tampered*, not *stale*; changing the database is reported as *stale*; the hook regenerates and refuses; the rejected diff is kept.

Small: about half a day. It makes the rule "never written by hand" mechanical rather than a convention.

## Phase 1. The model the review asked for

Each change is a schema migration, and each migration is a change set in the database itself.

1. **Links between items** (`item_relations`, versioned like the other links): *derives from*, *refines*, *limits*, *defers*, *conflicts with*, *depends on*. This is the change that matters most. It makes "P1 follows from U3" and "S6 limits P1" data, and it is what the mind map draws.
2. **A vision root.** One intent item at the top (proposed: I0, "a lead gets a trustworthy answer to an engineering question without hunting through files"), from which B and U derive. The roots of the graph are then the vision and the *givens* (the environment and the assumptions), which come from outside and derive from nothing.
3. **Origin and kind, apart.** Today the ID letter says where an item came from, and the pillar says what it is. Add `kind` under each pillar:
   - intent: *vision*, *goal*, *use case*;
   - constraint: *environment*, *assumption*, *rule*, *quality*;
   - scope: *floor* (deliver X), *ceiling* (not X), *non-goal*.

   The ID stays stable when the kind changes. P items become deferred scope; T items move out of the specification into a separate "assignment" group that the checks ignore.
4. **Hard and soft.** A flag on constraints. A hard constraint (R1, R8) can never be limited or deferred by scope, and the check refuses a link that tries.
5. **Assumptions carry their risk.** For each *assumption*: what breaks if it is false, and how it will be validated (C3: connector output quality is unknown; validate on a sample of real output).
6. **Statement apart from assessment.** The statement is versioned and changes rarely; it is what decisions pin. The assessment (standing, where the MVP stands) moves to `assessments`, one row per assessment, with the evidence it rests on and the spec fingerprint and commit it was made at. This removes the noise in `needs_review`, which today only avoids it by ignoring those columns.
7. **Change sets.** Each version belongs to a change set: id, kind (*correction*, *clarification*, *new information*, *requirement change*, *scope change*), author, approver, commit. Commits that change records carry `Records-Change: <id>`. Narrowing scope needs the *scope change* kind and an approver who is not the author; the check flags a change set that narrows scope in the same change that an item's standing drops.
8. **Version what is not versioned yet**: the brief, the sources, the groups and the slugs. Refuse a `valid_from` earlier than the version it displaces.

About two days. The data migration is mostly writing the links between the 36 items, which is a grill session in itself (phase 3).

## Phase 2. Capabilities, evidence and invariants: a bounded specification

1. **Capabilities.** Scope as a list that can be counted: each capability (search by text, ask in SQL, read a PDF, admit or refuse under load, …) names the scope item that admits it and the code surfaces that deliver it: modules, HTTP routes, MCP tools, readers. A small scanner lists the surfaces in the code (routes from the app, tools from the MCP servers, readers from the registry, top-level modules), so *code that exceeds scope* becomes a query: a surface that no capability claims.
2. **Acceptance criteria as rows.** Each criterion belongs to an item or a capability: a short structured form (*given*, *when*, *then*, or a property), and the test or gold-set entry that checks it, by name.
3. **Evidence.** The test run writes JUnit XML; `python -m design_records evidence` loads it as rows: criterion, test, result, commit, spec fingerprint. Standing is then *derived*: *met* needs a passing criterion for each claim; a hand-typed *met* with no evidence is a warning, later an error.
4. **Invariants as queries.** Each invariant is a row: an ID, a sentence, and a SQL query that returns the rows that break it. `check` runs them all. The review's set, to start:

   | ID | Invariant |
   | --- | --- |
   | I1 | Every active decision reaches the vision through *serves* and *derives from* links (decisions about process have their own kind) |
   | I2 | Every intent item is served by a decision, or limited or deferred by a scope item |
   | I3 | Every item assessed *met* or *partly met* has evidence that passed at this spec |
   | I4 | A scope item is *exceeded* if and only if a decision *exceeds* it, and only ceilings can be exceeded |
   | I5 | Every decision names the scope item or capability that admits it |
   | I6 | Every intent or constraint item *not met* is limited or deferred by a scope item, and no hard constraint is |
   | I7 | Every link has a reason that names its specific contribution |
   | I8 | `needs_review` and `drafts` are empty, and every code surface belongs to a capability |
   | I9 | No decision serves more than five intent items (a sign of linking everything to everything) |

5. **Open judgements.** What a query cannot decide (is this intent adequate? is this reason true?) becomes a row with an owner and a due date, not a silent gap.
6. **The specification is bounded** when every invariant returns no rows and every open judgement has an owner. That is the stopping rule for a design session, and a status the viewer shows.
7. **Formal proof, where it pays.** One property is absolute: permissions apply before limits, counts and joins (R1, R8), so no output for a user depends on a document that user may not read. Model the access rules and the order of the query pipeline in Alloy or TLA+ (or Lean, as an experiment), and back the model with property-based tests on the real code (Hypothesis: random trees, rules and queries; the restricted result must equal the result over the permitted subset). A second, cheap model: the lifecycle of a record (at most one active version; past versions frozen). Nothing else needs proof; for sentences, a proof only shows that the labels agree.

About three days, most of it the capability scanner and the evidence loader.

## Phase 3. Grill me against the database

The grill skill becomes a loop over the database rather than a free conversation:

1. **Questions come from failing invariants.** Each failing row is a question: "B1 is served by no decision and limited by no scope item: does a decision serve it, or does scope defer it?"
2. **A fixed question bank per kind**: who is the actor, what is the measure, what would show it false, who may change it; for an assumption, what breaks if it is false; for a ceiling, what would cross it.
3. **Answers become drafts**, through `propose_change` and new tools for links, criteria and capabilities. Nothing is activated in the session. At the end, the person reads one change set and activates it.
4. **The session ends** when the invariants hold or every remaining failure is an owned judgement. The output is a change set, a new spec fingerprint, and the regenerated documents.

This is how a new project would start: a vision, the givens, the use cases, the floors and ceilings, a first decision or two, and the criteria that will prove them, before any code.

## Phase 4. The specification drives development and QA

1. **Work packets.** For a capability or a change, the MCP server returns everything that bounds it: the intent it serves, the hard constraints it must keep, the scope ceiling it must not cross, the decisions in force, the criteria that must pass, and the code surfaces it touches. The agent starts from that, not from a paragraph.
2. **Test skeletons from criteria.** A criterion with no test produces a failing test skeleton named after it. QA is then "make the criteria pass", and the evidence loader closes the loop.
3. **The commit gate, mechanical first.** The hook already regenerates and checks. Add: every ID in the `Constraints:` line exists and is active; a new code surface needs a capability; the invariants hold, or the failures are in the commit message.
4. **An LLM review, advisory.** In a separate context from the agent that wrote the change, it compares the diff with the work packet and reports contradictions with a decision's words, each with a file and line and a record ID. It is calibrated on seeded violations (a change that leaks a count, a change that adds a reader) and never blocks a commit on its own.

## Phase 5. Seeing the specification

The viewer stays one self-contained file. The graph libraries are vendored and inlined at generate time, so it still works offline (a CDN would be simpler, but breaks that).

| View | What it shows | Library |
| --- | --- | --- |
| **Mind map** | The vision at the centre; intent, then constraints and scope, then decisions, then files, radiating out. Givens on their own branch. Click to expand or collapse | Cytoscape.js with a radial (concentric or breadth-first) layout, or D3's tree with a radial projection |
| **Relationship graph** | The full graph, including the cross-links a mind map hides: *limits*, *conflicts with*, *exceeds*. Filter by pillar or relation; highlight orphans and items that fail an invariant | Cytoscape.js (fcose layout) |
| **Traceability flow** | Intent to constraints to decisions to code, as bands whose width is the number of links. Shows at a glance where decisions pile up and what is starved | D3 Sankey |
| **Scope gauge** | Floors met or not; ceilings held or exceeded, with the decisions that exceed them | Plain SVG |
| **Time travel** | A slider that redraws any view as of a date or a spec fingerprint, from the history. What did the spec say when ADR 0018 was made? | Same data, filtered by `valid_from` and `valid_to` |
| **Bounded?** | The invariants, each passing or failing with its rows, and the open judgements with their owners | Plain HTML |

**A mind map needs a tree, and the specification is a graph.** Each item gets one *primary parent*: the first *derives from* link, or, for a decision, the intent item it serves most directly. The other links are drawn as dashed cross-links, or shown on demand. Choosing the primary parent is itself a modelling decision, so it is stored, not guessed.

The mind map can be tried before phase 1, with the links that exist today (decisions *serve* items), as a throwaway prototype. It will show at once why links between items are needed: without them, intent and constraints are flat lists with decisions hanging off them.

## Order, and what to decide first

| Order | Phase | Effort | Why this order |
| --- | --- | --- | --- |
| 1 | Phase 0: stamps and tamper detection | ½ day | Small, and it makes "artefacts only" mechanical |
| 2 | Mind map prototype on today's links | ½ day | Cheap, visual, and it tests the idea before the schema changes |
| 3 | Phase 1: links between items, kinds, assessments, change sets | 2 days | Everything after depends on the links |
| 4 | Phase 5: mind map, graph and flow on the new links | 1 day | Now there is a graph worth drawing |
| 5 | Phase 2: capabilities, evidence, invariants | 3 days | Makes the specification bounded and the standing true |
| 6 | Phase 3: grill against the database | 1 day | Needs the invariants to generate its questions |
| 7 | Phase 4: work packets, test skeletons, the gate | 2 days | Needs criteria and capabilities |

**Decisions to make first:**

1. **On a hand edit**, regenerate and refuse the commit, keeping the edit as a diff (proposed), or regenerate silently?
2. **The viewer's libraries**: vendored and inlined, so the file works offline (proposed), or loaded from a CDN, which is simpler but needs the network?
3. **Where the records system lives.** It is no longer part of the search MVP. Keep it in this repository, dogfooded on this project, until phase 3 works (proposed); then move `design_records` to its own repository, with its own specification in its own database.
4. **The vision root**: add I0, and agree its wording.

**Risks:**

- **The binary source.** With change sets and fingerprints, two writers are more likely, and git still cannot merge the database. If a second writer appears, revisit ADR 0021: a deterministic text dump as the source, with the database built from it.
- **Ceremony.** Every phase adds work to a change. It pays only if the records are kept as the code moves. Watch for `Constraints:` lines that say "serves U1" on every commit.
- **Fake traceability.** Links are easy to add and hard to judge; I7 and I9 are there to catch the worst of it, and the advisory LLM review for the rest.
- **The spec fitting the code.** Agents propose, people activate; scope narrows only with an approver who is not the author.
