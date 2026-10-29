# Agent instructions

## Before every commit

1. Run the full suite: `uv run --frozen pytest -q`. Commit only if it passes. Report the real numbers.
2. Review new and changed tests for tautologies: a test must be able to fail when the behaviour breaks. No asserting a value the test just set, no re-implementing the code under test, no mocks that make the assertion trivially true.
3. Check the change against the constraints and the use case. For each changed file, look up the records that govern it (`governing_records` on the `design-records` MCP server, then `get_constraint` and `get_decision`; or query `design/records/records.sqlite`). Then ask how the new code affects the system:
   - **Within the constraints?** Does it respect the requirements (R) and the scope (S)? Does it build something the brief says already exists (C1–C5 are *assumed*; their stand-ins stay minimal)? Does it break an accepted decision?
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

- `design/records/records.sqlite` is the source of the brief, the constraints and the decision records. `docs/adr/` and `docs/constraints/` are generated from it: edit the database, then run `uv run --frozen python -m design_records generate`. Never edit a generated page; the suite fails if you do.
- Before changing a file or the design, look up the records that govern it: the `design-records` MCP server (`governing_records`, `get_decision`, `get_constraint`, `search_records`) or the database. A change that conflicts with an accepted decision needs a new decision record, not a quiet edit.
- A new decision links the constraints it serves or leaves unmet, the records it supersedes or amends, and the files that implement and test it. `python -m design_records check` must pass. See `design/records/README.md`.
- Constraints with standing *assumed* (C1–C5) exist in the company already. The MVP's readers, folder, stores and chat clients are stand-ins for them (ADR 0020); do not grow them into products.

## Docs

`docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md` and `docs/engineering_knowledge_search_design_notes.html` are dated design inputs (29 October 2026). Do not edit them; record decisions in the design records database and the main docs.
