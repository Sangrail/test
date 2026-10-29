# Agent instructions

## Before every commit

1. Run the full suite: `uv run --frozen pytest -q`. Commit only if it passes. Report the real numbers.
2. Review new and changed tests for tautologies: a test must be able to fail when the behaviour breaks. No asserting a value the test just set, no re-implementing the code under test, no mocks that make the assertion trivially true.
3. Check the change against the brief and the decisions. The brief is `docs/Starting_document.md`; its pillars (background, constraints, use case, task, scope) are analysed, one ID per item, in `docs/constraints/`, and the decisions that follow from them are in `docs/adr/`. For each change ask:
   - **Within the constraints?** Does it respect the constraints of the brief? Does it build something the brief says already exists (the connectors, the stores, the chat shell)? Stand-ins for those stay minimal and are labelled as stand-ins. Does it break an accepted decision?
   - **Towards the use case?** Does it move the use case forward, hold it, or set it back? Not yet meeting it is fine when the change is on the way; say what is still missing.
   - **Within the scope?** The scope is an MVP, not the platform. Work beyond that is flagged, not hidden.
   - **Flag, do not hide.** If the change steps outside a constraint or the scope, or works against the use case, stop and tell the user before committing, and say so in the commit message. If a constraint or a decision is what should change, propose a new decision record rather than a quiet exception.
   - **Record it.** End the commit message with a `Constraints:` line that names the IDs the change serves and anything it flags.
4. Commit at each significant, tested milestone, on a feature branch. Merge to `main` only when asked.

## Design

- Deep modules, narrow interfaces (Ousterhout). Hide complexity behind small APIs.
- Inject dependencies at the edges: the index store and the readers are passed in, not imported where used. `runtime.py` wires them.
- Readers live in `engineering_search/indexing/readers/` and are registered in one place (the registry factory). Several versions of a reader for one format are allowed; the registry selects one.
- Indexing and searching are separate lines that meet only at the store.
- Permissions apply before limits, ranking, counts, joins and aggregates.

## Decision records

- `docs/constraints/` and `docs/adr/` are written by hand, and every item and decision traces to the brief. A decision links the IDs it serves and the files that implement and test it. A change that conflicts with an accepted decision needs a new decision record, not a quiet edit.
- The brief says connectors that extract metadata, text and properties already exist. The MVP's readers and extractors are sample stand-ins that show the flow; do not grow them into products.

## Docs

`docs/CODEX_ENGINEERING_SEARCH_HANDOFF.md` and `docs/engineering_knowledge_search_design_notes.html` are dated design inputs (29 October 2026). Do not edit them; record decisions in the ADRs and the main docs.
