"""Make design/system-design.svg and design/system-design.png.

Run from the repository folder (rsvg-convert makes the PNG):

    python3 design/make_diagram.py design/system-design.svg
    rsvg-convert -z 2 design/system-design.svg -o design/system-design.png
"""
import sys
from html import escape

W, H = 1680, 1305
out = []
add = out.append

STYLE = {
    "query": ("#EAF2FD", "#2B6CB0"),
    "ingest": ("#E9F7EF", "#2F855A"),
    "store": ("#FFF6E5", "#B7791F"),
    "existing": ("#EDEFF2", "#6B7280"),
    "note": ("#FFFFFF", "#A0AEC0"),
    "mcp": ("#F3EEFC", "#6B46C1"),
}
TEXT, MUTED, MONO = "#1A202C", "#4A5568", "SFMono-Regular, Menlo, Consolas, monospace"


def box(x, y, w, h, kind, title, lines=(), dashed=False, tag=None, title_size=14):
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    ty = y + 24
    add(f'<text x="{x + 12}" y="{ty}" font-size="{title_size}" font-weight="700" fill="{TEXT}">{escape(title)}</text>')
    if tag:
        add(f'<text x="{x + w - 10}" y="{y + h - 8}" font-size="10" text-anchor="end" '
            f'font-style="italic" fill="{stroke}">{escape(tag)}</text>')
    for i, line in enumerate(lines):
        add(f'<text x="{x + 12}" y="{ty + 20 + i * 17}" font-size="12" fill="{MUTED}">{escape(line)}</text>')


def arrow(d, label=None, lx=None, ly=None, dashed=False, anchor="middle"):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    add(f'<path d="{d}" fill="none" stroke="#4A5568" stroke-width="1.6"{dash} marker-end="url(#arrow)"/>')
    if label:
        add(f'<text x="{lx}" y="{ly}" font-size="11" text-anchor="{anchor}" fill="{MUTED}">{escape(label)}</text>')


def band(y, h, fill, label):
    add(f'<rect x="15" y="{y}" width="{W - 30}" height="{h}" rx="12" fill="{fill}"/>')
    add(f'<text x="30" y="{y + 22}" font-size="12" font-weight="700" letter-spacing="1.5" fill="{MUTED}">{escape(label)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">')
