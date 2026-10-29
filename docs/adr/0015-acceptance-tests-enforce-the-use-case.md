---
status: superseded in part by 0019 (evaluation); the acceptance tests stand
date: 2026-10-28
---
# Enforce the use case with acceptance tests on a public test repository

> **Superseded in part** by [ADR 0019](0019-evaluate-retrieval-and-nl-to-sql.md): evaluation now covers retrieval, natural language to SQL and the agent's reply. The acceptance tests stand; the test repository now has 148 files.

**Serves:** R4 (tests enforce the use case), U1–U5, R1 (no information from forbidden documents), S3 (public or synthetic test data).

## Context

The use case must be enforced by tests (R4), not only described. The repository will be published, so the test data must be public or synthetic (S3). Real engineering documents cannot be used. The tests need more than 100 documents (U2), questions with known answers and sources (U1, U4), and documents that some users cannot read (R1).

## Decision

- Keep a test repository in `test-repository/` with 138 files: 133 Markdown and 5 PDF.
  - 120 generated project files in `generated-projects/`, so the count is above 100 (U2).
  - Hand-written projects (Northgate, Riverside, Cedar), registers and specifications, with known values, conflicts, drafts and approvals.
  - Two public FHWA steel bridge handbook PDFs. `SOURCES.txt` records where they come from.
- Write one acceptance test for each part of the use case in `tests/test_use_case.py`:
  - more than 100 documents (U2);
  - one value from its exact file, page, lines and version, checked against the file (U1, U4, U5);
  - no answer when no document states it ([ADR 0013](0013-no-answer-before-a-wrong-answer.md));
  - list questions, material, approval status, load comparison and a follow-up (R3);
  - each answer within the 10-second limit (U3);
  - no answer from a file the user cannot read (R1).
- Test R1 more strongly in `tests/test_no_leaks.py`: every question, plus questions made from the text of each forbidden file, in each mode, on the first five result pages of 50 passages, for each user.
- Measure ranking and answers with `scripts/evaluate.py` on 17 questions, 16 of them scored (`evaluation/questions.json`). Save the results in `evaluation/results/answers.json`.

## Consequences

- A change that breaks the use case on these examples fails a test. The tests do not cover every failure: they pass with the defects listed in [TODO.md](../../TODO.md#known-defects-fix-first), for example a wrong parameter marked `found`, and lost results when forbidden passages fill the retrieval limit.
- The test data was made with the questions and the synonyms. The scores are higher than on a real repository. [docs/METRICS.md](../METRICS.md) and [evaluation/README.md](../../evaluation/README.md) explain the limits and the gaps in the tests.
- The tests prove the behaviour on this repository, not on the company's repository. A real question set, made from real users and real documents, is the next step ([ADR 0014](0014-defer-facts-store-and-embeddings.md)).

## Implementation

Done. Run `uv run --frozen pytest -q` and `uv run --frozen python -m scripts.evaluate`. The current figures are in [docs/METRICS.md](../METRICS.md).
