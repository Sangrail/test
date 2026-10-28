"""Make design/code-architecture.svg and design/code-architecture.png.

The diagram shows the modules in engineering_search/, the layer of each
module, the imports, the two processes and the files on disk. Keep it
accurate: change it when an import or a module changes.

Run from the repository folder (rsvg-convert makes the PNG):

    python3 design/make_architecture.py design/code-architecture.svg
    rsvg-convert -z 2 design/code-architecture.svg -o design/code-architecture.png
"""
import sys
from html import escape

W, H = 1680, 1640
out = []
add = out.append

STYLE = {
    "web": ("#EAF2FD", "#2B6CB0"),
    "mcp": ("#F3EEFC", "#6B46C1"),
    "service": ("#E6FFFA", "#2C7A7B"),
    "domain": ("#E9F7EF", "#2F855A"),
    "store": ("#FFF6E5", "#B7791F"),
    "core": ("#F1F5F9", "#475569"),
    "existing": ("#EDEFF2", "#6B7280"),
    "note": ("#FFFFFF", "#A0AEC0"),
}
TEXT, MUTED, MONO = "#1A202C", "#4A5568", "SFMono-Regular, Menlo, Consolas, monospace"
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


def box(x, y, w, h, kind, title, lines=(), right=(), split=None, imports=None, tag=None, dashed=False):
    """A module box. `right` is a second column of lines at x + split."""
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="6 4"' if dashed else ""
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
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4A5568"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# Title and legend
text(30, 42, "Engineering evidence search: code architecture", size=24, fill=TEXT, weight=700)
text(30, 66, "The modules in engineering_search/, by layer · every import points down the page · "
     "two processes, one SearchService in each, share the SQLite files in .runtime/", size=13)
legend = [("web", "Web front end"), ("mcp", "MCP front end"), ("service", "Service and wiring"),
          ("domain", "Domain logic"), ("store", "SQLite adapters"), ("core", "Base types"),
          ("existing", "Outside the code")]
