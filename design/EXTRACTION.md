# Extraction and stores: from questions to properties

The questions that users ask decide what the system must extract from the files, and how it must store the result. This document starts from the questions in the brief and works back to the extraction methods and the stores.

The files in the repository decide what the system can extract. [DATA-PROFILE.md](DATA-PROFILE.md) tells you how to profile the real repository first: formats, versions, structure and where the parameters are. That profile selects the readers, and it also affects the viewer that users need to see a source in its context.

The brief gives the constraints:

- The files are in an existing repository.
- Connectors and APIs can extract metadata, text and properties from supported files.
- Extracted information can go into structured stores, semantic stores, or both.
- A chat-agent shell can call backend APIs and tools.

The use case: an engineering lead finds a load limit, a material specification or a compliance approval status across 100+ documents, in less than 10 seconds, with 100% confidence in the source, and does not open a CAD file or a PDF viewer.

## 1. The questions

| # | Kind of question | Example | What the answer needs |
| --- | --- | --- | --- |
| Q1 | One value | "What is the roof load limit at Northgate?" | The value, its unit, and the exact source |
| Q2 | One status | "Has building control approved the Northgate warehouse?" | The status word, the authority or reference, and the source |
| Q3 | Documents by project or folder | "Do we have any documents in Northgate?" | The project of each document |
| Q4 | Documents by topic | "Of those, which mention compliance?" | Words or concepts in the text, and the previous list |
| Q5 | Documents by property | "Which documents specify S355?" "Which have a compliance approval status?" | Each document's material grades or statuses |
| Q6 | Documents by number | "Which documents have a roof load greater than 5 kN/m²?" | A number, a unit, and the thing that the number applies to |
| Q7 | Conflicts and currency | "Is the 7 kN/m² roof load approved?" | The status and revision of each value, and which document supersedes which |
| Q8 | Different words, same meaning | "bearing capacity" for "allowable bearing pressure" | Synonyms or meaning, not only the same words |

## 2. Three levels of extracted information

### 2.1 File metadata

**What:** path, project, discipline, document number, revision, date, author, format and format version, repository status (for example "issued for construction"), and the access control list.

**How:**

- Use the repository connector or API first. Most document systems already store project, revision and status as fields.
- Use file-naming rules where the repository has no field, for example `NDW-CALC-001-RevB.pdf`.
- Use the PDF document information (title, author, dates) and Markdown front matter.

**Store:** a structured store, one row per file version: `documents(file_id, version, project, discipline, doc_number, revision, status, date, acl, …)`.

**Answers:** Q3 directly, with an exact filter. Also the "project" and "revision" parts of Q1, Q5, Q6 and Q7.

### 2.2 Text with locations

**What:** passages of text, each with its file version, page, line range, heading path and, for tables, the row and column.

**How:** one reader for each format and format version.

- Markdown: split at headings and blank lines (implemented).
- PDF with a text layer: page by page, with numbered headings (implemented, with pypdf).
- PDF tables: a layout-aware reader that keeps rows and columns (later).
- Scanned PDF: OCR, with a confidence value for each word (later, outside the MVP).
- CAD files: text, title blocks and annotations through the connectors (later, outside the MVP).

**Store:**

- An inverted index for words (SQLite FTS5 now, OpenSearch or Elasticsearch at larger scale).
- A semantic store (vector index) for meaning (later).

Both stores point to the same passage records, so each result keeps its source.

**Answers:** Q4 and Q8 directly. Also the source text for all other questions.

### 2.3 Engineering properties (facts)

**What:** typed records with these fields:

| Field | Example |
| --- | --- |
| `parameter` | `roof_imposed_load` (from a controlled list) |
| `subject` | "Roof (no access)", "Portal frames", "Main girders" |
| `value`, `unit` | 0.6, kN/m² |
| `value_si` | 600 (N/m²), for comparisons |
| `condition` | "Category H", "static, dry" |
| `status` | approved, pending, rejected, draft |
| `project`, `revision` | from the file metadata |
| `source` | file version, page, lines, and the exact text span |
| `method`, `reader_version`, `confidence` | how the record was made |

**How:** use the cheapest method that is correct, in this order.

