"""The records database: schema, page rendering and consistency checks.

render() is a pure function of the database: it returns every generated file and its text.
problems() lists what the database cannot show on its own: files it names that do not
exist, constraints or code that a decision mentions but does not link, a brief that
differs from docs/Starting_document.md, broken links in the generated pages, and broken
foreign keys. check() adds the generated files that differ from the disk.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "design/records/records.sqlite"
DUMP = ROOT / "design/records/records.sql"
ADR_DIR = ROOT / "docs/adr"
CONSTRAINT_DIR = ROOT / "docs/constraints"
BRIEF = ROOT / "docs/Starting_document.md"
NOTICE = ("<!-- Generated from design/records/records.sqlite. Edit the database, then run "
          "`uv run --frozen python -m design_records generate`. -->")

SCHEMA = """
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  path TEXT,                     -- repository path, when the source is a file
  date TEXT
);
CREATE TABLE brief_sections (    -- docs/Starting_document.md, verbatim
  heading TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE TABLE constraint_groups (
  code TEXT PRIMARY KEY,         -- the ID prefix
  position INTEGER NOT NULL,
  name TEXT NOT NULL,
  page TEXT NOT NULL,            -- file under docs/constraints/
  summary TEXT NOT NULL,
  intro TEXT NOT NULL
);
CREATE TABLE constraints (
  id TEXT PRIMARY KEY,           -- for example U3; never renumbered
  group_code TEXT NOT NULL REFERENCES constraint_groups(code),
  position INTEGER NOT NULL,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES sources(id),
  brief_section TEXT REFERENCES brief_sections(heading),
  source_note TEXT,
  meaning TEXT NOT NULL,         -- what it means for the design
  standing TEXT NOT NULL CHECK (standing IN ('context', 'assumed', 'met', 'partly met', 'not met')),
  mvp TEXT NOT NULL              -- where the MVP stands
);
CREATE TABLE decisions (
  number INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,         -- one line for the index
  status TEXT NOT NULL,
  date TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',  -- under the title: supersession and amendment notes
  implementation_summary TEXT NOT NULL
);
CREATE TABLE decision_sections (
  number INTEGER NOT NULL REFERENCES decisions(number),
  position INTEGER NOT NULL,
  heading TEXT NOT NULL,
  body TEXT NOT NULL,
  PRIMARY KEY (number, position)
);
CREATE TABLE decision_constraints (
  number INTEGER NOT NULL REFERENCES decisions(number),
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  relation TEXT NOT NULL CHECK (relation IN ('serves', 'not met', 'cites')),
  position INTEGER NOT NULL,
  reason TEXT,
  PRIMARY KEY (number, constraint_id, relation)
);
CREATE TABLE decision_relations (
  number INTEGER NOT NULL REFERENCES decisions(number),
  other INTEGER NOT NULL REFERENCES decisions(number),
  kind TEXT NOT NULL CHECK (kind IN ('supersedes in part', 'amends', 'extends')),
  PRIMARY KEY (number, other, kind)
);
CREATE TABLE decision_files (
  number INTEGER NOT NULL REFERENCES decisions(number),
  path TEXT NOT NULL,            -- repository path
  role TEXT NOT NULL CHECK (role IN ('implements', 'tests', 'measures')),
  PRIMARY KEY (number, path)
);
CREATE TABLE constraint_files (
  constraint_id TEXT NOT NULL REFERENCES constraints(id),
  path TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('stand-in', 'enforced by', 'measured by', 'delivered by')),
  PRIMARY KEY (constraint_id, path, role)
);
"""

SECTION_HEADINGS = ("Context", "Decision", "Consequences", "Implementation")
CODE_PATH = re.compile(r"^(?:engineering_search|tests|scripts|evaluation|design_records)/[\w/.-]+\.\w+$")


def connect(path: Path = DATABASE, readonly: bool = True) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode={'ro' if readonly else 'rwc'}", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def create(path: Path) -> sqlite3.Connection:
    con = connect(path, readonly=False)
    con.executescript(SCHEMA)
    return con


# --- Constraint IDs in text -------------------------------------------------------------

def _id_pattern(con) -> re.Pattern:
    codes = "".join(row[0] for row in con.execute("SELECT code FROM constraint_groups"))
    return re.compile(rf"(?<![\w\[/#.-])([{codes}][1-9])(?![\w/])")


def _outside_code(text: str):
    """Yield (index, line, segments) where even segments are outside code spans and fences."""
    fence = False
    for index, line in enumerate(text.split("\n")):
        if line.startswith("```"):
            fence = not fence
            yield index, line, None
            continue
        yield index, line, (None if fence else line.split("`"))


def mentions(con, text: str) -> set[str]:
    known = {row[0] for row in con.execute("SELECT id FROM constraints")}
    pattern, found = _id_pattern(con), set()
    for _, _, parts in _outside_code(text):
        for part in (parts or [])[::2]:
            found |= {m.group(1) for m in pattern.finditer(part)} & known
    return found


def link_ids(con, text: str, prefix: str) -> str:
    """Link each known constraint ID to its anchor, outside code, headings and links."""
    pages = {row[0]: row[1] for row in con.execute(
        "SELECT c.id, g.page FROM constraints c JOIN constraint_groups g ON g.code = c.group_code")}
    pattern, out = _id_pattern(con), []
    for _, line, parts in _outside_code(text):
        if parts is None or line.startswith("#"):
            out.append(line)
            continue
        for i in range(0, len(parts), 2):
            def link(m, part=parts[i]):
                cid = m.group(1)
                if cid not in pages or part[m.end():m.end() + 2] == "](":
                    return cid
                return f"[{cid}]({prefix}{pages[cid]}#{cid.lower()})"
            parts[i] = pattern.sub(link, parts[i])
        out.append("`".join(parts))
    return "\n".join(out)


def code_paths(text: str) -> set[str]:
    """Repository code paths that a decision's text links to or names in a code span."""
    found = set()
    for target in re.findall(r"\]\(\.\./\.\./([^)#\s]+)", text):
        if CODE_PATH.match(target):
            found.add(target)
    for span in re.findall(r"`([^`\n]+)`", text):
        if CODE_PATH.match(span):
            found.add(span)
    return found


