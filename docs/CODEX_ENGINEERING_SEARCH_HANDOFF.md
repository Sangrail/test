# Codex implementation brief: evolve Sangrail/test into a version-aware, permission-safe engineering knowledge search system

**Target repository:** https://github.com/Sangrail/test  
**Prepared:** 29 October 2026  
**Intended environment:** macOS development, Python, `uv`, SQLite, local filesystem, simulated authentication and permissions  
**Working approach:** Incrementally evolve the *existing repository*. Audit and test before changing code. This document is an engineering brief, not a claim that any requested feature is already implemented.

> **Initial instruction for Codex:** Read this entire document, then inspect the local working tree, repository-specific instructions and tests. Establish the actual baseline before implementing. Where the local repository differs from the public documentation cited here, trust the local code and explain the difference. Do not generate a new application alongside the existing one. Do not replace working modules without a measured reason. Make changes in small, independently testable increments, and document the results.

## 1. Objective and product boundary

Build a proof of concept that searches a *project-organised filesystem* containing engineering files. The existing file tree remains the source of truth; the search index is a derived, rebuildable artefact. Users access a web UI or use an AI assistant through a local MCP server. For now, **authentication and authorisation remain simulated on macOS**, but all entry points must use the same authorisation interface so that a Windows/AD/NTFS implementation can replace it later.

The distinctive requirement is **question-driven extraction**: the indexer produces both unstructured content (text/passages suitable for FTS5/BM25 and eventually vectors) and structured engineering data (tables, rows, typed properties, quantities, units, project identities, revision/compliance assertions). Both representations retain stable references to the *same underlying document version and evidence location*.

The **MCP client/host's LLM is the natural-language query planner**. It discovers available tables and semantic conventions, then calls restricted MCP tools for structured SQL, keyword search and source evidence. Do not add another hosted LLM to the server or require an API key to run the POC. The web UI can retain deterministic search and, if desired later, receive client-generated query plans through a separately authenticated API. Do not pretend that a normal web search box has LLM planning until it actually does.

### Expected user questions

- Which project documents reference specification `ST-204`?
- Which drawings mention S355 structural steel, and which *components actually specify* it?
- Which components have an **allowable uniformly distributed load below 5 kN/m²**? Link each value to its component, source row/page and parent file.
- Which projects are awaiting compliance approval? Which supporting documents explicitly establish that status?
- Find reports discussing corrosion and fatigue in marine structures, regardless of exact wording (lexical baseline; optional semantic phase after evaluation).
- Find the latest non-superseded approved revision of a particular calculation or drawing.
- Show all files that could not be parsed, by format, version, reason and reader capability. Which projects have the greatest extraction gaps?
- A user with limited folder access asks the same question: return only results and aggregates about files that user may read.

### Non-goals for the first incremental delivery

- Production SSO, Kerberos/NTLM impersonation, NTFS ACL evaluation or enterprise user management.
- Full semantic vector infrastructure unless a measured evaluation establishes the need; preserve SQLite FTS5 first.
- Full interpretation of proprietary JT, DWG, DGN, CATIA or NX geometry without an installed, licensed, **verified** reader.
- Claims of engineering or compliance certification. A source citation establishes provenance, not truth or correctness.
- A new distributed platform, graph database, or unneeded orchestration framework.

## 2. Existing repository: start by preserving what already works

Public documentation at 29 October 2026 describes:

- Python package `engineering_search/`, with `core.py`, `store.py`, `query.py`, `answer.py`, `service.py`, `access.py`, `app.py`, `mcp_server.py`, `runtime.py`, `jobs.py`, `adapters.py` and static UI.
- SQLite FTS5 for text passages and document records; file SHA-256, page/line evidence; existing local index state; `search_evidence` and `read_evidence` MCP tools.
- Simulated identities, file/folder permission rules, audit events, a web UI, and about 138 fixture documents.
- Documentation: `README.md`, `RUNNING.md`, `ARCHITECTURE.md`, `TODO.md`, `design/DATA-PROFILE.md`, `design/EXTRACTION.md`, `design/SYSTEM-DESIGN.md`, `docs/MCP.md`, `docs/adr/`.
- Local commands documented as `uv sync --locked` and `uv run --frozen python -m engineering_search`. Follow `RUNNING.md` and `pyproject.toml` for the **actual** test commands.

