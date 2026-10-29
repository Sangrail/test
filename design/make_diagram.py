"""Make design/system-design.svg: the system design diagram of the initial phase (T3, T4).

It marks what already exists in the company (C1-C5, assumed), what the MVP
stands in for, what the MVP builds for the use case, and what is out of scope.
Keep it in step with design/SYSTEM-DESIGN.md.

Run from the repository folder (rsvg-convert makes the PNG):

    uv run --frozen python design/make_diagram.py design/system-design.svg
    rsvg-convert -z 2 design/system-design.svg -o design/system-design.png
"""
import sys
from html import escape

W, H = 1680, 1250
out = []
add = out.append

STYLE = {
    "existing": ("#EDEFF2", "#6B7280"),   # exists in the company: C1-C5, assumed
    "standin": ("#FFF6E5", "#B7791F"),    # the MVP's labelled stand-in for an existing part
    "mvp": ("#EAF2FD", "#2B6CB0"),        # built by the MVP for the use case
    "out": ("#FFFFFF", "#A0AEC0"),        # out of scope, recorded (dashed)
    "user": ("#FFFFFF", "#4A5568"),
}
TEXT, MUTED, RED = "#1A202C", "#4A5568", "#9B2C2C"
STANDIN_TEXT = "#7B5A12"


def label(x, y, value, size=12, fill=MUTED, weight=None, anchor=None, italic=False):
    attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if italic:
        attrs += ' font-style="italic"'
    add(f'<text {attrs}>{escape(value)}</text>')


def box(x, y, w, h, kind, title, lines=(), tag=None, standin=(), title_size=14):
    """A box. `standin` lines are drawn in an amber strip at the bottom: the MVP's stand-in."""
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="6 4"' if kind == "out" else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    label(x + 12, y + 24, title, size=title_size, fill=TEXT, weight=700)
    for i, line in enumerate(lines):
        label(x + 12, y + 44 + i * 17, line)
    if standin:
        sf, ss = STYLE["standin"]
        sh = 8 + 14 * len(standin)
        sy = y + h - sh - 8
        add(f'<rect x="{x + 8}" y="{sy}" width="{w - 16}" height="{sh}" rx="5" fill="{sf}" '
            f'stroke="{ss}" stroke-width="1.2"/>')
        for i, line in enumerate(standin):
            label(x + 16, sy + 15 + i * 14, line, size=11, fill=STANDIN_TEXT)
    if tag:
        label(x + w - 10, y + h - 8, tag, size=10, fill=stroke, anchor="end", italic=True)