# --- Rendering ---------------------------------------------------------------------------

def _id_list(rows) -> str:
    """'U1 (reason), U2–U5, R1 (reason)': runs of unexplained IDs in one group become ranges."""
    items, run = [], []

    def flush():
        if run:
            items.append(run[0] if len(run) == 1 else f"{run[0]}–{run[-1]}")
            run.clear()
    for cid, reason in rows:
        if reason:
            flush()
            items.append(f"{cid} ({reason})")
        elif run and cid[0] == run[-1][0] and int(cid[1:]) == int(run[-1][1:]) + 1:
            run.append(cid)
        else:
            flush()
            run.append(cid)
    flush()
    return ", ".join(items)


def _constraint_rows(con, number: int, relation: str, reasons: bool = True):
    return [(row["constraint_id"], row["reason"] if reasons else None) for row in con.execute(
        "SELECT constraint_id, reason FROM decision_constraints WHERE number = ? AND relation = ? "
        "ORDER BY position", (number, relation))]


def serves_line(con, number: int) -> str:
    line = f"**Serves:** {_id_list(_constraint_rows(con, number, 'serves'))}."
    unmet = _constraint_rows(con, number, "not met")
    if unmet:
        line += f" **Not met:** {_id_list(unmet)}."
    return line


def adr_file(row) -> str:
    return f"{row['number']:04d}-{row['slug']}.md"


def render_decision(con, row) -> str:
    parts = [f"---\nstatus: {row['status']}\ndate: {row['date']}\n---\n{NOTICE}", f"# {row['title']}"]
    if row["notes"]:
        parts.append(row["notes"])
    parts.append(serves_line(con, row["number"]))
    for section in con.execute("SELECT heading, body FROM decision_sections WHERE number = ? ORDER BY position",
                               (row["number"],)):
        parts.append(f"## {section['heading']}\n\n{section['body']}")
    return link_ids(con, "\n\n".join(parts), "../constraints/") + "\n"