These are **public-documentation observations, not a substitute for reading the local source**. The current docs report existing defects. Validate and address them rather than assuming the tests detect them:

1. `found` may cite the wrong engineering parameter (roof versus floor load); the subject and type are not bound to the value.
2. The FTS candidate cap of 1,000 is applied before permission and `within` scope filtering, potentially suppressing permitted results and creating an information side channel.
3. Signed quantities are misparsed, e.g. `-2 kN/m²` as `+2`.
4. Document-list pagination and completeness are limited.
5. A file-level read permission error can abort a whole refresh.
6. Concurrent web and MCP indexing may publish stale state.
7. A PDF with no text layer can be recorded as fully indexed despite having no searchable content.
8. Existing leak tests may not exercise all result pages.

**First deliverable:** create or update a short `docs/IMPLEMENTATION-BASELINE.md` with a table of **feature / actual code location / current test / gap / proposed change / priority**. Run the full suite, record test results and known failures, check `git status`, and use a feature branch. Preserve public API behaviour where possible. Do not silently change existing sample users, routes, MCP tool names or evidence contracts.

## 3. Target architecture: deep modules and narrow interfaces

Retain the service-oriented shape already in the repository:

```text
Project filesystem (source of truth)
   |
   +-- Inventory / fingerprints / file identity / project scope
   |       |
   |       +-- Content-based format + version detector
   |                 |
   |                 +-- Reader registry + capability compatibility
   |                           |
   |                           +-- Reader adapters (MD, PDF, CSV, XLSX, IFC, JT probe...)
   |                                      |
   |                                      +-- Canonical extraction envelope
   |                                              |
   |                        +---------------------+--------------------+
   |                        |                     |                    |
   |                    Passages                Tables              Typed facts
   |                        |                     |                    |
   |                      FTS5               SQL tables           SQL properties
   |                        +---------------------+--------------------+
   |                                              |
   +---------------------------------------> SearchService
                                                  |
                                       permission-scoped retrieval
                                         /                 \
                                  Web UI / API          MCP server
                                                        |
                                              LLM in MCP client/host
                                              discovers schema + plans
```

The file inventory and parser status are **first-class persisted data**. Indexing is *not binary success/failure*. A file may have metadata successfully extracted but have no searchable text, no readable CAD properties, or unsupported geometry. Preserve this distinction from extraction through search and observability.

Recommended logical packages/modules (adapt to existing style; names are suggestions, not a mandate):

- `inventory` / `detection`: discovery, stable file identity, content signatures, format version, hash and change detection.
- `readers`: reader protocol/registry and format-specific implementations.
- `extraction`: canonical passages, tables, cell references, fact extraction and validation.
- `store`: durable state, migrations and authorisation-scoped SQL projections; retain FTS5.
- `service`: orchestration and policy; no HTTP/MCP dependency.
- `mcp_server` / `app`: thin adapters sharing the service.
- `coverage`: extraction diagnostics, metrics and permission-safe admin reporting.

Each module should present a narrow typed interface. Avoid turning `core.py` or `service.py` into a single file of format-specific conditionals.

## 4. Inventory, file identification and version-aware reader selection

### 4.1 Inventory *all* files, not just readable ones

For each file encountered, persist at least:

- Stable source path and logical file ID; project/folder; extension; file size; modification time; inode/file identity when useful.
- Content signature/fingerprint, detection method and confidence; actual format family; format **version** and variant when detectable.
- SHA-256 content hash, when successfully read; avoid repeat full-file hashing when a reliable change cache suffices, but verify when needed.
- Current simulated permission scope or a reference to the policy, **not** a promise that this equals Windows effective ACLs.
- Reader candidates, selected reader, reader implementation/version, capability manifest, extraction attempt identifier and outcome.
- Indexed content counts: pages/blocks, tables/rows/cells, structured facts, searchable passages, extracted properties.
- Timestamp, elapsed time, warnings, bounded error details and correlation/run ID.

Treat extension as a **hint**, not proof. Detect via content for well-supported formats; record `FORMAT_MISMATCH` when `.jt` is not a JT file, rather than passing bytes blindly to a JT parser. Handle unknown, tiny, truncated, encrypted, empty, inaccessible and symbolic-link files explicitly. Resolve paths safely; avoid traversing symlinks outside the configured root and avoid symlink cycles. Do not silently follow filesystem paths based on user-supplied SQL or MCP tool arguments.

