---
status: accepted (partly implemented)
date: 2026-10-29
version: 1
---

# Evaluate retrieval, natural-language-to-SQL and the agent's reply, and gate releases on the results

Supersedes in part [ADR 0015](0015-acceptance-tests-enforce-the-use-case.md): its measurement part (17 questions, one script) is extended here. Its acceptance tests stay.

**Serves:** [U1](../constraints/use-case.md#u1) (find the parameter), [U4](../constraints/use-case.md#u4) (100% confidence in the source), [U6](../constraints/use-case.md#u6) (plain language), [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [R4](../constraints/requirements.md#r4) (the tests enforce the use case). **Not met:** [P6](../constraints/production.md#p6) (quality measured on real, held-back questions).

## Context

Trust fails quickly when search is wrong. A lead who gets one confident wrong load limit stops using the service. The tests prove that the code does what it was written to do, on the documents it was written for. They do not say how good the answers are, or how good they will be on real documents and real questions.

There are now three places where a question can go wrong:

1. **Retrieval and text answers** (the service). Does the index find the right passage, and does the answer step choose the right sentence, with the right status?
2. **Natural language to SQL** (the chat agent). [ADR 0016](0016-structured-facts-and-client-written-sql.md) gives the structured question to the MCP client's language model. The server makes the SQL safe, not right. A safe query can compare a demand with a capacity, miss S355J2 when asked for S355, read 5 N/m² as 5 kN/m², or drop a project filter. Nothing measured this.
3. **The agent's reply.** The agent reads the tool result and writes its own words. It can drop a row, change a value, or present an `unverified` value as fact. Nothing checks this either.

What existed on 29 October 2026: `scripts/evaluate.py` scores 16 text questions (Success@1 0.88, Success@5 1.00, MRR@10 0.90, Recall@10 0.90, answer correct 1.00, no leaks). The questions, the synonyms and the documents were written together by the same team, so the scores are optimistic ([docs/METRICS.md](../METRICS.md)). The SQL path had tests, not an evaluation.

## Decision

Evaluate each of the three places separately, so a failure points at its cause.

### 1. Retrieval and text answers

Keep `scripts/evaluate.py` and `evaluation/questions.json`, and extend the set by kind:

- **One value**: the answer comes from an expected file and contains the expected text; its status is the expected one (`found`, `unverified`, `partial`).
- **Not stated**: questions whose correct result is `not_found`. A confident answer is a failure.
- **Lists**: precision and recall of the document set, not only the first result.
- **Paraphrases**: the same question in other words, to measure the synonym gap.
- **Permissions**: the same question for each user; leaks must be 0.

Metrics: Success@1 and @5, MRR@10, Recall@10, answer correct, status correct, not-found precision, list precision and recall, zero-result rate, leaks, latency p50 and p95.

### 2. Natural language to SQL

Use **execution accuracy**, not SQL text: many different statements are correct. A question passes when the client's result has exactly the expected rows (as `[subject, file_id]` pairs) or the expected value.

- **The gold set**: [`evaluation/sql_questions.json`](../../evaluation/sql_questions.json), 13 questions with expected rows written by hand from the fixtures. Each names its **trap**: grade family, capacity versus demand, units, sign, project filter, a join through `table_rows`, permissions (Kamal), and "no rows is the right answer". Each has one reference SQL, and [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py) checks that it gives the expected rows, so the gold set cannot drift from the extraction.
- **Metrics**: execution accuracy; row precision and recall (partial credit shows what is missed); pass rate by trap; refused statements (the server's error messages should let the agent correct itself); tool calls and time per question.
- **Repeat each question several times.** A language model does not answer the same way twice. Report pass@1 and the share that pass every time.
- **Pin versions.** Record the client, its version and the model with every result. A model change is a new baseline.
- **Coincidental success.** A wrong query can return the right rows on small data. Use several paraphrases per question and the traps to make that unlikely, and grow the fixtures where a trap is not yet decisive.

### 3. The agent's reply and its choice of tool

- **Fidelity**: every value and row in the reply appears in a tool result; no expected row is missing; `partial` and `unverified` warnings are passed on; no forbidden content. Check these deterministically first (subjects, numbers and file names in the reply against the tool results). Use a language-model judge only as a second opinion, with people checking a sample.
- **Routing**: does the agent use SQL for filter and count questions, and text search for values in prose? A mixed set of questions, scored by which tools were called.

### 4. The harness

- The MCP server writes an opt-in trace (local file, evaluation only) of each tool call: the tool, the arguments (including the SQL), the row keys returned, any error and the time. It never writes passage text.
- A script runs each client (`claude -p`, `codex exec`, `pi -p`) on each question as its user, reads the trace and the final reply, and scores them. Results go to `evaluation/results/` with the date, the client and model versions, and the per-question details.

### 5. Gates and real questions

- **Every commit** (in the test suite): the gold SQL set is valid, the retrieval evaluation runs, leaks are 0, and answer correct stays at 1.00 on the scored set.
- **Before a release, or a model or client change**: the live-client evaluation for each supported client. No release with a permission leak or a fidelity failure; execution accuracy and the retrieval metrics must not fall below the last accepted baseline without a recorded reason.
- **Real questions**: collect questions from engineering leads, with the answers and sources they expect ([design/DATA-PROFILE.md](../../design/DATA-PROFILE.md)). Keep about a third back from the developers. Only scores on the held-back set predict real use.

## Consequences

- Each failure points at its layer: the index, the answer rules, the schema and its descriptions, the client's model, or the reply.
- The live evaluation costs money and time per run, so it runs before releases, not on every commit.
- The scores on synthetic data will stay optimistic until real, held-back questions exist. The documents say so ([docs/METRICS.md](../METRICS.md)).
- Schema descriptions and tool instructions become things to tune against the SQL evaluation, like the synonym list for retrieval.

## Implementation

Partial.

- Done: the retrieval evaluation ([`scripts/evaluate.py`](../../scripts/evaluate.py), 16 scored questions); the NL-to-SQL gold set with its validation test; the load test for the time budget ([ADR 0018](0018-admission-control-and-the-time-budget.md)).
- Gates: only the gold-set check runs in the test suite, and `tests/test_no_leaks.py` asks every evaluation question for each user. The retrieval evaluation is run by hand. There is no CI.
- Not done: the MCP trace, the live-client harness and its first baseline for Claude Code, Codex and Pi; not-found, list and paraphrase questions in the retrieval set; the fidelity and routing checks; real held-back questions. Each is a milestone in [TODO.md](../../TODO.md).

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-29 | now | Recorded when the decision was made. | sangrail |