def _range(ids: list[str]) -> str:
    return ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"


def render_adr_index(con) -> str:
    groups = []
    for group in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        rows = con.execute("SELECT id, title FROM constraints WHERE group_code = ? ORDER BY position",
                           (group["code"],)).fetchall()
        titles = "; ".join(r["title"] for r in rows)
        groups.append(f"| [{group['name']}](../constraints/{group['page']}) | {_range([r['id'] for r in rows])}: {titles} |")
    records = []
    for row in con.execute("SELECT * FROM decisions ORDER BY number"):
        serves = _id_list(_constraint_rows(con, row["number"], "serves", reasons=False))
        unmet = _constraint_rows(con, row["number"], "not met", reasons=False)
        if unmet:
            serves += f"; not met: {_id_list(unmet)}"
        status = row["status"][0].upper() + row["status"][1:]
        records.append(f"| [{row['number']:04d}]({adr_file(row)}) | {row['summary']} | {serves} | {status} | "
                       f"{row['implementation_summary']} |")
    text = f"""# Architecture decision records

{NOTICE}

These records explain the decisions of the MVP, and why each one serves the use case. **Accepted** means that the direction is agreed. It does not mean that every part is implemented: each record has an "Implementation" section that says what the code does now.

The records, the constraints and the links between them are kept in one SQLite database, [design/records/records.sqlite](../../design/records/README.md), and these pages are generated from it ([ADR 0021](0021-design-records-in-one-database.md)).

## The constraints

Each record cites the constraints it serves, linked to [docs/constraints](../constraints/README.md), where each one is stated with its source, what it means for the design and where the MVP stands. **Not met** names a production requirement that the record knowingly leaves open.

| Group | IDs |
| --- | --- |
{chr(10).join(groups)}

## Records

**Status** is the state of the decision: *accepted*, *amended* (still in force, with changes recorded in a later record) or *superseded in part* (the named part is replaced by a later record; the rest stands). No record is fully superseded.

| Record | Decision | Serves | Status | Implementation |
| --- | --- | --- | --- | --- |
{chr(10).join(records)}

## Related documents

[docs/README.md](../README.md) says what the MVP is and is not. [TODO](../../TODO.md) tracks delivery and gaps. [ARCHITECTURE](../../ARCHITECTURE.md) describes the code as it runs. [GLOSSARY](../../GLOSSARY.md) defines the terms. The [system design](../../design/SYSTEM-DESIGN.md) holds proposals, not shipped features.

## Changing a decision

Edit the database, not these pages, then run `uv run --frozen python -m design_records generate`; [design/records/README.md](../../design/records/README.md) shows how. When a decision changes, add the next numbered record, link it to the record it supersedes or amends, and update the older record's status and notes. Keep the reasons and the implementation status separate. Do not erase earlier trade-offs. An accepted future extension does not bring CAD into the MVP scope.
"""
    return link_ids(con, text, "../constraints/")


STANDING = {
    "context": "A fact about the problem, not a requirement to meet.",
    "assumed": "The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.",
    "met": "Met by the MVP, on the test data.",
    "partly met": "Met in part. Where the MVP stands says what is missing.",
    "not met": "Not met by the MVP.",
}
FILE_ROLES = {"stand-in": "Stand-in in the MVP", "enforced by": "Enforced by", "measured by": "Measured by",
              "delivered by": "Delivered by"}


def _source(con, row) -> str:
    source = con.execute("SELECT * FROM sources WHERE id = ?", (row["source_id"],)).fetchone()
    text = f"[{source['title']}](../../{source['path']})" if source["path"] else source["title"]
    if row["brief_section"]:
        text += f", {row['brief_section'].lower()}"
    if row["source_note"]:
        text += f". {row['source_note']}"
    return text


def _repo_link(path: str) -> str:
    return f"[`{path}`](../../{path})"


