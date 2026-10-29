---
status: superseded in part by 0017 (binding and the unverified status)
date: 2026-10-28
---
# Give no answer, or a partial answer, before a wrong answer

> **Superseded in part** by [ADR 0017](0017-bind-answers-and-permit-before-the-limit.md): the question words are bound to the sentence, its heading, the file path or the title, not checked against the whole document, and a new status, `unverified`, marks an unbound value. The principle stands.

**Serves:** U4 (100% confidence in the source), R2 (an answer, not passages), R1 (no information from forbidden documents), U1 (load limit, material or approval status).

## Context

The user asks for one parameter (U1) and must trust the source 100% (U4). The user also asked for an answer, not a list of passages (R2). Word search always finds something: a question about a project that does not exist still matches "roof" and "load" in other projects. If the service always gives its best match as the answer, a user can get the load limit of the wrong project, with a correct-looking source. That is worse than no answer. Two documents can also state different values for the same parameter, for example a draft and an approved revision.

## Decision

- Each answer has a status:
  - `found`: one sentence or table row states a value, and its document contains every question word.
  - `partial`: the closest sentence states a value, but its document does not contain some question words. `missing_words` names them. The user sees which words were not found, for example the project name.
  - `not_found`: no sentence states a value that matches enough question words (`MIN_COVERAGE`, 50%). The service gives no answer.
- Check the question words against the whole document text, not only the passage. A project name is often in the title, not in the sentence with the value.
- Copy the answer exactly from the document. Never write, round or convert the answer text.
- Show other readable files that also state a value as "also stated in", so the user sees conflicts (at most `MAX_ALSO_STATED`, 5).
- Use only readable files for each of these steps (R1, [ADR 0006](0006-permissions-before-results.md)).

## Consequences

- The service can say "not found" when a person would find the value in a table or a drawing that the readers cannot read. A correct "not found" is better than a wrong answer.
- `partial` is a word check, not an understanding of the question. It does not know that the value belongs to the asked element. [ADR 0014](0014-defer-facts-store-and-embeddings.md) records the facts store that would know this.
- The test questions include a question with no answer, and the acceptance tests check that the service gives none.

## Implementation

Done for the known case. `pick_answer()` in [`answer.py`](../../engineering_search/answer.py) checks that the cited sentence is bound to the question words: through the sentence, its heading, the file path or the document title. If the document has every word but the sentence does not name some of them, the status is `unverified`, with `unbound_words`. "Roof load is not specified. Floor load limit is 5 kN/m²." no longer answers "What is the roof load?" as `found`. The web page and the MCP server show the status and the missing or unbound words. Tests: `tests/test_binding.py`, `test_no_answer_is_given_when_no_document_states_it` and `test_one_value_is_answered_from_its_exact_source` in `tests/test_use_case.py`, and the `answer_correct` metric of `scripts/evaluate.py`.

Limits: binding is a word check. A sentence that names the subject can still state a different parameter. The document-title rule is a heuristic: the first passage counts as the title only if it starts in the first three lines.