1. **Structured sources.** CAD block attributes and title blocks, BIM or IFC property sets, PLM fields and spreadsheets already contain named properties. The brief says that connectors can extract these properties. Map them to the parameter list. This needs no language processing.
2. **Pattern rules.** Regular expressions find quantities with units, material grades (EN 10025 S-grades, concrete classes such as C30/37, ASTM or AASHTO grades) and status words. Table headers ("Parameter | Value | Approval status") tell which column holds what. The MVP already uses these rules at query time (see section 4).
3. **A small parameter dictionary.** Start with the 20 to 30 parameters that leads ask about. Give each one an ID, its usual names, and its allowed units. For example, `roof_imposed_load` has the names "roof load", "imposed roof load" and "roof live load", and the units kN/m², kPa and psf. This is the start of an ontology, not a full ontology.
4. **Language model extraction.** For text that the rules cannot read, a language model reads one passage and fills the record. The service keeps the record only if the value and the subject are exact spans of the passage. If they are not, it rejects the record. Records with low confidence go to a human review queue.

Each fact keeps its exact source span and the file version. Thus a fact gives the same confidence in the source as a quoted passage.

**Store:** a structured store, for example `facts(parameter, subject, value_si, unit, status, project, revision, file_id, version, page, start_line, end_line, span, method, confidence)`, with indexes on `(parameter, value_si)`, `(project)` and `(status)`. SQLite is sufficient for one site. PostgreSQL is better for a shared service.

**Answers:** Q1, Q2, Q5, Q6 and Q7 with exact filters and complete results. For example:

```sql
SELECT file_id, page, span FROM facts
WHERE parameter = 'roof_imposed_load' AND value_si > 5000 AND status <> 'superseded';
```

## 3. Which store answers which question

| Question | Inverted index (words) | Semantic store (meaning) | Structured store (metadata and facts) |
| --- | --- | --- | --- |
| Q1, Q2 one value or status | Finds candidate passages | Finds paraphrases | Gives the value directly, if extracted |
| Q3 documents by project | Finds the name in the text or path | Not needed | Exact filter on `project` |
| Q4 documents by topic | Yes | Yes, for other words with the same meaning | Not needed |
| Q5 documents by property | Finds the code, for example "S355" | Not needed | Exact filter on `parameter` and `value` |
| Q6 documents by number | Cannot compare numbers | Cannot compare numbers | Exact range filter on `value_si` |
| Q7 conflicts and currency | Shows all candidates | Shows all candidates | Uses `status`, `revision` and supersession |
| Q8 different words | Synonym list only | Yes | Parameter dictionary |

The chat agent does not need to know which store answers a question. It calls one tool. The tool selects the stores.

## 4. What the MVP does now

The MVP has the inverted index and the text with locations (2.2). It does not have a facts store. Instead, it applies the pattern rules from 2.3 **at query time**, to the passages that the index finds. The code is in [`engineering_search/answer.py`](../engineering_search/answer.py).

| Question | MVP method |
| --- | --- |
| Q1, Q2 | Split the best passages into sentences and table rows. Keep the parts that state a value. Return the part that has the most question words. Include the next sentence if it has a missing question word |
| Q3, Q4, Q5 | Find the documents that contain every question word (in text, heading or file name). Show the line that best shows why |
| Q4 follow-up | Limit the next question to the files of the previous list (`within`) |
| Q6 | Read the numbers and units in the lines of the matching documents. Convert units (N/m², kN/m², kPa, MPa, psf, ksi and others) and compare |
| Q7 | Show up to five other documents that also state a value, from the 8 best passages. Show the status in the same text when it is there |
| Q8 | A small synonym list only |

The limits of this method:

