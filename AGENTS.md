# Agent instructions

## Before every commit

1. Run the full suite: `uv run --frozen pytest -q`. Commit only if it passes. Report the real numbers.
2. Review new and changed tests for tautologies: a test must be able to fail when the behaviour breaks. No asserting a value the test just set, no re-implementing the code under test, no mocks that make the assertion trivially true.
3. Check the change against the constraints and the use case. For each changed file, look up the records that govern it (`governing_records` on the `design-records` MCP server, then `get_constraint` and `get_decision`; or query `docs/records/design.sqlite`). Then ask how the new code affects the system:
   - **Within the constraints?** Does it respect the items whose pillar is *constraint* (the environment C, the requirements R)? Does it build something the brief says already exists (C1–C5 are *assumed*; their stand-ins stay minimal)? Does it break an accepted decision?
   - **Scope is the arbiter.** Going beyond a scope item is acceptable, but record it: the decision links the item with *exceeds*, and its standing is *exceeded* (as S5 is for the readers). Falling short of a scope item is the failure to flag. Scope never excuses a hard constraint such as R1 or R8.
   - **Towards the use case?** Does it move a use case (U1–U6) forward, hold it, or set it back? Not yet meeting a use case is fine when the change is on the way to it; say which one and what is still missing.
   - **Production requirements?** Does it add to a known gap (P1–P6), for example another single point on the query path (P1) or another place that trusts an unverified user (P2)?
   - **Flag, do not hide.** If the change steps outside a constraint or the scope, or works against a use case, stop and tell the user before committing, and say so in the commit message. If the constraint or the decision is what should change, propose a new decision record rather than a quiet exception.
   - **Record it.** End the commit message with a `Constraints:` line that names what the change serves and anything it flags, for example `Constraints: serves U3, R1; stand-in for C3 only; flags P1 (one more lock on the query path).`
4. Commit at each significant, tested milestone, on a feature branch. Merge to `main` only when asked.

## Design

- Deep modules, narrow interfaces (Ousterhout). Hide complexity behind small APIs.
- Inject dependencies at the edges: the index store and the readers are passed in, not imported where used. `runtime.py` wires them.
- Readers live in `engineering_search/indexing/readers/` and are registered in one place (the registry factory). Several versions of a reader for one format are allowed; the registry selects one.
- Indexing and searching are separate lines that meet only at the store.
- Permissions apply before limits, ranking, counts, joins and aggregates.

## Design records

- `docs/records/design.sqlite` is the source of truth for intent, constraints, scope and the decision records, with every version of each. `docs/adr/`, `docs/constraints/`, `docs/records/design.sql` and `docs/records/index.html` are build artefacts: never edit them. Change the database with SQL through its views (`constraint_current`, `decision_current`, `decision_section_current`, `drafts`, `reviews`), always with a `change_reason`; each change adds a version and keeps the old one. The pre-commit hook (`.githooks/pre-commit`; turn on with `git config core.hooksPath .githooks`) regenerates the artefacts, or run `uv run --frozen python -m design_records generate`. See `docs/records/README.md`.
- Before changing a file or the design, look up the records that govern it: the `design-records` MCP server (`governing_records`, `get_decision`, `get_constraint`, `history`, `search_records`) or the database. A change that conflicts with an accepted decision needs a new decision version or record, not a quiet edit.
- From the MCP server, propose changes with `propose_change`: it writes a draft, which the user reads and activates. Do not activate records you proposed yourself unless the user asks you to make the change.
- Before a commit, `needs_review` and `drafts` should be empty, or the commit message says why not. When an item's wording changes, review each decision it lists: confirm it in `reviews`, or give it a new version.
- A new decision links the items it serves, leaves unmet or goes beyond, the records it supersedes or amends, and the files that implement and test it. `python -m design_records check` must pass.
- Constraints with standing *assumed* (C1–C5) exist in the company already. The MVP's readers, folder, stores and chat clients are stand-ins for them (ADR 0020); do not grow them into products.

## Docs

`docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md` and `docs/engineering_knowledge_search_design_notes.html` are dated design inputs (29 October 2026). Do not edit them; record decisions in the design records database and the main docs.