Split inventory and classification from expensive parsing. Ideally the inventory completes even if no usable reader exists for some formats. Report files/bytes by format and version before prioritising reader work.

### 4.2 Version-aware reader registry

Define a small protocol along these lines (illustrative; use Python typing/dataclasses or Pydantic consistent with the repo):

```python
@dataclass(frozen=True)
class FileSignature:
    format_id: str            # e.g. 'pdf', 'jt', 'xlsx'
    format_version: str | None
    variant: str | None
    confidence: float
    raw_observation: str      # bounded, safe string; not arbitrary file data
    detector_version: str

@dataclass(frozen=True)
class ReaderCapability:
    metadata: bool
    text: bool
    tables: bool
    properties: bool
    geometry: bool
    pmi: bool

@dataclass(frozen=True)
class ReaderManifest:
    reader_id: str
    reader_version: str
    supported_formats: tuple[str, ...]
    supported_versions: tuple[str, ...]  # or an explicit predicate/range
    capabilities: ReaderCapability
    supported_platforms: tuple[str, ...]
    required_dependencies: tuple[str, ...]
    licence_requirement: str | None

class Reader(Protocol):
    manifest: ReaderManifest
    def probe(self, signature: FileSignature) -> 'ProbeOutcome': ...
    def extract(self, source: 'SafeSource', context: 'ExtractionContext') -> 'ExtractionEnvelope': ...
```

`probe()` should distinguish **format/version compatibility** from **reader actually installed and working**. A supported version with a missing native library is not `UNSUPPORTED_VERSION`; it is `DEPENDENCY_MISSING`. Platform restrictions and licences are equally distinct. Multiple readers may support a format/version but deliver different capabilities. Choose the least expensive *tested* reader that meets requested extraction goals; fall back to another only when safe, and record the attempts.

Treat the reader's own version and the source file's format version as separate fields. Record capability-level outcomes: `metadata=ok`, `text=none`, `tables=unsupported`, `properties=partial`, `geometry=not_attempted`, etc.

### 4.3 JT is the acceptance-case for this registry

A `.jt` filename does not guarantee a readable JT file or a supported JT version. The file format has a version-bearing header; common references describe an **80-character version string** at the start, with text such as `Version 9.5 ...` or `Version 10.0 ...`. Confirm the exact header layout and variants against the relevant Siemens JT specification before productionising the detector. Inspect only bounded bytes for *classification*. Do not confuse successful header detection with successful JT parsing.

Implement a **safe JT metadata/header probe** that attempts to report:

- `format_id='jt'`, detected major/minor version and raw version-string evidence;
- header validity (including truncated/invalid header), ambiguity and confidence;
- available JT-capable readers and which *file versions and content capabilities* each reader is verified to support;
- reader availability (installed? platform? licence?) and extraction outcome;
- optional separate extraction of assembly metadata, LOD/tessellations, PMI, and B-rep **only when a real adapter is present and validated**.

Do **not** claim that a lightweight JT probe extracts geometry. Do not promise that a reader supporting JT 9.5 supports JT 10.5 or all of its representations. Do not install unlicensed proprietary binaries or embed vendor code. A metadata-only outcome such as `DETECTED_NO_READER` is correct and desirable in the POC. `UNSUPPORTED_VERSION` must be reportable even if *other versions* of JT are supported.

Siemens documents a JT Open Toolkit with read/write capabilities and membership/licensing requirements, and has published vulnerabilities in older JT parsing components. Keep JT/CAD parsing in isolated, resource-limited worker processes with updated dependencies; do not load untrusted native CAD files in the web server process. Consult the vendor's current support matrix rather than hardcoding an assumed version range.

Testing: (a) generate **synthetic header fixtures solely for detector tests**, clearly label them as *not complete valid JT files*; (b) corrupt/truncated/extension-mismatch cases; (c) optional integration tests with authorised, known-valid JT files of different real versions. Never present a synthetic header fixture as proof that a complete JT parser works. Keep genuine customer CAD files out of git unless explicitly approved.

## 5. Extraction is a canonical, evidence-preserving pipeline

### 5.1 Common representation

Return one `ExtractionEnvelope` per source document version, with immutable/versioned content references. It should be possible to re-run a reader or upgrade a fact extractor without losing the original source evidence.