def render_group(con, group) -> str:
    rows = con.execute("SELECT * FROM constraints WHERE group_code = ? ORDER BY position", (group["code"],)).fetchall()
    lines = [f"# {group['name']} ({group['code']})", "", NOTICE, "", group["intro"], "",
             "| ID | Constraint | Standing |", "| --- | --- | --- |"]
    lines += [f"| [{r['id']}](#{r['id'].lower()}) | {r['title']} | {r['standing']} |" for r in rows]
    for r in rows:
        lines += ["", f'<a id="{r["id"].lower()}"></a>', "", f"## {r['id']}. {r['title']}", "",
                  f"> {r['statement']}", "", f"**Source:** {_source(con, r)}.", "",
                  f"**Standing:** *{r['standing']}*. {STANDING[r['standing']]}", "",
                  f"**What it means for the design:** {r['meaning']}", "",
                  f"**Where the MVP stands:** {r['mvp']}", ""]
        for role, label in FILE_ROLES.items():
            paths = [f[0] for f in con.execute(
                "SELECT path FROM constraint_files WHERE constraint_id = ? AND role = ? ORDER BY path", (r["id"], role))]
            if paths:
                lines += [f"**{label}:** " + ", ".join(_repo_link(p) for p in paths) + ".", ""]
        decisions = con.execute(
            "SELECT d.number, d.slug, d.title, dc.relation FROM decision_constraints dc "
            "JOIN decisions d ON d.number = dc.number WHERE dc.constraint_id = ? ORDER BY d.number, dc.relation DESC",
            (r["id"],)).fetchall()
        if decisions:
            lines += ["**Decisions:**", ""]
            seen = set()
            for d in decisions:
                if d["number"] in seen:
                    continue
                seen.add(d["number"])
                how = {"serves": "", "cites": " (cited)", "not met": " (not met)"}[d["relation"]]
                lines.append(f"- [ADR {d['number']:04d}](../adr/{adr_file(d)}): {d['title']}{how}")
        else:
            lines.append("**Decisions:** none yet.")
    return link_ids(con, "\n".join(lines) + "\n", "")


def render_constraint_index(con) -> str:
    rows = []
    for g in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        ids = [r[0] for r in con.execute("SELECT id FROM constraints WHERE group_code = ? ORDER BY position", (g["code"],))]
        rows.append(f"| [{g['name']}]({g['page']}) | {_range(ids)} | {g['summary']} |")
    legend = "\n".join(f"- *{k}*: {v}" for k, v in STANDING.items())
    return f"""# Constraints

{NOTICE}

The background, constraints, use case, task and scope from [the brief](../Starting_document.md), the requirements added while the MVP was built, and the production requirements it does not meet. Each has a stable ID and anchor, so a decision record can link to it, and each page lists the decision records and the files linked to it. They are kept in the [design records database](../../design/records/README.md) with the decision records.

| Group | IDs | What it holds |
| --- | --- | --- |
{chr(10).join(rows)}

## Each entry gives

- the statement, quoted or closely paraphrased from its source;
- its source and its standing;
- what it means for the design, and where the MVP stands;
- the files that stand in for it, enforce it or measure it;
- the decision records that serve it, leave it unmet, or cite it.

**Standing:**

{legend}

## How to cite a constraint

Add a row to `decision_constraints` in the database (`serves`, `not met` or `cites`) and name the ID in the record's text. The generated pages link every ID to its anchor: the ID in lower case. Do not renumber an ID. If a constraint changes, edit its row and say what changed; if it no longer applies, keep the row and say so.
"""


def render(con) -> dict[Path, str]:
    files = {ADR_DIR / adr_file(row): render_decision(con, row)
             for row in con.execute("SELECT * FROM decisions ORDER BY number")}
    files[ADR_DIR / "README.md"] = render_adr_index(con)
    files[CONSTRAINT_DIR / "README.md"] = render_constraint_index(con)
    for group in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        files[CONSTRAINT_DIR / group["page"]] = render_group(con, group)
    files[DUMP] = "\n".join(con.iterdump()) + "\n"
    return files


# --- Checks ------------------------------------------------------------------------------

def brief_sections(text: str) -> list[tuple[str, str]]:
    sections = re.split(r"^# ", text, flags=re.M)[1:]
    return [(s.split("\n", 1)[0].strip().rstrip(":").strip(), s.split("\n", 1)[1].strip()) for s in sections]


