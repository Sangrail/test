# Evaluation: what the results mean

This folder holds the test questions and the saved scores of the search service. [docs/METRICS.md](../docs/METRICS.md) gives the full explanation. This page is the short version.

## Contents

| File | Contents |
| --- | --- |
| `questions.json` | 17 questions. Each question names a user and the expected sources: a file and a text that the correct passage must contain |
| `sql_questions.json` | 13 gold questions for the structured path: plain-language questions that a chat agent must turn into SQL, with the expected rows written by hand and the trap that each one tests |
| `results/baseline.json` | First version: exact word match, Markdown only, 18 files |
| `results/fts5.json` | FTS5 inverted index and PDF pages, 18 files |
| `results/answers.json` | Index, answer step and 138 files (28 October 2026). The current scores below (148 files) are not saved yet |

To score the current code, and to save the result (this overwrites the 138-file record):

```bash
uv run --frozen python -m scripts.evaluate --save evaluation/results/answers.json
```

The old results cannot be made again with the current code. They are a record of earlier versions.

The questions score the text path only (`search_evidence`). The structured path (`query_sql`) is checked by tests ([`tests/test_sql.py`](../tests/test_sql.py), [`tests/test_mcp_stdio.py`](../tests/test_mcp_stdio.py)), not by these questions.

## How each part is evaluated

[ADR 0009](../docs/adr/0009-acceptance-tests-and-evaluation-sets.md) gives the plan. A question can go wrong in three places, so each is measured on its own:

| Part | Question | How | State |
| --- | --- | --- | --- |
| Retrieval and text answers (the service) | Does the index find the right passage, and does the answer step choose the right sentence and status? | `scripts/evaluate.py` over `questions.json`: Success@1 and @5, MRR@10, Recall@10, answer correct, leaks, time | Runs. Needs not-found, list, paraphrase and status-scored questions |
| Natural language to SQL (the chat agent) | Does the agent's SQL return exactly the right rows? | Execution accuracy over `sql_questions.json`: the agent's result rows (`[subject, file_id]`) or value must equal the expected ones. Also row precision and recall, pass rate by trap, refused statements, tool calls, time. Each question several times, with the client and model versions recorded | The gold set exists and `tests/test_sql_questions.py` proves each expected answer against the extraction. The live-client harness (MCP trace and a runner for Claude Code, Codex and Pi) is not built |
| The agent's reply and tool choice | Does the reply quote the tool results, keep every row and pass on warnings? Does the agent pick SQL for filters and text search for prose? | Deterministic checks of subjects, numbers and file names in the reply against the traced tool results; a language-model judge only as a second opinion | Not built |
| Time budget | Is every request answered within 8 s, or refused at once? | `scripts/load_test.py`: N simultaneous requests through the real web app | Runs ([ADR 0008](../docs/adr/0008-a-time-budget-and-admission-control.md)) |

Why execution accuracy and not the SQL text: many different statements are correct. Why traps: on small data a wrong query can return the right rows by chance, so each gold question names the mistake that it is built to catch (grade family, capacity versus demand, units, sign, project filter, a join, permissions, and "no rows is the right answer").

## The results

| Metric | Baseline | FTS5 | Answers (138 files) | Now (148 files) |
| --- | ---: | ---: | ---: | ---: |
| Correct answer | (no answers) | (no answers) | 1.00 | 1.00 |
| Success@1 | 0.19 | 0.81 | 0.94 | 0.88 |
| Success@5 | 0.25 | 0.94 | 1.00 | 1.00 |
| MRR@10 | 0.22 | 0.86 | 0.95 | 0.90 |
| Recall@10 | 0.22 | 0.97 | 0.90 | 0.90 |
| Questions with no result | 76% | 0% | 0% | 0% |
| Permission leaks | 0 | 0 | 0 | 0 |
| Median time per question | 4 ms | 12 ms | 16 ms | 79 ms |
| p95 time per question | 4 ms | 54 ms | 68 ms | 330 ms |

"Now" was measured on 29 October 2026 with `uv run --frozen python -m scripts.evaluate`.

## What the results mean