Suggested conceptual entities:

```text
documents              logical source identity / project / permission scope
document_versions      immutable content hash, revision, original path, timestamps
file_detections        content format, version, detector, confidence
reader_attempts        candidate, version, start/end, capability outcomes, errors
content_blocks         kind, text, heading, page/line/bbox/sheet/entity locator
source_tables          table id, doc_version_id, sheet/page, caption, bounds
source_columns         name, original header, data type, units, position
source_rows            table id, row number, row-level project/subject if known
source_cells           source row/column, original text, typed value, locator
facts                  parameter, subject, assertion role, typed value, SI value,
                       dimension, original unit, qualifier, confidence,
                       source row/cell/block, extractor and source version
relationships          document/project/component/spec/material/revision edges
extraction_runs        toolchain version, status, duration, warnings, errors
```

Do not automatically duplicate facts with identical row and column provenance. Preserve the fact that a project-wide spreadsheet may contain **rows about multiple projects**; row-level project context overrides an unjustified document-level assumption.

### 5.2 Deterministic readers first

In the initial implementation, prioritise these formats based on the repository/question profile:

1. **Markdown / text:** retain existing heading and line evidence; add reliable Markdown table row/column parsing without breaking fenced code handling.
2. **PDF with text layer:** retain the existing `pypdf` text reader as fallback; add a layout-aware table extractor adapter chosen through tests (e.g. `pdfplumber` or another tested library). Preserve page number and ideally table bounding box, row/column and cell provenance. Handle multiple tables, spanning/merged cells, repeated headers, column/row ambiguity and multi-page tables; mark incomplete tables rather than inventing cells. Record table extraction method and version. Detect image-only or mixed pages separately; do not claim full extraction if some pages have no text. OCR is a pluggable future reader, not an implicit success.
3. **CSV:** encoding/BOM and dialect detection, stable row numbers, headers, typed columns and raw values; malformed rows become warnings or isolated failures.
4. **XLSX:** use a tested workbook reader (e.g. `openpyxl`), record workbook/sheet, cell coordinate, displayed or cached value where available, underlying formula, unit/header interpretation and formula-evaluation limitations; do not silently treat an unevaluated formula as a numeric value. Handle hidden sheets and merged headers explicitly.
5. **IFC / DXF / STEP:** create manifest/probe first. Implement substantive extraction only for a validated adapter and appropriate real fixtures. For proprietary DWG/DGN/JT/CATIA, start with capabilities and gaps rather than fake support.

For every reader: output partial usable results if possible, preserve warnings, and distinguish `no data exists` from `data could not be extracted`. Do not make files searchable by embedding raw binary or fabricated placeholder text.

### 5.3 Structured facts with engineering semantics

Move reliable quantities and material/status parsing to **index time**, while keeping existing passage-based query behaviour available during migration. Establish an initial controlled dictionary for `roof_imposed_load`, `allowable_distributed_load`, `load_capacity`, `material_grade`, `specification_reference`, and compliance status; extend after evaluation.

A fact must contain:

- **Subject/object binding:** e.g. *Beam B-104 allowable capacity* is distinct from *floor design load*.
- **Assertion role:** design requirement, measured value, maximum capacity, proposed value, prohibition, historical claim etc.
- **Value:** original string, parsed number (including signs/ranges/tolerances where supported), original unit, normalised value, physical dimension, and qualifiers.
- **Provenance:** exact document version, extraction method/version, page, heading, table/row/column/cell or CAD entity locator, and original supporting text.
- **Quality:** deterministic versus model-derived, verified/unverified, interpretation warnings, and confidence where justified.

Never equate demand with capacity. A query for “less than 5 N/m²” must not be silently converted to “less than 5 kN/m²”; normalise *units*, not user intent. Numeric SQL must be dimensionally checked and scoped to the correct parameter and subject. Avoid choosing a nearby unrelated number merely because the document mentions a keyword.

### 5.4 Revisions, authority and missing evidence

Store logical document identity separately from each immutable version. Preserve revision, published/draft/approved status where **explicitly known**, effective date and supersession relationships. Do not infer authoritative compliance state solely from a passing mention in an old PDF. Distinguish “no matching approved document in the indexed, authorised corpus” from “no approved document exists anywhere”.

