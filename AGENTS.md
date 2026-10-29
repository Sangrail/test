# Agent instructions

## Before every commit

1. Run the full suite: `uv run --frozen pytest -q`. Commit only if it passes. Report the real numbers.
2. Review new and changed tests for tautologies: a test must be able to fail when the behaviour breaks. No asserting a value the test just set, no re-implementing the code under test, no mocks that make the assertion trivially true.
3. Commit at each significant, tested milestone, on a feature branch. Merge to `main` only when asked.

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