- **The method got better up to 138 files.** The index and the synonyms removed the empty results. The answer step selects the correct sentence or table row for every scored question. This is the most reliable conclusion, because each version was measured on the same questions.
- **The structured data lowered Success@1.** Q01 ("What is the roof load limit?") now has its first correct passage at rank 5. The four rows of the new roof schedule rank above it: each row is a passage whose heading holds the column names "Allowable load" and "Roof imposed load". Q12 has its first correct passage at rank 4.
- **The answer is correct even when the first passage is not.** Q01 and Q12 both get the correct answer. The answer step reads the best 8 passages.
- **The search is slower.** The median went up from 16 ms to 79 ms. This was not profiled. The service now checks permissions on every file that contains a query word before the lookup, and reads every passage of the answer's document to set the status.
- **Lower recall is expected now.** Recall@10 went down from 0.97 to 0.90 when 120 generated files were added. Those files compete for the top 10 places. For example, Q07 ("S355") has 3 expected sources, and 70 files that JP can read contain S355.
- **No permission leak was found.** Kamal got nothing from the files that Kamal cannot read.
- **The search is still fast on this data.** The search itself uses a very small part of the 10-second limit.

**The results do not show the quality on real documents.** The same team wrote the documents, the questions and the code. The documents are synthetic and clean, and 120 of the 148 files come from one template. The structured fixtures were written for one question. Each value is next to its unit, and project names are in the file paths. With only 16 scored questions, 16 of 16 correct still allows a real failure rate of up to about 19%.

## Gaps in the testing

**Gaps in the question set**

1. **No real questions.** The developers wrote all 17 questions. Engineering leads did not write or check any of them.
2. **No held-out questions.** The code was changed while the developers looked at all the questions. There is no set to measure new questions fairly.
3. **Too few questions.** 16 scored questions are not enough for a precise score, or for a score for each format or question type.
4. **Users are unbalanced.** 15 questions are for JP and 2 for Kamal. No question is for Maya.
5. **Question types are missing from the scored set.** It has no list questions ("which documents…"), no number comparisons, no follow-up questions, no question that has no answer, and no structured (SQL) question. The acceptance tests check these, but only with a few examples each.
6. **No difficult wording.** There are no spelling errors, abbreviations, other units (psf, kip), other languages or very short questions.
7. **The expected sources are not complete.** Recall counts only the sources that the developers listed. A correct source that is not listed counts as wrong. A listed source can also be out of date.

**Gaps in what is checked**

8. **"Correct answer" is lenient.** The answer must come from an expected file and contain the expected text. The check does not confirm that the value is the current, approved one, or the authority when documents disagree.
9. **The "unverified", "partial" and "not found" results are not scored.** The scoring script does not measure if the service gives these statuses correctly. A few acceptance tests check them.
10. **The chat agent is not scored.** [`tests/test_mcp_stdio.py`](../tests/test_mcp_stdio.py) runs a real MCP client session over stdio, and `scripts/check_mcp.py` does the same by hand. Claude Code, Codex and Pi were checked by hand on one structured question. The gold SQL set exists, but no harness runs the clients on it yet, so the SQL that a language model writes, and its reply, are not measured. The model can change a value after the tool returns it.
11. **The web page is not tested automatically.** The sign-in screen, the answer panel, the chart and the folder table were checked by eye in a browser.

**Gaps in the conditions**

12. **No real documents.** There are a few small synthetic CSV and XLSX files, one scanned PDF and two synthetic `.jt` files (to test that they are reported). There is no CAD, BIM or Word content, no tables across pages, no title blocks and no real damaged files.
13. **The load test is small.** `scripts/load_test.py` sends up to 1,000 simultaneous requests to one process on 148 files: every answered request finishes within the 8 s budget, and the rest are refused at once ([ADR 0008](../docs/adr/0008-a-time-budget-and-admission-control.md)). One process answers about 10 requests a second. There is no test at the expected data size, with several processes, or with SQL over large projections.
14. **Simple permissions.** Three users and path rules in code. There are no groups, deny rules or permission changes during a search.
15. **The MCP user is not verified.** No test can find this gap, because the server trusts the `--user` flag. [docs/MCP.md](../docs/MCP.md) explains this security hole.

## What to do next

1. Profile the real repository. See [design/DATA-PROFILE.md](../design/DATA-PROFILE.md).
2. Collect 50 to 100 real questions from engineering leads, with the correct answers and sources recorded by engineers. Keep some questions back from the developers.
3. Add list, comparison, follow-up, no-answer and SQL questions to the scored set, for each user.
4. Score the "unverified", "partial" and "not found" results, and check that each value is the current one.
5. Build the live-client harness: an opt-in MCP trace and a runner that asks Claude Code, Codex and Pi each question in `sql_questions.json`, scores execution accuracy and reply fidelity, and saves a baseline with the client and model versions.
6. Measure on a sample of real documents, for each format, at the expected size and load.