## 6. Extraction status, failure taxonomy and coverage report

Persist an attempt even when it fails. Define controlled statuses, with a primary status and per-capability result:

- `DISCOVERED`, `CLASSIFIED`, `QUEUED`, `EXTRACTING`, `INDEXED_FULL`, `INDEXED_PARTIAL`;
- `UNSUPPORTED_FORMAT`, `UNSUPPORTED_VERSION`, `NO_READER`, `DEPENDENCY_MISSING`, `LICENCE_UNAVAILABLE`, `PLATFORM_UNSUPPORTED`;
- `FORMAT_MISMATCH`, `INVALID_HEADER`, `MALFORMED`, `ENCRYPTED`, `NO_TEXT_LAYER`, `NO_EXTRACTABLE_CONTENT`;
- `PERMISSION_DENIED_TO_INDEXER`, `READ_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`, `READER_CRASH`, `INDEX_WRITE_ERROR`.

Avoid treating every exception as `reader failed`. Include a bounded normalised error code, stage, retryability, reader ID/version, format/version and run ID. Raw exception traces should not leak through user search endpoints. Keep admin-only diagnostics separate from normal search and enforce simulated access there too. Make a failing file independent of its neighbours; one unreadable file must not abort the entire batch. Index publication must reject stale workers or coordinate writers across the web/MCP processes.

**Coverage is multidimensional.** Provide a repeatable inventory and extraction dashboard/API/CLI with:

- File and byte counts by extension, detected type and **detected version**.
- Fully/partially/unsupported/unprocessed/failed counts; reason breakdown and representative authorised examples.
- Capability coverage (metadata, text, tables, facts, CAD properties, geometry), not merely `files_processed / files_discovered`.
- Extracted page/table/row/fact counts and files whose pages or tables could not be read.
- Reader success/partial/failure by adapter version, dependency availability and platform.
- Per-project coverage, stale status, retries, queue backlog and processing time.
- `unknown` and `not_checked` treated explicitly, not as success.

Provide an admin-readable CSV or JSON report and a simple web view using existing admin UI conventions. Sample format:

```json
{
  "file": "Project-A/Design/assembly.jt",
  "detected_format": "jt",
  "detected_version": "10.5",
  "reader": null,
  "state": "NO_READER",
  "capabilities": {
    "metadata": "header_only",
    "text": "unsupported",
    "tables": "unsupported",
    "geometry": "unsupported"
  },
  "last_attempt": "2026-10-29T00:00:00Z",
  "issue_code": "JT_READER_NOT_INSTALLED"
}
```

That is an **illustrative diagnostic record**, not a claim that `10.5` parsing has been implemented. Include remediation hints where appropriate (e.g. “install/test reader X”, “requires OCR”, “unsupported version 8.1”) and let the index team requeue only affected files after adding or upgrading a reader.

## 7. Permission-safe structured and unstructured search

Retain current simulated macOS users and path-based access rules, but tighten the boundary: the service must establish which document versions are visible **before** applying result limits, ranking/paging, joins, grouping or aggregations. Adding thousands of forbidden documents must not displace authorised results or change authorised counts. Search, evidence, table query and document download all use the same authorisation policy and re-check when opening original files.

For the POC, an acceptable route is a **per-request permission-scoped read-only SQL projection** (e.g. isolated in-memory SQLite database or carefully constructed temporary authorised views) containing only the user's allowed documents **and every dependent table row**. Do not merely filter the final SQL rows: `COUNT`, `GROUP BY`, `JOIN`, `EXISTS`, `NOT EXISTS` and error/timing behaviour can otherwise disclose inaccessible data. For performance later, design a scalable policy-enforcement path, but do not weaken the invariant now. The protected base index must never be exposed directly to MCP SQL.

**MCP identity is simulated only.** The current `--user` selector is explicitly unsafe for a shared server. In this demo, mark it as a mock identity and bind one session context to the process; never accept `user_id` from a query tool argument. Document clearly that real deployment requires verified identity and effective filesystem permission checks, including group, inheritance and share-level semantics. The mock implementation must remain replaceable via a narrow `AuthorisationProvider` interface.

### SQL safety contract

If enabling model-authored SQL:

