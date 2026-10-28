# Evaluation: what the results mean

This folder holds the test questions and the saved scores of the search service. [docs/METRICS.md](../docs/METRICS.md) gives the full explanation. This page is the short version.

## Contents

| File | Contents |
| --- | --- |
| `questions.json` | 17 questions. Each question names a user and the expected sources: a file and a text that the correct passage must contain |
| `results/baseline.json` | First version: exact word match, Markdown only, 18 files |
| `results/fts5.json` | FTS5 inverted index and PDF pages, 18 files |
| `results/answers.json` | Current version: index, answer step and 138 files |

To score the current code, and to save the result:

```bash
uv run --frozen python -m scripts.evaluate --save evaluation/results/answers.json
```

The old results cannot be made again with the current code. They are a record of earlier versions.

## The results

| Metric | Baseline | FTS5 | Now |
| --- | ---: | ---: | ---: |
| Correct answer | (no answers) | (no answers) | 1.00 |
| Success@1 | 0.19 | 0.81 | 0.94 |
| MRR@10 | 0.22 | 0.86 | 0.95 |
| Recall@10 | 0.22 | 0.97 | 0.90 |
| Questions with no result | 76% | 0% | 0% |
| Permission leaks | 0 | 0 | 0 |
| Median time per question | 4 ms | 12 ms | 16 ms |

## What the results mean

- **The method got better at each step.** The index and the synonyms removed the empty results. The answer step selects the correct sentence or table row for every scored question. This is the most reliable conclusion, because each version was measured on the same questions.
- **The answer is correct even when the first passage is not.** Question Q12 has its first correct passage at rank 4, but its answer is correct. The answer step reads the best 8 passages.
- **Lower recall is expected now.** Recall@10 went down from 0.97 to 0.90 when 120 generated files were added. Those files compete for the top 10 places. For example, Q07 ("S355") has 3 expected sources, and 66 files contain S355.
- **No permission leak was found.** Kamal got nothing from the files that Kamal cannot read.
- **The search is fast on this data.** The search itself uses a very small part of the 10-second limit.

**The results do not show the quality on real documents.** The same team wrote the documents, the questions and the code. The documents are synthetic and clean, and 120 of the 138 files come from one template. Each value is next to its unit, and project names are in the file paths. With only 16 scored questions, 16 of 16 correct still allows a real failure rate of up to about 19%.

## Gaps in the testing

**Gaps in the question set**

1. **No real questions.** The developers wrote all 17 questions. Engineering leads did not write or check any of them.
2. **No held-out questions.** The code was changed while the developers looked at all the questions. There is no set to measure new questions fairly.
3. **Too few questions.** 16 scored questions are not enough for a precise score, or for a score for each format or question type.
4. **Users are unbalanced.** 15 questions are for JP and 2 for Kamal. No question is for Maya.
5. **Question types are missing from the scored set.** It has no list questions ("which documents…"), no number comparisons, no follow-up questions, and no question that has no answer. The acceptance tests check these, but only with a few examples each.
6. **No difficult wording.** There are no spelling errors, abbreviations, other units (psf, kip), other languages or very short questions.
7. **The expected sources are not complete.** Recall counts only the sources that the developers listed. A correct source that is not listed counts as wrong. A listed source can also be out of date.

**Gaps in what is checked**

8. **"Correct answer" is lenient.** The answer must come from an expected file and contain the expected text. The check does not confirm that the value is the current, approved one, or the authority when documents disagree.
9. **The "partial" and "not found" results are not scored.** The scoring script does not measure if the service says "not found" correctly. Only two acceptance tests check this.
10. **The chat agent is not tested.** `scripts/check_mcp.py` checks the MCP server by hand. There is no automated MCP test, and no test of the language model reply. The model can change a value after the tool returns it.
11. **The web page is not tested automatically.** The sign-in screen, the answer panel, the chart and the folder table were checked by eye in a browser.

**Gaps in the conditions**

12. **No real documents.** There are no CAD, BIM, Office, spreadsheet or scanned files. There are no tables across pages, title blocks or damaged files.
13. **No scale or load test.** The times come from one laptop, one user, one process and 138 files. There is no test at the expected size, and no test with many users at the same time.
14. **Simple permissions.** Three users and path rules in code. There are no groups, deny rules or permission changes during a search.
15. **The MCP user is not verified.** No test can find this gap, because the server trusts the `--user` flag. [docs/MCP.md](../docs/MCP.md) explains this security hole.

## What to do next

1. Profile the real repository. See [design/DATA-PROFILE.md](../design/DATA-PROFILE.md).
2. Collect 50 to 100 real questions from engineering leads, with the correct answers and sources recorded by engineers. Keep some questions back from the developers.
3. Add list, comparison, follow-up and no-answer questions to the scored set, for each user.
4. Score the "not found" and "partial" results, and check that each value is the current one.
5. Add an automated MCP test, and a check that the chat agent reply quotes the tool result correctly.
6. Measure on a sample of real documents, for each format, at the expected size and load.
