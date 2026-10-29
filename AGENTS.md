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
- Keep the pages linked, or they become useless. In both folders:
  - Every item ID (B, C, U, T, S, K, G, O and a number) is a link to its own section: `[C3](../constraints/constraints.md#c3)` from an ADR, `[C3](constraints.md#c3)` between item pages, `[K3](#k3)` on its own page. Write a range as two links: `[U2](use-case.md#u2)–[U6](use-case.md#u6)`.
  - A new item gets a row in its page's summary table, an `<a id="…">` anchor and a section. A new ADR gets the next number and a row in `docs/adr/README.md` with its title, its status (`*Proposed:*` in front of the title while proposed) and the items it serves, all of which its **Serves:** line also cites.
  - When you change an item, a decision or a file they name, update every page that links to it in the same commit.
  - `tests/test_doc_links.py` fails on a broken link or anchor anywhere in the documents, a bare item ID, a link to the wrong item, a summary table that differs from its sections, and an ADR index that differs from the records. Fix the pages; never weaken the test to pass.
- The brief says connectors that extract metadata, text and properties already exist. The MVP's readers and extractors are sample stand-ins that show the flow; do not grow them into products.

## Docs

`docs/engineering_knowledge_search_design_notes.html` is a dated design input (29 October 2026). Do not edit it; record decisions in the ADRs and the main docs.