def arrow(d, text=None, lx=None, ly=None, dashed=False, anchor="middle", over=False):
    """An arrow. `over` draws a white halo first, so it reads as passing over a crossing line."""
    if over:
        add(f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="7"/>')
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    add(f'<path d="{d}" fill="none" stroke="#4A5568" stroke-width="1.6"{dash} marker-end="url(#arrow)"/>')
    if text:
        add(f'<text x="{lx}" y="{ly}" font-size="11" text-anchor="{anchor}" fill="{MUTED}" '
            f'paint-order="stroke" stroke="#FFFFFF" stroke-width="4">{escape(text)}</text>')


def band(y, h, fill, text):
    add(f'<rect x="15" y="{y}" width="{W - 30}" height="{h}" rx="12" fill="{fill}"/>')
    add(f'<text x="30" y="{y + 22}" font-size="12" font-weight="700" letter-spacing="1.5" fill="{MUTED}">{escape(text)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">')
add('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4A5568"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# Title and legend
label(30, 44, "Engineering evidence search: system design of the initial phase", size=24, fill=TEXT, weight=700)
label(30, 70, "The initial phase (T3): one search service between the existing chat shell and the existing stores · "
      "permissions before any limit or count · every answer quotes its file, or is refused", size=13)
for x, kind, text in [(30, "existing", "Exists in the company (C1–C5, assumed)"),
                      (330, "standin", "MVP stand-in for an existing part"),
                      (590, "mvp", "Built by the MVP for the use case"),
                      (850, "out", "Out of scope (recorded)")]:
    fill, stroke = STYLE[kind]
    dash = ' stroke-dasharray="5 3"' if kind == "out" else ""
    add(f'<rect x="{x}" y="86" width="22" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
    label(x + 28, 97, text, size=11)

# Query path
band(115, 375, "#F7FAFE", "QUERY PATH · ANSWERED WITHIN THE 8 S BUDGET, OR REFUSED AT ONCE WITH A RETRY TIME (ADR 0008)")
XS = [30, 267, 504, 741, 978, 1215, 1452]
BW, AY, AH = 200, 150, 150
BY, BH = 330, 140
box(XS[0], AY, BW, BY + BH - AY, "user", "Engineering lead (U1)",
    ["An authorised pilot", "group (K5)", "", "Asks in plain language:", "“What is the roof load",
     "limit at Northgate?”", "“Which documents", "specify S355?”", "",
     "Gets the value, the quoted", "text and its source (U5)", "Opens no CAD file and", "no PDF viewer (U6)"])
box(XS[1], AY, BW, AH, "existing", "Chat-agent shell (C5)",
    ["Claude Code, Codex, Pi", "Owns the conversation;", "its model picks a tool", "and may write SQL (K9)"],
    standin=["stand-in harness:", "the web /search page"])
box(XS[2], AY, BW, AH, "mvp", "MCP server · HTTP API",
    ["Tools over stdio, and", "the same calls on HTTP", "search_evidence,", "read_evidence, query_sql,",
     "describe_schema, …"], tag="ADR 0005")
label(XS[2] + 56, AY + AH + 16, "--user not verified (G1)", size=11, fill=RED)
box(XS[3], AY, BW, AH, "mvp", "Refuse SQL, plan",
    ["A SQL statement as a", "question: refused (K9)", "Stop words, synonyms", "S355 → prefix S355*",
     "One value, or a list?"], tag="ADR 0006")
box(XS[4], AY, BW, AH, "mvp", "Permissions first",
    ["Files with a query word,", "then the access rules", "(stand-in, G1)", "Before ranking, limits",
     "and counts (K13)"], tag="ADR 0004")
box(XS[5], AY, BW, AH, "mvp", "FTS5 lookup",
    ["One MATCH over the", "permitted files only", "Heading, text, path words", "Most words first, BM25",
     "At most 1,000 passages"], tag="ADR 0002")
box(XS[6], AY, BW, AH, "mvp", "Answer",
    ["One sentence or row,", "copied, never written", "found · unverified ·", "partial · not found",
     "List: documents, paged"], tag="ADR 0003")
mid = AY + 62
for a in range(6):
    arrow(f"M{XS[a] + BW} {mid} H{XS[a + 1]}")

box(XS[1], BY, BW, BH, "existing", "Agent reply",
    ["Quotes the value with", "its file, page, lines", "Says what was searched", "“Not found” when no",
     "readable file states it"])
fill, stroke = STYLE["mvp"]
SX, SYQ, SW, SHQ = XS[2], 360, XS[3] + BW - XS[2], 110
add(f'<rect x="{SX}" y="{SYQ}" width="{SW}" height="{SHQ}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
label(SX + 12, SYQ + 18, "Table questions: the chat agent writes SQL (ADR 0006)", size=12.5, fill=TEXT, weight=700)
for i, line in enumerate(["query_sql → access rules on every file → in-memory",
                          "projection of the permitted rows only → allowlist,",
                          "read-only, step budget, ≤ 500 rows → fingerprint check",
                          "→ audit (SQL hash, no rows) · rows cite file and line",
                          "Safe, not necessarily right (G4, G7)"]):
    label(SX + 12, SYQ + 38 + i * 14, line, size=11)
box(XS[4], BY, BW, BH, "mvp", "Audit gate",
    ["Records who asked, the", "decisions and sources", "No document text", "Fails → no evidence",
     "is returned"])
box(XS[6], BY, BW, BH, "mvp", "Fingerprint check",
    ["Hash each cited file", "Changed or gone since", "indexing → refused:", "changed_files, or 409"],
    tag="ADR 0003 · ADR 0007")

arrow(f"M{XS[6] + 100} {AY + AH} V{BY}")
arrow(f"M{XS[4]} {BY + 18} H{XS[1] + BW}", "answer · file · page · lines · fingerprint · request ID", 722, BY + 12)
arrow(f"M{XS[1]} {BY + 70} H{XS[0] + BW}")
add(f'<path d="M{XS[1] + 100} {AY + AH} V{BY}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="3 3"/>')
arrow(f"M{XS[2] + 20} {AY + AH} V{SYQ}", "SQL", XS[2] + 26, AY + AH + 16, anchor="start")
arrow(f"M{SX + SW} {SYQ + 70} H{XS[4]}")

# Stores (C4) and the access rules
CY = 530
SY, SH = CY + 45, 140
box(30, SY, 200, SH, "standin", "Access rules (G1)",
    ["access.py: repository,", "folder and file rules", "Stand-in for the", "repository's controls",
     "(K13, K15)"])
fill, stroke = STYLE["existing"]
add(f'<rect x="267" y="{CY}" width="{1652 - 267}" height="200" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
label(281, CY + 24, "Structured and/or semantic stores (C4) · existing", size=13, fill=TEXT, weight=700)
label(640, CY + 24, "the MVP stands in with SQLite files in .runtime/, shared by the web and MCP processes", size=12)
box(287, SY, 230, SH, "out", "Semantic store",
    ["Embeddings per passage", "Out of scope (O1)", "Lexical search shows", "why a passage matched"],
    tag="out of scope")
fill, stroke = STYLE["standin"]
add(f'<rect x="532" y="{SY}" width="900" height="{SH}" rx="10" fill="#FFFDF8" stroke="{stroke}" stroke-width="1.5"/>')
label(546, SY + 20, "index-<id>.sqlite3 · stand-in", size=13, fill=TEXT, weight=700)
label(756, SY + 20, "structured tables and a lexical full-text index · one transaction per refresh, under the index lock",
      size=11.5)
for i, (title, lines) in enumerate([
        ("documents", ["file_id", "content fingerprint", "(SHA-256 of the bytes)", "passage count"]),
        ("passages + FTS5", ["exact text, heading,", "page and lines", "full-text index over", "heading, text, path"]),
        ("tables + facts", ["source_tables, table_rows", "facts: subject, parameter,", "role, value, SI value",
                            "file, table, row, line"]),
        ("files", ["inventory: type, format", "version, reader, status,", "reason if not read"])]):
    box(544 + i * 220, SY + 30, 210, 102, "standin", title, lines, title_size=13)
box(1447, SY, 190, SH, "standin", "audit.sqlite3",
    ["Search, read and", "SQL events", "No document text", "Stand-in for a", "durable audit (G2)"], title_size=13)

arrow(f"M{XS[5] + 100} {AY + AH} V{SY}", "MATCH", XS[5] + 108, 520, anchor="start")
arrow(f"M{XS[6]} {BY + 80} H{XS[4] + BW}", over=True)
arrow(f"M820 {SYQ + SHQ} V{SY}", "permitted rows", 828, 494, anchor="start")
arrow(f"M{XS[4] + 100} {BY + BH} V500 H1540 V{SY}", "write before release", 1420, 494, over=True)
arrow(f"M130 {SY} V515 H960 V{AY + 120} H{XS[4]}", "access rules", 600, 510, dashed=True)

# Indexing path
IY0 = 750
band(IY0, 185, "#F5FBF7", "INDEXING PATH · ON START AND ON REQUEST · NO UPLOADS, NO TIMER, NO WATCHER (K12, K16)")
IY, IH = 785, 135
box(XS[0], IY, BW, IH, "existing", "Repository (C2)",
    ["Project folders (K15),", "read in place, never", "uploaded (K12)"],
    standin=["stand-in: test-repository/,", "149 files, 145 readable"])
box(XS[1], IY, BW, IH, "mvp", "Refresh (K16)",
    ["On start and on request", "SHA-256 fingerprint of", "every file; re-read only", "new and changed files;",
     "remove deleted ones"], tag="ADR 0007")
box(XS[2], IY, BW, IH, "mvp", "Detect type",
    ["From the content; the", "extension is a hint", "Signatures: PDF, XLSX,", "DOCX, JT, DXF",
     "Registry picks a reader"], tag="ADR 0001")
box(XS[3], IY, XS[4] + BW - XS[3], IH, "existing", "Connectors and APIs (C3)",
    ["Extract metadata, text and properties from supported files"],
    standin=["stand-in readers: Markdown · text-layer PDF · CSV · XLSX",
             "· DXF notes and title-block attributes (ASCII)",
             "Not read: scans, CAD geometry, binary DXF, DWG, JT,",
             "CATIA (G8) · each listed with its reason"])
box(XS[5], IY, BW, IH, "standin", "Passages and facts",
    ["Text with heading, page", "and lines", "Table rows with lines", "Facts from table cells,",
     "SI values (fact rules)"])
box(XS[6], IY, BW, IH, "mvp", "Publish",
    ["One transaction, under", "the index lock", "Coverage report: every", "file not read, and why",
     "(index team, G8)"])
imid = IY + 62
for a in (0, 1, 2):
    arrow(f"M{XS[a] + BW} {imid} H{XS[a + 1]}")
arrow(f"M{XS[4] + BW} {imid} H{XS[5]}")
arrow(f"M{XS[5] + BW} {imid} H{XS[6]}")
arrow(f"M{XS[6] + 100} {IY} V765 H1300 V{SY + SH}", "publish", 1430, 760)

# What this phase leaves open
GY = 955
add(f'<rect x="30" y="{GY}" width="{1652 - 30}" height="100" rx="10" fill="#FFFFFF" stroke="#A0AEC0" stroke-width="1.2"/>')
label(46, GY + 26, "What this phase leaves open", size=14, fill=TEXT, weight=700)
label(262, GY + 26, "docs/constraints/gaps.md · recorded, not solved by the MVP · the hardest is G4", size=12)
gaps = [("G1", "Identity and the repository's permissions"), ("G2", "Durable, tamper-evident audit"),
        ("G3", "Approved language-model use"), ("G4", "Quality on real questions"),
        ("G5", "Any number of users within 10 s"), ("G6", "One vocabulary for status values"),
        ("G7", "Who wrote a SQL statement"), ("G8", "What the stand-in readers cannot read"),
        ("O1", "Semantic search: out of scope"), ("O2", "Slow-query analysis: out of scope")]
for i, (gid, text) in enumerate(gaps):
    x, y = 46 + (i % 5) * 322, GY + 56 + (i // 5) * 24
    label(x, y, gid, size=12, fill=RED if gid.startswith("G") else MUTED, weight=700)
    label(x + 28, y, text, size=12)

# Measured on the test repository
EY = 1075
add(f'<rect x="30" y="{EY}" width="{1652 - 30}" height="155" rx="10" fill="#F7FAFE" stroke="#2B6CB0" stroke-width="1.5"/>')
label(46, EY + 26, "Measured on the test repository", size=14, fill=TEXT, weight=700)
label(282, EY + 26, "29 October 2026 · 149 files, 145 with a reader · scripts.evaluate, scripts.load_test and pytest · "
      "docs/METRICS.md · not proof on real questions (G4)", size=12)
cols = [("Questions", ["16 scored retrieval questions", "13 agent-written SQL questions", "Acceptance tests ask the",
                       "use case through HTTP (ADR 0009)"]),
        ("Retrieval", ["Success@1 0.88, @5 1.00", "MRR@10 0.90", "Recall@10 0.90", "Zero-result rate 0.00"]),
        ("Answers", ["Correct answers 1.00", "Each quote checked against", "the file: page and lines",
                     "Unbound value → unverified"]),
        ("Safety", ["Permission leaks 0", "Each user, mode and page", "SQL sees permitted rows only",
                    "Changed file → refused"]),
        ("Speed", ["p50 83 ms, p95 336 ms, in process", "About 10 requests/s a process", "8 s budget, else refused",
                   "at once · end to end not measured"])]
for i, (title, lines) in enumerate(cols):
    x = 46 + i * 322
    label(x, EY + 54, title, size=12.5, fill="#2B6CB0", weight=700)
    for j, line in enumerate(lines):
        label(x, EY + 73 + j * 17, line)

add("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