- Offer only a **read-only, documented, allowlisted schema**, not arbitrary `sqlite_master`, filesystem or internal audit/permission/reader-error tables.
- Accept one validated `SELECT` only; optionally allow simple non-recursive CTEs after testing. Deny DDL/DML, `ATTACH`, `PRAGMA`, virtual-table abuses, extensions, `load_extension`, filesystem/remote functions and multiple statements. Use a SQL parser/AST allowlist plus SQLite connection-level `query_only`, read-only authorisation hooks as available, resource/step/time budgets, maximum rows, bounded response sizes and a small function allowlist. Test bypass attempts.
- Parameters must be bound separately from the SQL when tool API supports them. Prevent arbitrary table names and unrestricted joins. Implement structured error responses rather than echoing sensitive underlying database errors.
- Ensure every permitted SQL row can reference an authorised parent document or table, and that aggregates represent only authorised content.
- Make `describe_schema`/`describe_table` describe column types, join keys, **unit semantics**, example query patterns and evidence linkage; omit private file content and internal permission metadata.
- Store a query audit event without exposing private rows, and report execution truncation or timeout rather than giving a misleading complete result.

## 8. Let the MCP client be the LLM query planner

Preserve existing MCP tools `search_evidence` and `read_evidence` for backwards compatibility. Add or adapt tools after inspecting the local SDK and current tool schemas:

| Tool | Purpose | Rules |
|---|---|---|
| `list_tables` | List *queryable* structured tables/views | Safe schema only |
| `describe_schema` | Describe authorised SQL model, units and join graph | No private document content |
| `describe_table(name)` | Columns, types, meanings and evidence keys | Allowlisted names |
| `query_sql(sql, params?, limit?)` | Run validated structured read-only SQL | Scoped DB, bounded execution |
| `search_documents(query, filters?, page?)` | Search accessible passages/documents via existing FTS5 | Filter before rank/limit |
| `get_document_evidence(document_id, source_id?)` | Return exact citation and relevant context | Recheck permission |
| `get_index_coverage(...)` | Reader gaps and extraction status | Index-team-only |

If useful, preserve `search_evidence` as a high-level backwards-compatible orchestration tool rather than deleting it. Do not automatically invoke a second server-side LLM to plan queries. The host's LLM can call `list_tables` and `describe_schema`, choose SQL for numerical/status questions, FTS5 for conceptual text and both for mixed questions, then obtain citations.

**Example expected tool sequence**:

1. User asks: “Which S355 components have an allowable load below 5 kN/m² in projects awaiting approval?”
2. Client calls `describe_schema` / `describe_table`, learns table names, keys, canonical predicate and dimension (`N/m²`).
3. Client constructs safe SQL over `facts` / `documents` / `projects` / table-row relationships; server validates it, limits access and runs it.
4. Client calls `get_document_evidence` for each matching source cell/row or passage.
5. Client reports exact values, documents, revisions, locations and uncertainties, without asserting more than the source proves.

Provide several *tested* example SQL queries in `docs/MCP.md`, including numeric comparison, material-grade matching, project compliance status, join by source-row identity, a count by project and a query that should correctly return no rows. The schema is a public contract to the LLM; keep it stable and legible.

Do not introduce vectors solely to meet a diagram. Keep BM25/FTS5 as the baseline. Define an optional `SemanticRetriever` interface and add an experimental semantic path only after retrieval evaluation demonstrates better recall or relevance. Never use embeddings for numeric comparison or exact grade equality.

## 9. Evidence is part of each result, not a later decoration

Every returned structured row or unstructured match must be traceable to:

- logical parent document + immutable version/hash;
- project, document type and revision/status if known;
- exact source location: PDF page + row/column/bounding box, Excel sheet/cell, CSV/Markdown line, or CAD entity/attribute if available;
- original text or cell values, and how the match satisfied the query;
- reader/extractor version and whether extraction was complete or partial.

A result explains *why it was selected*: e.g. `allowable_distributed_load = 4,500 N/m²`, threshold `< 5,000 N/m²`, `material_grade = S355`, project compliance status `awaiting_approval`, with supporting locations. Distinguish **retrieved mention** from **confirmed engineering property**. Do not call a document “approved” because the word approved appears in unrelated text.

Avoid leaking source paths, snippets, document IDs, matching counts, hidden-project existence or error messages for forbidden files. Links to parent files should re-authorise at the point of opening and check that the cited version matches the underlying bytes; otherwise show a stale-version warning.

