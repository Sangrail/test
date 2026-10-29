# Background (B)

> A company has years of engineering and infrastructure design information stored in design files and related project documents. Users often do not know which files contain the information they need, and they do not want to learn file formats, schema details, query languages, or system-specific jargon.

| ID | Item | Standing |
| --- | --- | --- |
| [B1](#b1) | Years of design information in design files and project documents | context |
| [B2](#b2) | Users do not know which files hold what they need | context |
| [B3](#b3) | Users will not learn file formats or schema details | context |
| [B4](#b4) | Users will not learn query languages or system-specific jargon | context |

<a id="b1"></a>

## B1. Years of design information in design files and project documents

> "years of engineering and infrastructure design information stored in design files and related project documents"

**For the design:** the information is spread over many files of many formats, old and new. Design files (CAD) and documents (PDF, spreadsheets, text) both hold parameters.

**In the MVP:** the [test repository](../../test-repository/TEST-DATA.txt) has 149 files across several projects: Markdown, PDF, CSV, XLSX, a DXF drawing, and JT files and notes that no reader takes, so that the gaps show.

<a id="b2"></a>

## B2. Users do not know which files hold what they need

> "Users often do not know which files contain the information they need"

**For the design:** the user asks a question, not a file. The system finds the file and says which one it was ([U5](use-case.md#u5)).

**In the MVP:** the search covers every file the user may read ([K10](clarifications.md#k10)). The answer names the file it came from.

<a id="b3"></a>

## B3. Users will not learn file formats or schema details

> "they do not want to learn file formats, schema details"

**For the design:** the user never sees a format, a table schema or a column name. The answer is the quoted value and where it is.

**In the MVP:** readers turn every format into passages and tables ([ADR 0001](../adr/0001-prove-the-use-case-with-stand-in-readers.md)). The schema is for the chat agent, never the user ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)).

<a id="b4"></a>

## B4. Users will not learn query languages or system-specific jargon

> "query languages, or system-specific jargon"

**For the design:** questions are in plain language. A SQL statement typed as a question is refused ([K9](clarifications.md#k9)).

**In the MVP:** `POST /search` and the MCP tool `search_evidence` refuse a question that is a SQL statement ([`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py)). The chat agent may write constrained SQL for the user ([ADR 0006](../adr/0006-the-user-never-writes-sql.md)).
