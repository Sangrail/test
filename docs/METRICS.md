# Metrics on the test data

This document gives the scores of the MVP on `test-repository/`. [evaluation/README.md](../evaluation/README.md) is a short version, with a list of the gaps in the testing. It also tells you why the scores are high, and why they do not predict the scores on real company documents.

**Summary.** On the test data, the service finds the correct answer for every scored question, gives no information from forbidden files, and answers in about 16 ms. These results show that the parts of the MVP work together correctly. They do not show that the method will work on the real repository. The same team made the documents, the questions and the code, and the documents are clean and small.

## 1. What is measured

Two sets of checks measure the service. Both run against `test-repository/` (138 files: 133 Markdown and 5 PDF, 2,511 passages).

### Scored questions

[`evaluation/questions.json`](../evaluation/questions.json) has 17 questions. Each question names a user and the expected sources: a file (or a file pattern) and a text that the correct passage must contain. 16 questions have expected sources. Question Q17 has none. It checks only that Kamal gets nothing from a forbidden file.

Run the scoring script:

```bash
uv run --frozen python -m scripts.evaluate
```

The script asks each question through `POST /search`, looks at the top 10 passages and at the answer, and calculates these metrics:

| Metric | Definition | Result |
| --- | --- | ---: |
| Correct answer | The answer (one sentence or table row) comes from an expected file and contains the expected text | 1.00 (16 of 16) |
| Success@1 | The first passage is relevant | 0.94 (15 of 16) |
| Success@5 | A relevant passage is in the first five | 1.00 |
| MRR@10 | The mean of 1 / rank of the first relevant passage | 0.95 |
| Recall@10 | The share of expected sources found in the top 10 | 0.90 |
| Questions with no result | The share of questions with no passage | 0.00 |
| Permission leaks | Passages or answers from a file that the user must not see | 0 |
| Time per question | In-process, on one laptop, p50 and p95 | about 16 ms and 68 ms |

A passage is "relevant" when its file matches an expected file and its text contains the expected text (case is ignored).

### Acceptance tests

The automated tests ([`tests/`](../tests/), 69 tests) enforce the use case. They fail if:

- the repository has 100 documents or fewer;
- one of 9 value questions gets the wrong value, file or page;
- the answer text is not in the file at the cited lines, or the cited version is not the SHA-256 of the file (the tests read the file without the service code);
- a request takes 10 seconds or more;
- a document list or a number comparison is wrong;
- the service gives an answer when no document states it;
- any user gets a file name, text or count from a file that the user cannot read ([`tests/test_no_leaks.py`](../tests/test_no_leaks.py) asks every question, and questions made from each forbidden file, in each mode and on each page).

### History

| Metric | Exact match, Markdown only (18 files) | FTS5 index and PDF (18 files) | With answers (138 files, now) |
| --- | ---: | ---: | ---: |
| Correct answer | (no answers) | (no answers) | 1.00 |
| Success@1 | 0.19 | 0.81 | 0.94 |
| MRR@10 | 0.22 | 0.86 | 0.95 |
| Recall@10 | 0.22 | 0.97 | 0.90 |
| Questions with no result | 76% | 0% | 0% |
| Permission leaks | 0 | 0 | 0 |
| Median time per question | 4 ms | 12 ms | 16 ms |

The saved results are in [`evaluation/results/`](../evaluation/results/). The history is the most useful part of this table. It shows that each change to the method made the scores better on the same questions.

Recall@10 went down from 0.97 to 0.90 when the 120 generated files were added. Those files compete for the top 10 places. For example, the question "S355" (Q07) has three expected sources, and more than 60 generated files also contain S355.

The one Success@1 miss is Q12, "service bridge live load limit". The first relevant passage is at rank 4. The answer is still correct, because the answer step reads the best 8 passages, not only the first one.

## 2. Why the scores are high

The scores are high because the test data is easy for this method. Each reason below makes the result better than the result on real documents.