## 10. Test corpus and evaluation: create controlled, realistic failure cases

Keep existing 138 files/tests, then add a **small, deterministic set of synthetic project folders** representing:

- A and B projects with distinct file/folder permissions; a C project only admin can see.
- PDF with selectable text and **real aligned tabular data**; a second PDF with a scanned/image-only page (or mixed pages); an encrypted/password-protected file when testing is practical.
- XLSX multi-sheet material/load schedule with formulas and explicit units; CSV with mixed units; Markdown with tables, headings and text.
- Two different components in the same document with *roof* and *floor* values so incorrect parameter binding fails.
- Duplicate/superseded revisions, conflicting status claims, signed values, unit conversions, and a project-wide schedule whose rows belong to different projects.
- A `.jt` **header-only synthetic detector fixture** for each selected header version, plus malformed/truncated/mislabelled cases. Clearly mark these *not valid full JT files*. Real JT ingestion integration tests must be gated on a verified reader and legitimate test assets.
- One deliberately unreadable file, one reader timeout/crash simulation, one unsupported version, and one failed table extraction.

Create gold-labelled question-and-answer cases: direct value, list, exact reference, numeric comparison, material, compliance, mixed predicates, no evidence, and permissions. Record both source correctness and retrieval completeness; split `found / unverified / incomplete / not found` appropriately.

### Mandatory acceptance tests

1. Inventory identifies all files, including unsupported, unreadable and extension-mismatched sources, without terminating a batch.
2. JT header/version detection reports what it actually knows; no reader means not indexed for JT properties/geometry. A synthetic header cannot pass a JT geometry test.
3. Reader registry chooses among eligible format-version/capability combinations; handles missing dependencies, licence/platform constraints and fallback transparently.
4. PDF/CSV/XLSX/Markdown table extraction retains headers, individual row/column identity, original values, page/sheet/cell/line location and table-to-parent-document references.
5. A query `< 5 kN/m²` uses a typed value threshold of `5000 N/m²`. A `5 N/m²` query is kept different. Negative signs and different dimensions are not silently misparsed.
6. Values stay bound to the right element and engineering role; a floor design load must never satisfy a roof capacity query merely because both appear in one file.
7. Adding any number of inaccessible matching files does not change a user's matching counts, result ordering, pages or relevant error messages.
8. An unauthorised user cannot retrieve a hidden document via SQL, aggregation, `get_document_evidence`, a direct document URL or a manipulated MCP argument. Read-only SQL bypasses are rejected.
9. Every result supplies parent document, immutable source version, exact source locator, value/context and explanation. Stale sources are flagged.
10. A no-text PDF, an unsupported JT version, a reader crash and a partially parsed workbook appear in the **coverage report with distinct outcomes**.
11. Concurrent indexing cannot overwrite a newer indexed file version with an older one; interrupted runs can be retried idempotently.
12. Existing web/MCP routes, existing simulated sign-in, audit and legacy search tests remain functional (or changes are explicitly migrated and justified).