for i, (kind, label) in enumerate(legend):
    x = 30 + i * 150
    fill, stroke = STYLE[kind]
    add(f'<rect x="{x}" y="80" width="22" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    text(x + 28, 91, label, size=11)
add(f'<path d="M1080 87 H1120" stroke="#4A5568" stroke-width="1.6" marker-end="url(#arrow)"/>')
text(1128, 91, "a call at run time (the caller is above)", size=11)
text(1400, 91, "imports: package modules only", size=11, fill="#475569", mono=True)

# 1. Clients
band(110, 150, "#F7F8FA", "CLIENTS")
box(LEFT, 142, 520, 106, "web", "Web pages · static/",
    ["search.html + search.js: sign-in, search bar, folder panel",
     "admin.html + dashboard.js: index, scan, uploads, access rules",
     "audit.html + audit.js: audit log, page by page",
     "style.css · app.py serves them · HTTP with a session cookie"])
box(610, 142, 240, 106, "existing", "Chat client",
    ["Claude Code, Claude Desktop", "Starts the MCP server as a", "child process and calls its", "tools over stdio"], tag="existing")
box(865, 142, 250, 106, "note", "Tests and scripts",
    ["tests/: create_app + TestClient", "scripts/evaluate.py: create_app",
     "scripts/check_mcp.py: starts", "mcp_server.py over stdio"])

# 2. Entry points
band(275, 150, "#F7FAFE", "ENTRY POINTS · ONE PROCESS EACH")
box(LEFT, 307, 520, 107, "web", "__main__.py · process 1: web server",
    ["python -m engineering_search --documents --state-dir --port",
     "Checks the flags, then uvicorn.run(app) on 127.0.0.1",
     "Starts the upload workers (through app.py)"], imports="runtime")
box(610, 307, 505, 107, "mcp", "mcp_server.py · process 2: MCP server",
    ["python -m engineering_search.mcp_server --user jp",
     "FastMCP over stdio · tools search_evidence, read_evidence",
     "--user → access.USERS, not verified ⚠ · reindex() at start"], imports="runtime, service, access")
arrow(f"M735 248 V307", "starts · stdio", 742, 284, anchor="start")
arrow(f"M990 248 V307", "check_mcp", 997, 284, anchor="start")

# 3. Wiring
band(440, 130, "#F2FBFA", "WIRING")
box(LEFT, 472, 870, 88, "service", "runtime.py · opens the stores and builds each process",
    ["stores(documents, state): index-<id>.sqlite3, queue-<id>.sqlite3 and audit.sqlite3 in the state folder",
     "build_app() → app.create_app(stores)  ·  build_service() → SearchService(MockPermissionStore, stores)"],
    imports="access, adapters, app, jobs, service, store")
arrow(f"M450 414 V472", "build_app()", 457, 450, anchor="start")
arrow(f"M800 414 V472", "build_service()", 807, 450, anchor="start")

# 4. HTTP front end
band(585, 165, "#F7FAFE", "HTTP FRONT END · PROCESS 1 ONLY")
box(LEFT, 617, 700, 124, "web", "app.py · FastAPI",
    ["create_app(): the app and its SearchService",
     "Default stores if none given (index in memory)",
     "WorkerPool threads → service.index_upload()",
     "Upload routes call service.queue directly",
     "imports: service, access, adapters, jobs, store, core"],
    ["/search · /auth/* · /demo/documents",
     "Index team only: /admin /index /scan /uploads",
     "/audit /telemetry /health /docs",
     "backend_boundary checks the role on each call",
     "ServiceError → JSON reply with its status"], split=390)
add('<rect x="850" y="626" width="170" height="106" rx="8" fill="#FFFFFF" stroke="#A0AEC0" stroke-dasharray="5 4"/>')
for i, line in enumerate(["The MCP server has no", "HTTP layer. Its tools", "call SearchService", "directly, in process 2."]):
    text(862, 648 + i * 18, line, size=12)
arrow(f"M{LEFT} 195 H{LEFT - 25} V680 H{LEFT}")
add(f'<text x="44" y="430" font-size="11" fill="{MUTED}" transform="rotate(-90 44 430)" text-anchor="middle">'
    'HTTP + session cookie</text>')
arrow(f"M450 560 V617", "create_app(stores)", 457, 596, anchor="start")

# 5. Service
band(765, 165, "#F2FBFA", "SERVICE · ALL SEARCH LOGIC · NO HTTP, NO MCP, NO SQL")
box(LEFT, 797, 1040, 124, "service", "service.py · SearchService · one in each process",
    ["search(user, question, limit, page, mode, within)",
     "read(user, file_id, page) · readable_files(user)",
     "scan() · reindex() · status()",
     "save_upload(job, content) · index_upload(job, start)",
     "commit_audit(event): fails → ServiceError(503)"],
    ["Holds: index, audit, permissions, queue, telemetry",
     "lock: index reads and writes in this process",
     "operation_lock: one scan or build at a time",
     "ServiceError(status, detail) for both front ends",
     "imports: query, answer, access, adapters, jobs, core"], split=530)
arrow(f"M600 741 V797", "routes call search(), read(), reindex(), scan(), save_upload()", 592, 758, anchor="end")
arrow(f"M800 560 V797", "creates", 807, 784, anchor="start")
arrow(f"M1068 414 V797", "search(), read()", 1061, 784, anchor="end")

# 6. Domain logic
band(945, 165, "#F5FBF7", "DOMAIN LOGIC · PURE PYTHON · NO FILES, NO SQL")
box(LEFT, 977, 420, 124, "domain", "answer.py",
    ["understand(question, mode) → Intent: value or list",
     "answer(): exact sentence or table row,",
     "found · partial · not_found, also stated in",
     "list_documents(): Comparison, unit conversion",
     "manifest(): the answer sources for the audit"], imports=None)
text(LEFT + 92, 977 + 24, "imports: core, query", size=11, fill=STYLE["domain"][1], mono=True)
box(640, 977, 475, 124, "domain", "access.py",
    ["ACCESS_RULES: repository, folder or file · governing_rule()",
     "MockPermissionStore.evaluate(user, files): most specific wins",
     "USERS: jp, kamal, maya · DemoSessions: pretend sign-in",
     "folder_access(): the folder list on the sign-in screen"], imports="none")
arrow(f"M470 921 V977")
arrow(f"M877 921 V977", "evaluate()", 884, 958, anchor="start")

# 7. SQLite adapters
band(1125, 165, "#FFFCF5", "ADAPTERS · THE ONLY SQL")
box(LEFT, 1157, 330, 124, "store", "store.py",
    ["SQLiteSearchIndex · WAL", "candidates(): FTS5 MATCH, then BM25", "document_matches() · passages()",
     "apply(): all changes in one transaction"], imports="core, query")
box(420, 1157, 320, 124, "store", "adapters.py",
    ["SQLiteAuditStore: append(), read_page()", "Telemetry: in memory, last 10,000",
     "queries and 100 index runs", "Resets when the process stops"], imports="none")
box(755, 1157, 360, 124, "store", "jobs.py",
    ["SQLiteJobQueue: create, enqueue, claim,", "complete, fail, retry · full at 1,000 jobs",
     "WorkerPool: threads claim a job and call", "service.index_upload()"], imports="none")
arrow(f"M567 921 V1118 H330 V1157")
arrow(f"M567 1118 H580 V1157")
arrow(f"M567 1118 H935 V1157")
text(760, 1112, "index · audit and telemetry · queue: objects that the service holds", size=11, anchor="middle")

# 8. Base
band(1305, 140, "#F6F7F9", "BASE · IMPORTS NOTHING FROM THE PACKAGE")
box(LEFT, 1337, 700, 96, "core", "core.py",
    ["Types: Passage, Document",
     "Interfaces: SearchIndex, AuditStore, AuditReader",
     "evidence_manifest() · tokens()"],
    ["source_files(), scan_files(): .md, .pdf, SHA-256",
     "extract(): Markdown by headings and blank lines",
     "PDF by page with pypdf, at most 15 lines"], split=350)
box(790, 1337, 325, 96, "core", "query.py",
    ["plan(question) → QueryPlan", "Stop words, synonym groups", "S355 → prefix S355*"])

# 9. Files on disk
band(1460, 160, "#F7F8FA", "FILES ON DISK")
box(LEFT, 1492, 300, 112, "existing", "test-repository/",
    ["138 files: 133 Markdown, 5 PDF", "core.extract() reads them",
     "service.save_upload() writes", "uploaded Markdown here"], tag="existing")
arrow(f"M300 1433 V1492", "reads", 307, 1468, anchor="start")
add(f'<rect x="400" y="1492" width="715" height="112" rx="10" fill="#FFFDF8" stroke="#B7791F" stroke-width="1.5"/>')
text(414, 1512, ".runtime/  (--state-dir)", size=13, fill=TEXT, weight=700)
text(590, 1512, "<id> comes from the document folder path · both processes open the same files", size=12)
for i, (name, owner, note) in enumerate([("index-<id>.sqlite3", "store.py", "documents, passages, FTS5, meta"),
                                         ("queue-<id>.sqlite3", "jobs.py", "upload jobs and their state"),
                                         ("audit.sqlite3", "adapters.py", "events, no document text")]):
    x = 414 + i * 233
    box(x, 1524, 220, 70, "store", name, [f"written by {owner}", note])

# Side panels
panel(110, 385, "The path of one question", [
    ("1", ["app.py POST /search, or mcp_server search_evidence",
           "User from the session cookie, or from --user"]),
    ("2", ["answer.understand(): one value or a list?",
           "Finds a comparison, for example > 5 kN/m²"]),
    ("3", ["query.plan(): stop words, synonyms, prefixes"]),
    ("4", ["store.candidates(): FTS5, up to 1,000 passages",
           "store.document_matches() for a list question"]),
    ("5", ["access.evaluate(): permitted files only from here",
           "Fails → 503 and no evidence"]),
    ("6", ["answer.answer() or answer.list_documents()",
           "Exact text from the document, never written"]),
    ("7", ["service.py pages the supporting passages"]),
    ("8", ["SQLiteAuditStore.append(): decisions, sources",
           "Fails → 503 and no evidence"]),
    ("9", ["Telemetry.record_stages(), then return",
           "Web: JSON reply · MCP: the tool result"]),
])
panel(510, 425, "The index and upload paths", [
    "Reindex: POST /index, web start or MCP start",
    ("1", ["core.source_files(), then the SHA-256 of each file"]),
    ("2", ["Compare with store.versions(): read only",
           "new and changed files"]),
    ("3", ["core.extract(): a Document with its passages",
           "A file that fails is listed in failed_files"]),
    ("4", ["queue.reconcile_ready(), store.apply(): one", "transaction for all changes"]),
    "Upload: Markdown, index team only",
    ("1", ["POST /uploads → service.queue.create()"]),
    ("2", ["PUT /uploads/{id}/content → save_upload():",
           "writes the file, then queue.enqueue()"]),
    ("3", ["WorkerPool thread: queue.claim()",
           "→ service.index_upload()"]),
    ("4", ["core.extract() → store.upsert() → queue.complete()"]),
    "Scan: POST /scan",
    ("", ["core.scan_files(): compare only, no change"]),
])
panel(950, 360, "Rules that the structure keeps", [
    ("1", ["Every import points down the page.", "No module imports one above it."]),
    ("2", ["Only app.py knows HTTP.", "Only mcp_server.py knows MCP."]),
    ("3", ["SQL is only in store.py, adapters.py", "and jobs.py."]),
    ("4", ["Permissions and the audit are in service.py,", "so both front ends give the same result."]),
    ("5", ["service.py gets its stores as objects, from", "runtime.py or from a test."]),
    ("6", ["Each process has its own SearchService, locks", "and telemetry. They share the SQLite files."]),
    ("⚠", ["MVP shortcuts: pretend sign-in, --user not", "verified, upload routes use service.queue",
           "directly, rules in access.py. See ARCHITECTURE.md"]),
])

panel(1325, 295, "Related documents", [
    ("", ["ARCHITECTURE.md", "Modules, one question step by step, MVP shortcuts"]),
    ("", ["design/system-design.svg", "The wider system: planes, stores, phases, MCP"]),
    ("", ["docs/adr/0011 and 0012", "One search service · the MCP server and its hole"]),
    ("", ["docs/adr/0006 and 0010", "Permissions before results · folder and file rules"]),
    ("", ["design/make_architecture.py", "Makes this diagram: change it with the code"]),
])

add("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