1. **The same team wrote the documents, the questions and the code.** The questions use the words that the documents use. When a question failed, the code or the synonym list was changed until it passed. Thus the method is fitted to these 17 questions. There is no held-out question set that the developers did not see.
2. **The synonym list was made for these questions.** It has five groups of words, for example "limit", "maximum" and "allowable". Real users use many more words, abbreviations and local terms.
3. **The documents are synthetic and clean.** The Markdown files have clear headings and simple tables. The synthetic PDFs come from a script. They have a clean text layer, numbered headings and one value in each sentence. There are no scanned pages, no rotated text, no tables across pages, no title blocks and no handwritten notes.
4. **120 of the 138 files come from one template.** Each generated project file has the same 13 lines with different numbers. If the method works on one of them, it works on all of them. Thus the list counts (for example 53 documents above 5 kN/m²) test one document structure 120 times.
5. **Each value is next to its unit and its subject.** For example "Maximum roof load | 7 kN/m²". The answer rules look for exactly this pattern. Real documents often put the value in one table cell and the subject in a header two rows above, or on another page.
6. **Project names are in the folder and file names.** The service indexes the words of the file path. Thus "Northgate" matches the Northgate file. In a real repository, a project can have a code, a client name and a site name, and the folder name may use none of them.
7. **There are few conflicts.** The test data has a small number of deliberate conflicts, for example a draft and an approved specification. Real repositories have many revisions of the same document, superseded values and copies.
8. **The expected answers were widened once.** When the 120 generated files were added, three questions (Q07, Q09, Q13) got more correct sources. Their expected sources were changed to include them. This was correct, but it also shows that the expected answers follow the data.
9. **The metric is lenient.** An answer is "correct" when it comes from an expected file and contains the expected text. The metric does not check that the value is the current, approved or authoritative one. It does not check the language model reply in a chat agent.
10. **The repository is small.** 138 files and 2,511 passages fit in memory. Most passages (2,116) come from the two public FHWA PDFs. The time per question is measured on one laptop, in one process, with a warm cache, with no network and with no language model.
11. **The permissions are simple.** Three users, path rules in code, no groups, no deny rules, no sharing links and no permission changes during a search.

## 3. Limits of these metrics

| Limit | Effect |
| --- | --- |
| 16 scored questions | Each question is about 6% of a score. A score of 16 of 16 still allows a real failure rate of up to about 19% (95% confidence, "rule of three": 3 / 16). The scores are not precise |
| No real questions | The questions were written by the developers, not by engineering leads. Real questions are shorter, less exact and use local words |
| No real documents | Format, structure, age, quality and size are not those of the company repository |
| No held-out set | The method was changed while the developers looked at the questions. Scores on new questions will be lower |
| No scale test | 16 ms on 138 files does not predict the time on 100,000 files, or with many users at the same time |
| Only Markdown and text PDF | No CAD, BIM, Office, spreadsheet or scanned files. These formats are most of a real engineering repository |
| Correct source, not correct value | The metric does not know if a value is current, approved or replaced by a later revision |
| No chat agent in the loop | The language model can change or shorten the answer. The metric checks only the tool result |
| Simple permissions | Real permissions have groups, inheritance breaks, deny rules and changes over time |
| No user study | The metrics do not show if a lead trusts the answer, or finds it in under 10 seconds end to end |

## 4. What the metrics do show

- The parts of the MVP work together: plain-language question, index, permissions, answer, audit and source.
- Each answer can be checked against the file, with its page, lines and SHA-256 version.
- No user gets information from a file that the user cannot read, for all questions in the tests.
- The scores went up with each change. The same scripts can measure the next change.
- The service answers in milliseconds on a small repository. The search itself does not use most of the 10-second time limit.

## 5. What to measure next

1. **Profile the real repository** first. See [design/DATA-PROFILE.md](../design/DATA-PROFILE.md).
2. **Collect 50 to 100 real questions** from engineering leads, in their own words. Ask engineers to record the correct answer and its source for each question.
3. **Keep a held-out set.** The developers must not see some of the questions until the final measurement.
4. **Sample real documents** from each format, age and project type. Measure the scores for each group, not only the total.
5. **Add stricter metrics:** the value is the current approved one, the reply of the chat agent quotes the tool result correctly, and "not found" is correct when no document states the value.
6. **Measure at the expected size and load,** and measure the time from the question to the reply in the chat agent.
7. **Give a confidence interval** with each score.