Include unit, integration and end-to-end MCP tests. Add a local test that drives an MCP client over stdio (if the project's SDK permits), not merely Python calls to tool functions. Run tests and include actual numbers; do not state “all tests pass” without execution.

## 11. Ordered implementation plan for Codex

**Phase A: Audit and correctness baseline (first).** Read repository docs/ADRs and source, run tests, identify interfaces to preserve. Fix known false-answer, signed-unit, permission-before-limit, file-level exception and no-text-PDF defects with regression tests. Coordinate index writers or disable unsafe concurrent refreshes by design, rather than pretending it is safe.

**Phase B: Inventory and reader capabilities.** Introduce version-aware content detection and reader registry, extraction attempt persistence, explicit `indexed_partial/no_reader/unsupported_version` statuses, `format/version/reader` coverage report and JT header probe. Deliver an admin CLI or endpoint that profiles the fixture corpus **before** expanding content parsing.

**Phase C: Canonical extraction and deterministic tables.** Add source tables, columns, rows, cells, source locators and extractors for PDF text tables, CSV, XLSX and Markdown tables. Preserve existing passage/FTS5 extraction; use incremental index migrations and re-extraction versioning.

**Phase D: Typed engineering facts.** Convert selected deterministic table/text values into subject-bound, unit-normalised facts; add project and revision metadata. Build source-to-fact and fact-to-document links. Separate approved/compliance assertions from free-text mentions.

**Phase E: Permission-scoped SQL + MCP client planner.** Expose safe schema discovery, read-only SQL and evidence lookup; preserve old MCP tools. Demonstrate correct client tool sequence and permission-safe `JOIN`, `COUNT`, `NOT EXISTS`, paging and follow-up queries.

**Phase F: UI, coverage, evaluation.** Show authorised result explanations, clickable evidence and extraction limitations. Add a gap dashboard for the index team; expand fixtures, evaluations and docs. Evaluate vectors separately before any production adoption.

For each phase: (1) update an ADR or focused design note, (2) add tests that fail beforehand, (3) implement minimal code, (4) run all relevant tests, (5) document measured behaviour and remaining gaps, (6) commit only with permission. Do not jump straight to Phase E if the file corpus cannot produce correct typed facts.

## 12. Delivery checklist and explicit report back

Codex should return a concise final engineering report, with:

- Architecture and code changes by module, including which existing behaviour is preserved.
- Schema migrations and exact commands to run from a clean checkout on macOS.
- Reader compatibility matrix showing each **format / source version / reader version / capabilities / installed status / license / platform / measured result**.
- Inventory and coverage numbers: files by type/version, successful/partial/unsupported/failed, and sample problems with diagnosis.
- SQL/MCP tool contracts, an example MCP client configuration, actual tool-call traces for the query examples, and permission tests.
- Evaluation results against the original and expanded test questions, including failures and false positives.
- Limitations clearly labelled: what works, what is stubbed, what needs a licensed reader, what is simulated and what is unsuitable for production.
- Updated `README.md`, `ARCHITECTURE.md`, `TODO.md`, `design/DATA-PROFILE.md`, `design/EXTRACTION.md` and `docs/MCP.md` **only where changes are justified**. Keep the original design rationale where valid; avoid wholesale rewriting.

### Definition of done for the first meaningful milestone

The existing app still runs, its original test corpus still works, and we can point it at a mixed project folder and obtain a report that says, without ambiguity: **which formats and versions were discovered, which readers were tried, what was extracted, what was only partially extracted, what remains opaque, and why**. The indexed PDF/CSV/XLSX/Markdown tables support at least a few precise, permission-scoped, source-cited numerical/material queries. The MCP client can inspect the structured schema and issue restricted SQL without any additional server-side LLM. If a JT file has no verified reader, the system explains this rather than claiming success.

## 13. Supporting sources and compatibility due diligence

Repository documents to inspect locally (do not substitute the web copies for local code):

- https://github.com/Sangrail/test/blob/main/README.md
- https://github.com/Sangrail/test/blob/main/ARCHITECTURE.md
- https://github.com/Sangrail/test/blob/main/TODO.md
- https://github.com/Sangrail/test/blob/main/design/DATA-PROFILE.md
- https://github.com/Sangrail/test/blob/main/design/EXTRACTION.md
- https://github.com/Sangrail/test/blob/main/docs/MCP.md

Reader research to validate before implementation:

- Siemens JT Open Program: https://www.siemens.com/en-gb/products/plm-components/jt/jt-open-program/
- JT v10 format reference (header/version details): https://www.plm.automation.siemens.com/en_us/Images/JT-v10-file-format-reference-rev-B_tcm1023-233786.pdf
- Siemens JT parsing security advisory SSA-001569: https://cert-portal.siemens.com/productcert/html/ssa-001569.html

The existence of a published JT format reference does **not** imply every source version can be read by an available, supported, licensed library on macOS. Verify compatibility, platform and security status by actual reader/version and test fixture.

---

## Codex kickoff prompt (paste this after placing the file in your repo)

> Read `CODEX_ENGINEERING_SEARCH_HANDOFF.md` in full and audit the existing local repository. Do not start by rebuilding the app. Compare the proposed target with the existing `engineering_search/` package, architecture docs, ADRs, tests and known defects. Produce a baseline and implementation plan, then implement **Phase A and Phase B** with tests and a working file-format/version/reader coverage report, including a conservative JT header probe. Preserve current web and MCP behaviour. Stop short of claiming support for binary CAD content without a tested reader. Report actual test results, representative failures and remaining work. Proceed to Phase C only if Phase A/B meet their acceptance criteria and the code remains maintainable.