- It finds only what the word search finds first. A value written with other words is not found.
- It does not know which element a number belongs to. "Mezzanine 7.5 kN/m²" is not a roof load. For Q6, a line must contain one question word, so "floor load 10 kN/m²" qualifies for "roof load greater than 5 kN/m²". For Q1 and Q2, the status `found` checks the question words against the whole document, so a floor load sentence can be the `found` answer to a roof load question. These are known defects ([TODO.md](../TODO.md#known-defects-fix-first)).
- It does not know which document supersedes which. It shows some conflicts, but it does not resolve them.
- The patterns and the unit list are small. Signs are not read: "-2 kN/m²" is compared as 2 kN/m².
- A list returns at most 200 documents.
- The work happens on each query. At a large scale, a facts store is faster and gives complete lists.

The same rules can run at index time to fill the facts store. Thus the MVP code is a first version of extraction method 2, not a separate path.

### Worked example: the role of "Northgate"

Question: "What is the roof load limit at Northgate?"

1. The query planner removes "what", "is", "the" and "at". It keeps four words: `roof`, `load`, `limit` (with its synonyms) and `northgate`. "Northgate" is only a word. The service does not know that it is a project.
2. The inverted index finds passages that contain any of the words. It searches three columns: the passage heading, the passage text, and the words of the file path. Every passage of `project-northgate/northgate-warehouse-structural-calculations.pdf` matches `northgate` through its path.
3. The answer step checks where each word occurs:

| Source | `roof` | `load` | `limit` | `northgate` |
| --- | --- | --- | --- | --- |
| Northgate PDF, page 2: "The roof is designed for an imposed load of 0.6 kN/m²." | sentence | sentence | heading "3.1 Roof load limit" | file path |
| `project-cedar/03-roof-load.md`: "Maximum uniformly distributed roof load: 5 kN/m²." | sentence | sentence | sentence ("maximum") | not found |

The Northgate sentence has all four words in its sentence, heading or file path, so it is the answer. The Cedar sentence has three, so it is shown below the answer as "also stated in".

Thus the MVP gets "Northgate" from the **folder and file name**. That works here because the repository names its folders by project. It fails when:

- a Northgate document has no "Northgate" in its path or in the passage;
- a document only mentions Northgate, for example the material register, which lists one Northgate row among Riverside rows;
- a project has more than one name, for example "Northgate", "NDW" and "Northgate Distribution Warehouse".

The correct design uses the `project` field of the file metadata (2.1), from the repository connector, and a list of project names and codes. Then "at Northgate" becomes the exact filter `project = 'Northgate'`, and the remaining words search only those documents.

## Embeddings

The MVP does not use embeddings. It has no semantic store.

Embeddings help with Q8: different words with the same meaning, for example "bearing capacity" and "allowable bearing pressure". They do not help with these parts of the use case:

- **Numbers and filters.** An embedding does not know that 7 kN/m² is greater than 5 kN/m². Q6 needs the facts store.
- **Exact codes.** "S355" and "S275" have similar embeddings, but they are different materials. Word search and exact filters are better.
- **The source.** A vector search returns passages, the same as word search. The confidence in the source comes from the passage record and the exact text, not from the search method.

They also add cost: a model (local, or an external API), an index build for each model version, and a test that shows the gain.

The recommendation:

1. Do not add embeddings to the MVP.
2. In phase 3, add a vector index of the same passages. Combine the word ranking and the vector ranking (hybrid search, for example reciprocal rank fusion).
3. Keep it only if the test questions show a gain. Add paraphrased questions to the question set first.
4. Use embeddings to find candidate passages and to map phrases to parameters in the dictionary. Do not use them to decide a value.

## 5. How the chat agent uses the stores

The chat agent is the conversational plane. The backend gives it tools, and each tool returns sources.

| Tool | Status | Purpose |
| --- | --- | --- |
| `search_evidence(question, mode, within)` | Implemented (MCP and HTTP) | One value, or a list of documents, with exact sources |
| `read_evidence(file_id, page)` | Implemented (MCP) | Read the text around a source |
| `find_facts(parameter, project, operator, value, status)` | Later | Exact filters on the facts store |
| `list_documents(project, discipline, revision, status)` | Later | Exact filters on file metadata |
| `verify_citations(answer)` | Later | Check that every value in the agent's answer is in a cited source |

The agent writes the reply in plain language. The tools supply the values and the sources. The rule for the agent: quote values exactly, cite the file and page, and say "not found" when a tool finds nothing.

## 6. Phases

| Phase | Extraction | Stores | Questions answered well |
| --- | --- | --- | --- |
| 1 (this MVP) | Markdown and PDF text, query-time pattern rules | Inverted index | Q1, Q2, Q3, Q4, Q5. Q6 partly. Q7 shows conflicts |
| 2 | Repository metadata from the connector. Index-time pattern rules for the three parameter families in the brief. Parameter dictionary version 1 | Add metadata and facts tables | Q6 complete. Q3 with exact project filters. Q7 with revisions |
| 3 | Language model extraction with span checks and a review queue. Layout-aware PDF tables | Add a semantic store | Q8. Values in free text and complex tables |
| 4 | CAD and BIM properties through the connectors. OCR, if the business needs it | Same stores | Values that are only in design files |

Each phase uses the same test questions, and adds new questions for the new capability. A phase is complete when its questions pass. See [`evaluation/`](../evaluation/) and [`tests/test_use_case.py`](../tests/test_use_case.py).

## 7. Risks

- **Scope of the parameter dictionary.** It can grow without limit. Start with the parameters that users ask about, and add more only from real questions.
- **Units and conventions.** Some documents give characteristic values and some give design values. Some use imperial units. The facts store must record the condition and the unit, not only the number.
- **Subject binding.** Many values in a table belong to different elements. Extraction must keep the row and column, or the value is wrong.
- **Revisions.** An old revision can state a different value. Without supersession data, the system must show all values and their revisions, and not select one.
- **Extraction quality.** PDF tables, scans and CAD text lose structure. Measure extraction on real files before you trust a filter on extracted values.
- **Cost.** Language model extraction of a large repository costs money and time. Use it only where rules and structured sources cannot do the work.
