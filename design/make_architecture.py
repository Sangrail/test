"""Make design/code-architecture.svg and design/code-architecture.png.

The diagram shows the modules in engineering_search/, the layer of each
module, the imports, the two processes and the files on disk. It marks the
extractors (the readers and the fact rules) as simulated: in the company they
are provided by the existing connectors (C3, ADR 0001). Keep it accurate:
change it when an import or a module changes.

Run from the repository folder (rsvg-convert makes the PNG):

    uv run --frozen python design/make_architecture.py design/code-architecture.svg
    rsvg-convert -z 2 design/code-architecture.svg -o design/code-architecture.png
"""
import sys
from html import escape

TOP = 24                        # the second legend row pushes the body down
W, H = 1680, 2005 + TOP
out = []
add = out.append

STYLE = {
    "web": ("#EAF2FD", "#2B6CB0"),
    "mcp": ("#F3EEFC", "#6B46C1"),
    "service": ("#E6FFFA", "#2C7A7B"),
    "domain": ("#E9F7EF", "#2F855A"),
    "indexing": ("#FDF2F8", "#B83280"),
    "store": ("#FFF6E5", "#B7791F"),
    "core": ("#F1F5F9", "#475569"),
    "existing": ("#EDEFF2", "#6B7280"),       # exists in the company (C2, C5)
    "simulated": ("#FFFDF8", "#B7791F"),      # provided in reality, simulated here (dashed)
    "connector": ("#FFFFFF", "#6B7280"),      # a company connector, not in this code (dashed)
    "note": ("#FFFFFF", "#A0AEC0"),
}
DASHED = {"simulated", "connector"}
TEXT, MUTED, MONO = "#1A202C", "#4A5568", "SFMono-Regular, Menlo, Consolas, monospace"
SIM = "#7B5A12"
LEFT, RIGHT = 75, 1115          # the layered stack of modules
PX, PW = 1145, 505              # the side panels


def text(x, y, value, size=12, fill=MUTED, weight=None, mono=False, anchor=None, italic=False):
    attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if mono:
        attrs += f' font-family="{MONO}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if italic:
        attrs += ' font-style="italic"'
    add(f'<text {attrs}>{escape(value)}</text>')


def box(x, y, w, h, kind, title, lines=(), right=(), split=None, imports=None, tag=None):
    """A module box. `right` is a second column of lines at x + split."""
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="6 4"' if kind in DASHED else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    text(x + 12, y + 24, title, size=14, fill=TEXT, weight=700)
    for column, rows in ((x + 12, lines), (x + (split or 0), right)):
        for i, line in enumerate(rows):
            if line.startswith("imports:"):
                text(column, y + 44 + i * 17, line, size=11, fill=stroke, mono=True)
            else:
                text(column, y + 44 + i * 17, line)
    if imports is not None:
        text(x + 12, y + h - 10, f"imports: {imports}", size=11, fill=stroke, mono=True)
    if tag:
        text(x + w - 10, y + h - 8, tag, size=10, fill=stroke, anchor="end", italic=True)