add('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4A5568"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# Title and legend
add(f'<text x="30" y="44" font-size="24" font-weight="700" fill="{TEXT}">Engineering evidence search: MVP system design</text>')
add(f'<text x="30" y="70" font-size="13" fill="{MUTED}">A chat agent or the web page calls one search function · FTS5 inverted index · '
    'permissions before answers, counts and pages · each answer is exact text from one file, with its source</text>')
lx = 1065
for i, (kind, dashed, label) in enumerate([("query", False, "MVP, built"),
                                           ("mcp", False, "MCP install and test"),
                                           ("note", True, "Later phase"),
                                           ("existing", False, "Existing (brief)")]):
    x = lx + i * 150
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="5 3"' if dashed else ""
    add(f'<rect x="{x}" y="34" width="22" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
    add(f'<text x="{x + 28}" y="45" font-size="11" fill="{MUTED}">{label}</text>')

# Query plane
band(95, 360, "#F7FAFE", "QUERY PLANE · ONLINE · EACH QUESTION IN UNDER 10 S")
XS = [30, 267, 504, 741, 978, 1215, 1452]
BW, AY, AH = 200, 130, 140
box(XS[0], AY, BW, 300, "query", "Engineering lead",
    ["Asks in plain language:", "“What is the roof load", "limit at Northgate?”", "“Which documents", "specify S355?”", "",
     "Gets the value, the exact", "text and its source.", "Never opens a CAD", "file or a PDF viewer."])
box(XS[1], AY, BW, AH, "existing", "Chat-agent shell",
    ["Claude Code, Claude", "Desktop (MCP client),", "or the web page /search", "Its LLM picks the tool", "and writes the reply"], tag="existing")
box(XS[2], AY, BW, AH, "mcp", "MCP server · HTTP API",
    ["mcp_server.py, stdio", "search_evidence(question,", "mode, within, page)", "read_evidence(file_id, page)", "--user flag: not verified ⚠"])
box(XS[3], AY, BW, AH, "query", "Understand and plan",
    ["One value, or a list?", "Stop words, synonyms", "S355 → prefix S355*", "“> 5 kN/m²” → number", "comparison, with units"])
box(XS[4], AY, BW, AH, "query", "FTS5 index lookup",
    ["One MATCH, no file scans", "Most question words first,", "then BM25", "Up to 1,000 passages", "List: files with all words"])
box(XS[5], AY, BW, AH, "query", "Permissions",
    ["Rules on the repository,", "a folder or one file", "Most specific rule wins", "Before answer, counts", "and pages · fail closed"])
box(XS[6], AY, BW, AH, "query", "Answer step",
    ["Value: exact sentence", "or table row", "found · partial · not found", "List: matching files,", "number filters"])

mid = AY + 62
arrow(f"M{XS[0] + BW} {mid} H{XS[1]}")
for a in range(1, 6):
    arrow(f"M{XS[a] + BW} {mid} H{XS[a + 1]}")

BY, BH = 310, 120
box(XS[6], BY, BW, BH, "query", "Audit gate",
    ["Records who asked, the", "permission decisions and", "the answer source", "No document text · fails →", "no evidence is returned"])
box(XS[1], BY, BW, BH, "existing", "Agent reply",
    ["Quotes the value and its", "file, page and lines", "Says what was searched", "“Not found” when no", "readable file states it"], tag="existing")
add(f'<rect x="{XS[2]}" y="362" width="440" height="62" rx="8" fill="#FFFFFF" stroke="#A0AEC0" stroke-dasharray="5 4"/>')
add(f'<text x="{XS[2] + 12}" y="382" font-size="12" font-weight="700" fill="{TEXT}">Measured on 138 files (17 test questions)</text>')
add(f'<text x="{XS[2] + 12}" y="399" font-size="11.5" fill="{MUTED}">Search p50 16 ms, p95 70 ms · acceptance test: each question &lt; 10 s</text>')
add(f'<text x="{XS[2] + 12}" y="415" font-size="11.5" fill="{MUTED}">The chat agent adds its own LLM time</text>')

arrow(f"M{XS[6] + 100} {AY + AH} V{BY}")
arrow(f"M{XS[6]} {BY + 26} H{XS[1] + BW}", "answer · file · page · lines · SHA-256 version · request ID", 840, BY + 19)
arrow(f"M{XS[1]} {BY + 60} H{XS[0] + BW}")
add(f'<path d="M{XS[1] + 100} {AY + AH} V{BY}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="3 3"/>')

# Stores
CY, CH = 475, 205
add(f'<rect x="267" y="{CY}" width="{1652 - 267}" height="{CH}" rx="12" fill="#FFFDF8" stroke="#B7791F" stroke-width="1.5"/>')
add(f'<text x="480" y="{CY + 24}" font-size="13" font-weight="700" fill="{TEXT}">State folder (.runtime/)</text>')
add(f'<text x="645" y="{CY + 24}" font-size="12" fill="{MUTED}">SQLite files · the web service and MCP server can share them</text>')
SY, SH = 545, 118
box(287, SY, 170, SH, "store", "audit.sqlite3",
    ["Search and read events", "Permission decisions", "Answer sources", "No document text"], title_size=13)
box(470, SY, 170, SH, "store", "queue-<id>.sqlite3",
    ["Upload jobs", "State, attempts, errors", "Upload workers"], title_size=13)
add(f'<rect x="653" y="515" width="604" height="155" rx="10" fill="none" stroke="#B7791F" stroke-width="1.2"/>')
add(f'<text x="665" y="534" font-size="13" font-weight="700" fill="{TEXT}">index-&lt;id&gt;.sqlite3</text>')
add(f'<text x="815" y="534" font-size="12" fill="{MUTED}">structured + keyword store · WAL · one transaction per update</text>')
subs = [("documents", ["file_id", "SHA-256 version", "passage count"]),
        ("passages", ["exact text", "heading, lines", "PDF page"]),
        ("passages_fts", ["FTS5 inverted", "index: heading,", "text, path words"]),
        ("meta", ["time of the", "last change"])]
for i, (title, lines) in enumerate(subs):
    box(663 + i * 148, SY, 140, SH, "store", title, lines, title_size=13)
box(1270, SY, 175, SH, "store", "metadata + facts",
    ["project, revision, status", "subject, value, unit", "with exact source", "design/EXTRACTION.md"], dashed=True, tag="phase 2", title_size=13)
box(1458, SY, 180, SH, "store", "vectors",
    ["Embeddings per passage", "Only if the test", "questions show a gain"], dashed=True, tag="phase 3", title_size=13)
box(30, SY, 200, SH, "existing", "Repository permissions",
    ["MVP: rules in access.py", "Later: synced from the", "repository's own", "file permissions"], tag="existing")
arrow(f"M130 {SY} V{BY + BH + 20} H{XS[5] + 60} V{AY + AH}", "access rules", 600, BY + BH + 14, dashed=True)

arrow(f"M{XS[4] + 100} {AY + AH} V515")
arrow(f"M{XS[6] + 150} {BY + BH} V{CY - 12} H372 V{SY}", "write before release", 1350, CY - 18)

# Ingestion plane
IY0 = 700
band(IY0, 172, "#F5FBF7", "INGESTION PLANE · AT START, ON REINDEX AND ON UPLOAD")
IY, IH = 735, 122
box(XS[0], IY, BW, IH, "existing", "Document repository",
    ["test-repository/: 138 files", "133 Markdown, 5 PDF", "Later: DXF, DWG, JT,", "CATIA · no OCR in MVP"], tag="existing")
box(XS[1], IY, BW, IH, "ingest", "Change detection",
    ["SHA-256 of each file", "Read only new and", "changed files", "Remove deleted files"])
box(XS[2], IY, BW, IH, "ingest", "Upload queue",
    ["Markdown uploads", "Worker threads", "Retries, failed jobs", "shown in /admin"])
box(XS[3], IY, BW, IH, "ingest", "Readers (core.py)",
    ["Markdown: headings,", "blank lines, code fences", "PDF: pypdf text layer,", "page by page"])
box(XS[4], IY, BW, IH, "existing", "Extraction connectors",
    ["Metadata, text and", "properties of other", "formats", "Not used in the MVP"], dashed=True, tag="existing · later")
box(XS[5], IY, BW, IH, "ingest", "Passages",
    ["Exact text, heading", "Line range, PDF page", "At most 15 lines (PDF)", "File version (SHA-256)"])
box(XS[6], IY, BW, IH, "ingest", "Publish",
    ["All changes in one", "transaction", "Unreadable files are", "skipped and reported"])
imid = IY + 61
arrow(f"M{XS[0] + BW} {imid} H{XS[1]}")
arrow(f"M{XS[1] + BW} {imid} H{XS[2]}")
arrow(f"M{XS[2] + BW} {imid} H{XS[3]}")
arrow(f"M{XS[3] + BW} {imid} H{XS[4]}", dashed=True)
arrow(f"M{XS[4] + BW} {imid} H{XS[5]}", dashed=True)
arrow(f"M{XS[3] + 100} {IY + IH} V{IY + IH + 8} H{XS[5] + 100} V{IY + IH}")
arrow(f"M{XS[5] + BW} {imid} H{XS[6]}")
arrow(f"M{XS[2] + 76} {IY} V{SY + SH}", "enqueue / claim", XS[2] + 84, IY - 12, anchor="start")
arrow(f"M{XS[6] + 100} {IY} V715 H1100 V670", "upsert", 1200, 710)

# MCP install and test
MY, MH = 892, 222
fill, stroke = STYLE["mcp"]
add(f'<rect x="30" y="{MY}" width="{1652 - 30}" height="{MH}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
add(f'<text x="46" y="{MY + 26}" font-size="14" font-weight="700" fill="{TEXT}">Install and test the MCP server</text>')
add(f'<text x="282" y="{MY + 26}" font-size="12" fill="{MUTED}">Full guide: docs/MCP.md · Python 3.11+ and uv · '
    'the chat client starts the server on your computer and talks to it over stdio</text>')
steps = [
    ("1  Install", "uv sync --locked"),
    ("2  Check", "uv run --frozen python -m scripts.check_mcp --user kamal      → ends with “The MCP server works.”"),
    ("3  Claude Code", 'claude mcp add engineering-search-jp -- uv run --frozen --directory "$PWD" python -m engineering_search.mcp_server --user jp'),
    ("4  Claude Desktop", 'claude_desktop_config.json: "command": "<output of which uv>",'),
    ("", '"args": ["run", "--frozen", "--directory", "<repository>", "python", "-m", "engineering_search.mcp_server", "--user", "jp"]'),
    ("5  Test", "Add one server per user (jp, kamal, maya). Ask the questions in docs/MCP.md as each user. Report the request_id of each problem."),
]
for i, (label, text) in enumerate(steps):
    y = MY + 52 + i * 19
    add(f'<text x="46" y="{y}" font-size="12" font-weight="700" fill="#553C9A">{escape(label)}</text>')
    font = "Helvetica Neue, Helvetica, Arial, sans-serif" if label.startswith("5") else MONO
    add(f'<text x="190" y="{y}" font-size="11.5" font-family="{font}" fill="{TEXT}">{escape(text)}</text>')
add(f'<text x="190" y="{MY + 52 + 6 * 19}" font-size="11.5" font-weight="700" fill="#9B2C2C">'
    'Kamal must get no text, file name or count from project-northgate/ or specifications/. Report it at once if Kamal does.</text>')
add(f'<text x="46" y="{MY + 52 + 7 * 19 + 6}" font-size="12" font-weight="700" fill="#9B2C2C">⚠ Security hole</text>')
add(f'<text x="190" y="{MY + 52 + 7 * 19 + 6}" font-size="11.5" fill="#9B2C2C">'
    'The server trusts --user. It does not match the person who uses the MCP client to the file permissions. '
    'Anyone who can edit the client configuration can read as JP.</text>')
add(f'<text x="190" y="{MY + 52 + 8 * 19 + 6}" font-size="11.5" fill="#9B2C2C">'
    'Fix before real restricted files: remote MCP server with OAuth sign-in, user from the token, permissions from the repository.</text>')

# Evaluation
EY = 1130
add(f'<rect x="30" y="{EY}" width="{1652 - 30}" height="150" rx="10" fill="#FAF5FF" stroke="#6B46C1" stroke-width="1.5"/>')
add(f'<text x="46" y="{EY + 26}" font-size="14" font-weight="700" fill="{TEXT}">Evaluation and tests</text>')
add(f'<text x="210" y="{EY + 26}" font-size="12" fill="{MUTED}">Measured on every change with scripts.evaluate and pytest, not judged by eye</text>')
cols = [("Test questions", ["17 questions in evaluation/", "Values, lists, follow-ups", "Questions with no answer", "Three users, different access"]),
        ("Retrieval", ["Success@1 0.94", "MRR@10 0.95", "Recall@10 0.90", "Zero-result rate 0.00"]),
        ("Answers", ["Correct answers 1.00", "Answer text checked against", "the file: SHA-256, page, lines", "No calculated values"]),
        ("Safety", ["Permission leaks 0", "test_no_leaks.py: each user,", "each mode, each result page", "Audit written before release"]),
        ("Operations", ["p50 16 ms, p95 70 ms", "Under 10 s per question (test)", "Unreadable files reported", "Index reads changed files only"])]
for i, (title, lines) in enumerate(cols):
    x = 46 + i * 322
    add(f'<text x="{x}" y="{EY + 54}" font-size="12.5" font-weight="700" fill="#553C9A">{escape(title)}</text>')
    for j, line in enumerate(lines):
        add(f'<text x="{x}" y="{EY + 73 + j * 16}" font-size="12" fill="{MUTED}">{escape(line)}</text>')

add("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
