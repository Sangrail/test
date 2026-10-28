---
status: accepted
date: 2026-10-28
---
# Give no answer, or a partial answer, before a wrong answer

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

Partial. `answer()` in [`answer.py`](../../engineering_search/answer.py) takes a `document_text` callable that `SearchService.search` gives it. The web page and the MCP server show the status and the missing words. Tests: `test_no_answer_is_given_when_no_document_states_it` and `test_one_value_is_answered_from_its_exact_source` in `tests/test_use_case.py`, and the `answer_correct` metric of `scripts/evaluate.py`.

The statuses work for the wrong-project case in the context: a Cedar roof load is `partial` for a Northgate question. They do not stop a wrong parameter from the right document. Because the question words are checked against the whole document, a document with "Roof load is not specified. Floor load limit is 5 kN/m²." answers "What is the roof load?" with the floor load and status `found`. This is the wrong answer that this decision exists to prevent. The tests and the evaluation do not include this case. See [TODO.md](../../TODO.md#known-defects-fix-first).
