# Know the data first: the repository profile

The MVP works on a small, clean test repository that we made. The real system must work on the company repository, with years of files in many formats. Before the team selects readers, extractors, stores or indexes, it must know what that repository holds. This document tells you why, what to measure, and how the result controls the design.

## 1. Why the profile comes first

Each stage of the system depends on the stage before it:

```mermaid
flowchart LR
    Profile[Repository profile<br/>formats, versions,<br/>structure, quality] --> Readers[Readers<br/>one for each format<br/>and version]
    Readers --> Parse[Parse and extract<br/>metadata, text with<br/>locations, properties]
    Parse --> Structured[(Structured stores<br/>metadata, facts)]
    Parse --> Unstructured[(Unstructured stores<br/>keyword index,<br/>embeddings)]
    Structured --> Answer[Answers with<br/>exact sources]
    Unstructured --> Answer
    Answer --> Viewer[Viewer<br/>open the source at<br/>the cited location]
    Profile --> Viewer
```

- **A reader can only read the formats and versions that it supports.** A DWG file from 2004 and a DWG file from 2024 can need different software. A PDF can have a text layer, or it can be a scanned image that needs OCR. The file extension does not tell you this.
- **The extractors can only extract what the files contain.** If a load limit is in a CAD title block attribute, a text extractor does not find it. If it is in a scanned calculation sheet, only OCR finds it.
- **The stores can only answer questions about what the extractors put into them.** A structured store answers "all documents with S355" exactly only if each material was extracted as a property. A keyword index only finds the words.
- **Thus the profile defines the readers, the readers define what can be extracted, and the extracted data defines which questions can be answered.**

If the team skips the profile, it can build good software for formats that are rare, and have no reader for the formats that hold most of the answers.

## 2. What to measure

Run an inventory over the whole repository, or over a large random sample. Use the file content to identify each format, not the file extension.

| Area | What to measure | Why it matters |
| --- | --- | --- |
| Formats | Count and total size for each format: PDF, DWG, DXF, DGN, RVT, IFC, JT, CATIA, STEP, Word, Excel, email, images | Which readers are needed first |
| Format versions | The version of each file, for example the DWG version or the PDF version | One format can need more than one reader. Old versions can have no supported reader |
| PDF type | Text layer, scanned image, mixed, forms, encrypted, password-protected | Scanned pages need OCR. Encrypted files need keys or a policy |
| Structure | Title blocks, schedules, tables, attributes, layers, sheets, bookmarks, headings | Where the parameters are, and how to give an exact location |
| Parameters | Where load limits, materials and approval statuses appear: text, table, attribute, title block, separate register | Which extraction method each parameter family needs |
| Units and notation | kN/m², kPa, psf, kip; S355, ASTM A992; decimal commas | Unit conversion and the parameter dictionary |
| Projects and metadata | Project codes and names, discipline, revision, status, author, dates; where each one is kept (path, file properties, title block, document system) | Metadata filters such as "at Northgate" |
| Revisions and copies | Revisions of the same document, superseded files, duplicates, near-duplicates | Which value is current. Which source is the authority |
| References | External references (xrefs), linked files, missing links | A drawing can depend on other files to be complete |
| Age and quality | File dates, damaged files, empty files, very large files | Coverage, failed files and indexing time |
| Languages | The languages of the text | Tokenizer, stemming, synonyms |
| Permissions | How access is set: folders, groups, document system roles, exceptions | How to copy the access rules to the search, exactly |
| Change rate | Files added, changed and deleted each day | Indexing capacity and how fresh the index must be |

Record the results in a table that the team can repeat. Run the inventory again after a change in the repository.

## 3. From the profile to the readers

For each format and version that holds a significant part of the answers, the team must select a reader. A reader is the software that opens the file and gives its content to the system. The brief says that connectors and APIs already exist for supported files. The profile tells the team which formats they support, which formats they do not support, and how much of the repository is in each group.

For each reader, record:

- the formats and versions that it reads, and its tested limits;
- what it gives: metadata, text with locations, properties, geometry, images;
- how it gives a location: page and box for PDF, sheet or layout and entity handle for CAD, cell for a spreadsheet;
- its licence, its cost and where it can run (server, desktop only, cloud);
- its speed on the largest files.

[ADR 0003](../docs/adr/0003-versioned-reader-selection.md) records the rule: detect the format and version of each file, select a tested reader, and record the reader and its version with each extracted item.

## 4. Structured and unstructured downstream systems

The same reader output must feed two kinds of downstream systems.

| Downstream system | What it needs from the reader | Questions it answers |
| --- | --- | --- |
| Structured stores: metadata and facts | Exact properties with types: project, revision, status; parameter, value, unit, element; each with its source location | "All documents with S355", "roof loads above 5 kN/m²", "approval status of Northgate" |
| Unstructured stores: keyword index and embeddings | Text in reading order, divided into passages, each with its location | Questions in plain language, paraphrases, topics with no fixed property |

Both stores must keep the same location for the same information. Then the system can show one source, and the user can check it. [EXTRACTION.md](EXTRACTION.md) gives the map from question types to extraction methods and stores.

There is no single design that suits all repositories. A repository of mostly scanned calculation sheets needs OCR and table extraction first. A repository of mostly CAD drawings needs title block and attribute extraction first. A repository of mostly reports needs good text and table extraction from PDF and Word. The profile tells the team which case it has.

## 5. Users will want to see the document

The brief asks for an answer without opening a CAD file or a PDF viewer. That is correct for the first step: find the value. But after a lead finds a value, the lead often wants to see it in its context. For example:

- the full table or the calculation around the value;
- the drawing, with the element that the value applies to;
- the revision block, the signature or the approval stamp.

Thus the real system will probably need a viewer, or a link into an existing viewer. This has consequences for the design:

1. **The viewer must read the same formats as the readers.** Often the same software (the same SDK or vendor library) can extract the content and show it. Select readers and viewers together, from the same profile.
2. **The location must work in the viewer.** A source location such as "page 4, lines 6 to 8" is enough for the MVP. A viewer needs a location that it understands: a page and a box for PDF, a sheet or layout and an entity handle for CAD, a cell for a spreadsheet. The readers must record that location at index time.
3. **The viewer must show the same version.** The answer cites a file version (SHA-256). The viewer must open that version, not a newer one, or show that a newer one exists.
4. **The viewer must apply the same permissions.** A user who cannot read a file must not be able to open it in the viewer.
5. **The viewer can run in the browser or on a server.** A browser viewer for PDF is simple. A viewer for DWG, JT or CATIA can need a server that changes the drawing into a web format. That is a cost and a licence question.

The MVP shows the exact text and its location, and it has no viewer. That meets the brief for Markdown and text PDF. For the real system, plan the viewer with the readers.

## 6. Steps

1. Run the inventory (section 2) on the real repository, or on a large random sample.
2. Find where the three parameter families are: load limits, material specifications and approval statuses. Do this with engineers, on a sample of real documents.
3. Collect real questions and the answers that the users need. See [docs/METRICS.md](../docs/METRICS.md) section 5.
4. Rank the formats by the share of answers that they hold, not by the number of files.
5. Select and test a reader, and a viewer, for each format at the top of the list.
6. Design the structured and unstructured stores for those questions. See [EXTRACTION.md](EXTRACTION.md).
7. Measure on the real questions. Then repeat for the next formats.