def arrow(d, label=None, lx=None, ly=None, anchor="middle", dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    add(f'<path d="{d}" fill="none" stroke="#4A5568" stroke-width="1.6"{dash} marker-end="url(#arrow)"/>')
    if label:
        add(f'<text x="{lx}" y="{ly}" font-size="11" text-anchor="{anchor}" fill="{MUTED}" '
            f'paint-order="stroke" stroke="#FFFFFF" stroke-width="4">{escape(label)}</text>')


def band(y, h, fill, label):
    add(f'<rect x="15" y="{y}" width="{PX - 30}" height="{h}" rx="12" fill="{fill}"/>')
    add(f'<text x="{LEFT}" y="{y + 20}" font-size="12" font-weight="700" letter-spacing="1.5" '
        f'fill="{MUTED}">{escape(label)}</text>')


def panel(y, h, title, rows):
    """A side panel. Each row is (label, text) or a heading string."""
    add(f'<rect x="{PX}" y="{y}" width="{PW}" height="{h}" rx="10" fill="#FFFFFF" stroke="#A0AEC0" stroke-width="1.2"/>')
    text(PX + 16, y + 26, title, size=14, fill=TEXT, weight=700)
    cy = y + 50
    for row in rows:
        if isinstance(row, str):
            text(PX + 16, cy + 4, row, size=12, fill="#2C7A7B", weight=700)
            cy += 22
            continue
        label, lines = row
        if label:
            text(PX + 16, cy, label, size=12, fill=TEXT, weight=700)
        for i, line in enumerate(lines):
            text(PX + 40, cy + i * 16, line, size=12, fill=TEXT if i == 0 else MUTED)
        cy += 16 * len(lines) + 8


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">')
add('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4A5568"/></marker>'
    '<pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    '<rect width="9" height="9" fill="#FBF6EA"/><line x1="0" y1="0" x2="0" y2="9" stroke="#EEDFC0" '
    'stroke-width="3"/></pattern></defs>')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# Title and legend
text(30, 42, "Engineering evidence search: code architecture", size=24, fill=TEXT, weight=700)
text(30, 66, "The modules in engineering_search/, by layer · every import points down the page · "
     "the web server and each MCP server have their own SearchService and share the files in .runtime/", size=13)
legend = [("web", "Web front end"), ("mcp", "MCP front end"), ("service", "Service and wiring"),
          ("domain", "Search logic"), ("indexing", "Indexing line"), ("store", "SQLite adapters"),
          ("core", "Base types")]
for i, (kind, label) in enumerate(legend):
    x = 30 + i * 130
    fill, stroke = STYLE[kind]
    add(f'<rect x="{x}" y="80" width="22" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    text(x + 28, 91, label, size=11)
add('<path d="M960 87 H1000" stroke="#4A5568" stroke-width="1.6" marker-end="url(#arrow)"/>')
text(1008, 91, "a call at run time (the caller is above)", size=11)
text(1290, 91, "imports: package modules only", size=11, fill="#475569", mono=True)
for x, kind, label, hatch in [(30, "existing", "Exists in the company: the repository (C2), the chat shell (C5)", False),
                              (470, "simulated", "Provided in reality, simulated here: the extractors (C3, ADR 0001)", True),
                              (930, "connector", "A company connector: not in this code; it plugs in as a Reader", False)]:
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="4 3"' if kind in DASHED else ""
    add(f'<rect x="{x}" y="104" width="22" height="14" rx="3" fill="{"url(#hatch)" if hatch else fill}" '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    text(x + 28, 115, label, size=11)

add(f'<g transform="translate(0 {TOP})">')

# 1. Clients
band(110, 150, "#F7F8FA", "CLIENTS")
box(LEFT, 142, 520, 106, "web", "Web pages · static/",
    ["search.html + search.js: sign-in, search bar, folder panel (test harness)",
     "admin.html + dashboard.js: index status, scan, refresh, telemetry",
     "audit.html + audit.js: audit log, page by page",
     "style.css · app.py serves them · HTTP with a session cookie"])
box(610, 142, 240, 106, "existing", "Chat client (C5)",
    ["Claude Code, Codex, Pi", "Starts the MCP server as a", "child process and calls its", "tools over stdio"],
    tag="existing (C5)")
box(865, 142, 250, 106, "note", "Tests and scripts",
    ["tests/: create_app + TestClient", "tests/test_mcp_stdio.py and",
     "scripts/check_mcp.py start", "mcp_server.py over stdio"])

# 2. Entry points
band(275, 150, "#F7FAFE", "ENTRY POINTS · ONE PROCESS EACH")
box(LEFT, 307, 520, 107, "web", "__main__.py · the web server process",
    ["python -m engineering_search --documents --state-dir --port",
     "Checks the flags, then uvicorn.run(app) on 127.0.0.1",
     "Refreshes the index at start, unless --no-startup-index"], imports="runtime")
box(610, 307, 505, 107, "mcp", "mcp_server.py · one MCP server process per client",
    ["python -m engineering_search.mcp_server --user jp",
     "FastMCP over stdio · 7 tools (+ coverage) · admit() per call",
     "--user → access.USERS, not verified ⚠ · reindex() at start"], imports="runtime, service, access")
arrow("M735 248 V307", "starts · stdio", 742, 284, anchor="start")
arrow("M990 248 V307", "stdio client", 997, 284, anchor="start")

# 3. Wiring
band(440, 130, "#F2FBFA", "WIRING")
box(LEFT, 472, 870, 88, "service", "runtime.py · opens the stores and builds each process",
    ["stores(): index, index-<id>.lock (FileLock), audit, Admission(SEARCH_BUDGET_SECONDS = 8 s)",
     "build_app() → app.create_app(stores)  ·  build_service() → SearchService(MockPermissionStore, stores)"],
    imports="access, adapters, app, service, store")
arrow("M450 414 V472", "build_app()", 457, 450, anchor="start")
arrow("M800 414 V472", "build_service()", 807, 450, anchor="start")

# 4. HTTP front end
band(585, 165, "#F7FAFE", "HTTP FRONT END · WEB SERVER ONLY")
box(LEFT, 617, 700, 124, "web", "app.py · FastAPI",
    ["create_app(): the app and its SearchService",
     "AdmissionMiddleware: over budget → 503, Retry-After",
     "index_on_start → service.reindex()",
     "Default stores if none given",
     "imports: service, access, adapters, store, core"],
    ["/search · /sql · /sql/schema · /auth/*",
     "/evidence/…/tables/n/rows/n · /demo/documents",
     "Index team only: /admin /index /index/coverage",
     "/scan /audit /telemetry · /health /docs",
     "backend_boundary checks the role on each call"], split=390)
add('<rect x="850" y="626" width="170" height="106" rx="8" fill="#FFFFFF" stroke="#A0AEC0" stroke-dasharray="5 4"/>')
for i, line in enumerate(["The MCP server has no", "HTTP layer. Its tools", "call SearchService", "directly, in its process."]):
    text(862, 648 + i * 18, line, size=12)
arrow(f"M{LEFT} 195 H{LEFT - 25} V680 H{LEFT}")
add(f'<text x="44" y="430" font-size="11" fill="{MUTED}" transform="rotate(-90 44 430)" text-anchor="middle">'
    'HTTP + session cookie</text>')
arrow("M450 560 V617", "create_app(stores)", 457, 596, anchor="start")

# 5. Service
band(765, 165, "#F2FBFA", "SERVICE · ALL SEARCH LOGIC · NO HTTP, NO MCP, NO SQL")
box(LEFT, 797, 1040, 124, "service", "service.py · SearchService · one in each process",
    ["search(user, question, limit, page, mode, within)",
     "query_sql(user, sql, limit) · sql_schema() · table_row_evidence()",
     "read() · readable_files() · scan() · reindex() · status() · coverage()",
     "admit(): a ticket, or 503 busy · changed_on_disc(): cited files",
     "commit_audit(event): fails → ServiceError(503)"],
    ["Holds: root, index, index_lock, audit, permissions, admission",
     "A SQL statement as a question → 422 (K9)",
     "A cited file changed on disc → refused, or 409",
     "index_lock: FileLock, plan and publish, all processes",
     "imports: indexing, query, answer, sql, access, adapters, core"], split=530)
arrow("M600 741 V797", "routes call search(), query_sql(), reindex(), …", 592, 758, anchor="end")
arrow("M800 560 V797", "creates", 807, 784, anchor="start")
arrow("M1068 414 V797", "search(), query_sql(), …", 1061, 784, anchor="end")

# 6. Search logic
band(945, 165, "#F5FBF7", "SEARCH LOGIC · NO FILES ON DISK")
box(LEFT, 977, 370, 124, "domain", "answer.py",
    ["understand(question, mode) → Intent: value or list",
     "answer(): exact sentence or table row, with status",
     "found · unverified · partial · not_found",
     "list_documents(): comparison, signs, pages of 200",
     "manifest(): the answer sources for the audit"], imports=None)
text(LEFT + 92, 977 + 24, "imports: core, query, units", size=11, fill=STYLE["domain"][1], mono=True)
box(460, 977, 300, 124, "domain", "sql.py",
    ["Projection: SQLite in memory, per request",
     "Only permitted rows: documents, facts, …",
     "SELECT only · authoriser · step budget",
     "is_sql_statement(): refuse SQL questions"], imports="none")
box(800, 977, 315, 124, "domain", "access.py",
    ["ACCESS_RULES: repository, folder, file",
     "MockPermissionStore.evaluate(user, files)",
     "Most specific rule wins",
     "USERS · DemoSessions: pretend sign-in"], imports="none")
arrow("M400 921 V977")
arrow("M610 921 V977", "query_sql()", 617, 958, anchor="start")
arrow("M957 921 V977", "evaluate()", 964, 958, anchor="start")

# 7. Indexing line, with the simulated extractors
band(1125, 330, "#FEF7FB", "INDEXING LINE · READS FILES · NEVER WRITES THE INDEX")
arrow("M780 921 V1157", "plan(), extract()", 787, 1145, anchor="start")
box(700, 1157, 415, 279, "indexing", "indexing/ · Indexer",
    ["detect.py: ContentDetector; the extension is a hint;",
     "PDF, XLSX, DOCX, JT and DXF signatures decide",
     "the type and format version",
     "indexer.py: scan(), plan(indexed, previous), extract()",
     "extract(path): registry.select() → reader.read()",
     "  → Extraction → facts.extract_facts(tables)",
     "inventory.py: SourceFile, with reader@version",
     "status.py: statuses and hints",
     "coverage.py: by type, version, status, folder and",
     "capability, with each file not read and why",
     "The service publishes the plan under the index lock"],
    imports="core · readers/, facts.py")
fill, stroke = STYLE["simulated"]
add(f'<rect x="285" y="1150" width="395" height="295" rx="10" fill="url(#hatch)" stroke="{stroke}" '
    f'stroke-width="1.8" stroke-dasharray="8 5"/>')
text(299, 1170, "SIMULATED EXTRACTORS", size=12, fill=SIM, weight=700)
text(470, 1170, "provided in reality, simulated here", size=11, fill=SIM, italic=True)
text(299, 1186, "stand-ins for the company's connectors (C3, ADR 0001)", size=11, fill=SIM)
box(300, 1194, 365, 160, "simulated", "readers/ · sample readers",
    ["base.py: Reader protocol, ReaderManifest,",
     "read(file_id, version, raw) → Extraction",
     "registry.py: default_registry(), the one list",
     "markdown.py · pdf.py (pypdf) · csv.py ·",
     "xlsx.py (openpyxl) · dxf.py: notes and title",
     "block, no geometry · text.py: a shared helper"],
    imports="core, detect, status")
box(300, 1362, 365, 74, "simulated", "facts.py · fixed fact rules",
    ["table cells → Fact: subject, parameter, role, SI value", "imports: core, units"])
box(75, 1194, 190, 242, "connector", "Company connector",
    ["Provided in reality (C3);", "not in this code", "", "A Reader: a manifest and",
     "read() → Extraction,", "listed in the registry", "", "Closes G8: scans, CAD", "geometry, DWG, JT, CATIA"])
text(87, 1424, "plugs in here →", size=12, fill=STYLE["connector"][1], weight=700)
arrow("M265 1272 H300", dashed=True)
arrow("M700 1272 H665")
arrow("M700 1399 H665")

# 8. SQLite adapters
band(1470, 165, "#FFFCF5", "ADAPTERS · SQLITE FILES ON DISK")
box(LEFT, 1502, 480, 124, "store", "store.py",
    ["SQLiteSearchIndex · WAL · versions(): fingerprints", "candidates(query, files): FTS5, ≤ 1,000",
     "structured(files) · document_matches()", "apply(): one transaction, with the inventory"],
    imports="core, query")
box(570, 1502, 545, 124, "store", "adapters.py",
    ["FileLock: flock on index-<id>.lock", "Admission: n·mean + 2√n·spread ≤ budget",
     "SQLiteAuditStore: append(), read_page()", "Telemetry: in memory"], imports="none")
add('<path d="M75 900 H40 V1463 H842" fill="none" stroke="#4A5568" stroke-width="1.6"/>')
arrow("M380 1463 V1502")
arrow("M842 1463 V1502")
text(470, 1490, "objects that the service holds", size=11)

# 9. Base
band(1650, 140, "#F6F7F9", "BASE · IMPORTS NOTHING FROM THE PACKAGE")
box(LEFT, 1682, 430, 96, "core", "core.py",
    ["Passage, Table, TableRow, Fact, Document",
     "SearchIndex: the seam where the store is injected",
     "AuditStore, AuditReader · evidence_manifest()"])
box(515, 1682, 280, 96, "core", "units.py",
    ["Unit table, signed numbers", "to_si(): pressure in Pa, length in m", "Used by facts.py and answer.py"])
box(805, 1682, 310, 96, "core", "query.py",
    ["plan(question) → QueryPlan", "Stop words, synonym groups", "S355 → prefix S355*"])

# 10. Files on disk
band(1805, 180, "#F7F8FA", "FILES ON DISK")
add(f'<rect x="{LEFT}" y="1837" width="720" height="136" rx="10" fill="#FFFDF8" stroke="#B7791F" stroke-width="1.5"/>')
text(89, 1857, ".runtime/  (--state-dir)", size=13, fill=TEXT, weight=700)
text(265, 1857, "<id> comes from the document folder path · every process opens the same files", size=12)
for i, (name, lines) in enumerate([("index-<id>.sqlite3", ["store.py", "passages, FTS5, files,", "tables, rows, facts"]),
                                   ("index-<id>.lock", ["adapters.py FileLock", "one process plans and", "publishes at a time"]),
                                   ("audit.sqlite3", ["adapters.py", "events, SQL hashes,", "no document text"])]):
    box(89 + i * 235, 1869, 225, 94, "store", name, lines)
box(815, 1837, 300, 136, "existing", "Repository (C2)",
    ["test-repository/ stands in for it:", "149 files: 135 Markdown, 6 PDF,", "2 CSV, 1 XLSX, 1 DXF, 2 JT, 2 text",
     "Read in place, never written", "service hashes the cited files"], tag="existing (C2)")
add('<path d="M1115 1300 H1130 V1905 H1115" fill="none" stroke="#4A5568" stroke-width="1.6" marker-end="url(#arrow)"/>')

# Side panels
panel(110, 420, "The path of one question (text)", [
    ("1", ["app.py POST /search, or mcp_server search_evidence",
           "Admitted only if it fits the budget, else 503 busy"]),
    ("2", ["sql.is_sql_statement(): a SQL question → 422",
           "answer.understand(), query.plan(): value or list"]),
    ("3", ["store.document_matches(): files with a query word",
           "Then within, if given"]),
    ("4", ["access.evaluate(user): permitted files from here",
           "Fails → 503 and no evidence"]),
    ("5", ["store.candidates(query, permitted files):",
           "FTS5 inside the file filter, ≤ 1,000 passages"]),
    ("6", ["answer.answer(): found · unverified · partial",
           "or answer.list_documents(), pages of 200"]),
    ("7", ["changed_on_disc(): hash each cited file; a changed",
           "file is dropped and listed in changed_files"]),
    ("8", ["SQLiteAuditStore.append(): decisions, sources",
           "Fails → 503 and no evidence"]),
    ("9", ["Telemetry.record_stages(), then return",
           "Web: JSON reply · MCP: the tool result"]),
])
panel(545, 275, "The path of one SQL query (tables)", [
    ("1", ["app.py POST /sql, or mcp_server query_sql, admitted",
           "The chat agent wrote the SQL, not the service"]),
    ("2", ["access.evaluate() on every indexed file"]),
    ("3", ["store.structured(permitted) → sql.Projection",
           "in memory, with the permitted rows only"]),
    ("4", ["One SELECT · authoriser · query_only",
           "step budget · ≤ 500 rows · ≤ 4,000 characters"]),
    ("5", ["Rows from a file changed on disc → 409"]),
    ("6", ["Audit: SQL hash, scope, cited files, no rows"]),
    ("7", ["get_document_evidence: the row and its passage"]),
])
panel(835, 310, "The index refresh path", [
    "Refresh: POST /index, web start or MCP start",
    ("1", ["Take the FileLock (index-<id>.lock), then",
           "store.versions() and the stored inventory"]),
    ("2", ["Indexer.plan(): scan, hash, detect, choose a",
           "reader; extract new, changed or re-read files"]),
    ("3", ["Reader → Extraction: passages, tables",
           "facts.py → facts · failures with a status"]),
    ("4", ["store.apply(): one transaction; files deleted",
           "from disc are removed"]),
    "Scan: POST /scan",
    ("", ["Indexer.scan(): compare only, no change"]),
    ("", ["No uploads, no timer, no watcher (K12, K16)"]),
])
panel(1160, 440, "Rules that the structure keeps", [
    ("1", ["Every import points down the page.", "No module imports one above it."]),
    ("2", ["Only app.py knows HTTP.", "Only mcp_server.py knows MCP."]),
    ("3", ["SQL is only in store.py, sql.py", "and adapters.py."]),
    ("4", ["Permissions and the audit are in service.py,", "so both front ends give the same result."]),
    ("5", ["service.py gets its stores and the index lock as", "objects, from runtime.py or from a test."]),
    ("6", ["indexing/ reads files only. It never writes the", "index. Search code never imports it."]),
    ("7", ["Each process has its own SearchService, telemetry", "and Admission. They share SQLite files and a lock."]),
    ("8", ["The readers and fact rules are stand-ins (C3). A", "company connector is a Reader in the registry."]),
    ("⚠", ["MVP shortcuts: pretend sign-in, --user not", "verified, the agent writes the SQL, rules in",
           "access.py. See ARCHITECTURE.md"]),
])
panel(1615, 210, "Related documents", [
    ("", ["ARCHITECTURE.md", "Modules, both answer paths, the indexing line"]),
    ("", ["design/system-design.svg", "The initial phase: existing parts and stand-ins"]),
    ("", ["docs/MCP.md and docs/adr/", "Client setup · the decisions"]),
    ("", ["design/make_architecture.py", "Makes this diagram: change it with the code"]),
])

add("</g>")
add("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