def _anchors(text: str) -> set[str]:
    found = set(re.findall(r'<a id="([^"]+)"', text))
    for heading in re.findall(r"^#+ (.+)$", text, re.M):
        found.add(re.sub(r"[^\w\s-]", "", heading.lower()).strip().replace(" ", "-"))
    return found


def broken_links(files: dict[Path, str]) -> list[str]:
    found = []
    for path, text in files.items():
        if path.suffix != ".md":
            continue
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if target.startswith(("http:", "https:", "mailto:")):
                continue
            file, _, anchor = target.partition("#")
            resolved = (path.parent / file).resolve() if file else path
            if resolved not in files and not resolved.exists():
                found.append(f"{path.relative_to(ROOT)}: no file {target}")
            elif anchor and resolved.suffix == ".md":
                body = files.get(resolved) or resolved.read_text()
                if anchor not in _anchors(body):
                    found.append(f"{path.relative_to(ROOT)}: no anchor {target}")
    return found


def problems(con, root: Path = ROOT) -> list[str]:
    found = [f"broken foreign key in {row[0]} (row {row[1]})" for row in con.execute("PRAGMA foreign_key_check")]
    for d in con.execute("SELECT number, notes FROM decisions ORDER BY number").fetchall():
        number = d["number"]
        text = "\n".join([d["notes"]] + [s[0] for s in con.execute(
            "SELECT body FROM decision_sections WHERE number = ?", (number,))])
        linked = {r[0] for r in con.execute("SELECT constraint_id FROM decision_constraints WHERE number = ?", (number,))}
        cited = {r[0] for r in con.execute(
            "SELECT constraint_id FROM decision_constraints WHERE number = ? AND relation = 'cites'", (number,))}
        named = mentions(con, text)
        found += [f"ADR {number:04d} mentions {c} but has no decision_constraints row for it" for c in sorted(named - linked)]
        found += [f"ADR {number:04d} cites {c} but its text does not mention it" for c in sorted(cited - named)]
        files = {r[0] for r in con.execute("SELECT path FROM decision_files WHERE number = ?", (number,))}
        found += [f"ADR {number:04d} names {p} but has no decision_files row for it" for p in sorted(code_paths(text) - files)]
        headings = tuple(r[0] for r in con.execute(
            "SELECT heading FROM decision_sections WHERE number = ? ORDER BY position", (number,)))
        if headings != SECTION_HEADINGS:
            found.append(f"ADR {number:04d} has sections {headings}, expected {SECTION_HEADINGS}")
    for table in ("decision_files", "constraint_files"):
        for (path,) in con.execute(f"SELECT DISTINCT path FROM {table} ORDER BY path"):
            if not (root / path).exists():
                found.append(f"{table} names {path}, which does not exist")
    stored = [(r[0], r[1]) for r in con.execute("SELECT heading, text FROM brief_sections ORDER BY position")]
    if stored != brief_sections((root / BRIEF.relative_to(ROOT)).read_text()):
        found.append("brief_sections differ from docs/Starting_document.md")
    return found


def check(con, root: Path = ROOT) -> list[str]:
    files = render(con)
    found = [f"{path.relative_to(ROOT)} differs from the database (run generate)"
             for path, text in files.items() if not path.exists() or path.read_text() != text]
    found += [f"{path.relative_to(ROOT)} is not generated from the database"
              for path in sorted(ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")) if path not in files]
    return found + problems(con, root) + broken_links(files)


def generate(con) -> list[Path]:
    files = render(con)
    for path in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md"):
        if path not in files:
            path.unlink()
    written = []
    for path, text in files.items():
        if not path.exists() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            written.append(path)
    return written


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "check"
    if command == "mcp":
        from .mcp_server import main as serve
        serve()
        return 0
    con = connect()
    if command == "generate":
        for path in generate(con):
            print("wrote", path.relative_to(ROOT))
        found = problems(con) + broken_links(render(con))
    elif command == "check":
        found = check(con)
    else:
        print("usage: python -m design_records [generate | check | mcp]")
        return 2
    for problem in found:
        print("problem:", problem)
    return 1 if found else 0
