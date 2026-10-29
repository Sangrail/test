"""The records database: rendering the generated files, and the consistency checks.

docs/records/design.sqlite is the source of truth; schema.sql (next to this file) is its
schema. render() is a pure function of the database: it returns every generated file and
its text, built from the active versions, with their history. problems() lists what the
database cannot show on its own: files it names that do not exist, constraints or code
that a decision mentions but does not link, a brief that differs from
docs/Starting_document.md, a schema that differs from schema.sql, broken links and broken
foreign keys. warnings() lists open drafts, decisions that need review, and scope not met.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("schema.sql")
VIEWER_TEMPLATE = Path(__file__).with_name("viewer.html")
RECORDS = ROOT / "docs/records"
DATABASE = RECORDS / "design.sqlite"
DUMP = RECORDS / "design.sql"
VIEWER = RECORDS / "index.html"
ADR_DIR = ROOT / "docs/adr"
CONSTRAINT_DIR = ROOT / "docs/constraints"
BRIEF = ROOT / "docs/Starting_document.md"
NOTICE = ("<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run "
          "`uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->")

SECTION_HEADINGS = ("Context", "Decision", "Consequences", "Implementation")
CODE_PATH = re.compile(r"^(?:engineering_search|tests|scripts|evaluation|design_records)/[\w/.-]+\.\w+$")
RELATIONS = (("serves", "Serves"), ("not met", "Not met"), ("exceeds", "Exceeds scope"))


def connect(path: Path = DATABASE, readonly: bool = True) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode={'ro' if readonly else 'rwc'}", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def create(path: Path) -> sqlite3.Connection:
    con = connect(path, readonly=False)
    con.executescript(SCHEMA.read_text())
    return con


def day(stamp: str | None) -> str:
    return (stamp or "")[:10]


# --- Constraint IDs in text -------------------------------------------------------------

def _id_pattern(con) -> re.Pattern:
    codes = "".join(row[0] for row in con.execute("SELECT code FROM constraint_groups"))
    return re.compile(rf"(?<![\w\[/#.-])([{codes}][1-9])(?![\w/])")


def _outside_code(text: str):
    """Yield (line, segments) where even segments are outside code spans; None inside fences."""
    fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
            yield line, None
            continue
        yield line, (None if fence else line.split("`"))


def mentions(con, text: str) -> set[str]:
    known = {row[0] for row in con.execute("SELECT id FROM constraints")}
    pattern, found = _id_pattern(con), set()
    for _, parts in _outside_code(text):
        for part in (parts or [])[::2]:
            found |= {m.group(1) for m in pattern.finditer(part)} & known
    return found


def link_ids(con, text: str, prefix: str) -> str:
    """Link each known constraint ID to its anchor, outside code, headings and links."""
    pages = {row[0]: row[1] for row in con.execute(
        "SELECT c.id, g.page FROM constraints c JOIN constraint_groups g ON g.code = c.group_code")}
    pattern, out = _id_pattern(con), []
    for line, parts in _outside_code(text):
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
    found = {t for t in re.findall(r"\]\(\.\./\.\./([^)#\s]+)", text) if CODE_PATH.match(t)}
    return found | {s for s in re.findall(r"`([^`\n]+)`", text) if CODE_PATH.match(s)}


# --- Decision pages ----------------------------------------------------------------------

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


def _links(con, number: int, version: int, relation: str, reasons: bool = True):
    return [(r["constraint_id"], r["reason"] if reasons else None) for r in con.execute(
        "SELECT constraint_id, reason FROM decision_constraints WHERE number = ? AND version = ? AND relation = ? "
        "ORDER BY position", (number, version, relation))]


def serves_line(con, number: int, version: int) -> str:
    return " ".join(f"**{label}:** {_id_list(rows)}." for relation, label in RELATIONS
                    if (rows := _links(con, number, version, relation)))


def adr_file(row) -> str:
    return f"{row['number']:04d}-{row['slug']}.md"


def published_decisions(con):
    """The version to publish for each decision: the active one, or the last one if withdrawn."""
    return con.execute("""
        SELECT d.slug, v.* FROM decisions d JOIN decision_versions v ON v.number = d.number
         WHERE v.lifecycle = 'active' OR (v.lifecycle = 'withdrawn' AND NOT EXISTS
               (SELECT 1 FROM decision_versions a WHERE a.number = d.number AND a.lifecycle = 'active'))
         ORDER BY d.number""").fetchall()


def _history_table(rows) -> str:
    lines = ["| Version | Active from | Until | Change | By |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        until = f"{day(r['valid_to'])} ({r['end_reason']})" if r["valid_to"] else "now"
        lines.append(f"| {r['version']} | {day(r['valid_from'])} | {until} | {r['change_reason']} | {r['changed_by']} |")
    return "\n".join(lines)


def _review_line(con, number: int) -> str:
    rows = con.execute("SELECT * FROM needs_review WHERE number = ? ORDER BY constraint_id", (number,)).fetchall()
    if not rows:
        return ""
    return "**Needs review:** " + "; ".join(
        f"{r['constraint_id']} was {r['change']} after this decision (made under version {r['made_under']}"
        + (f", now version {r['current_version']})" if r["current_version"] else ")") for r in rows) + "."


PASSIVE = {"extends": "Extended", "amends": "Amended", "supersedes in part": "Superseded in part"}


def render_decision(con, row) -> str:
    number, version = row["number"], row["version"]
    parts = [f"---\nstatus: {row['status']}\ndate: {row['date']}\nversion: {version}\n---\n{NOTICE}", f"# {row['title']}"]
    if row["lifecycle"] == "withdrawn":
        parts.append(f"> **Withdrawn** on {day(row['valid_to'])}: {row['end_reason']}. Kept for its history.")
    if row["notes"]:
        parts.append(row["notes"])
    parts.append(serves_line(con, number, version))
    if review := _review_line(con, number):
        parts.append(review)
    for section in con.execute("SELECT heading, body FROM decision_sections WHERE number = ? AND version = ? ORDER BY position",
                               (number, version)):
        parts.append(f"## {section['heading']}\n\n{section['body']}")
    history = con.execute("SELECT * FROM decision_versions WHERE number = ? AND lifecycle != 'proposed' ORDER BY version DESC",
                          (number,)).fetchall()
    later = con.execute("SELECT r.kind, d.number, d.slug FROM decision_relation_current r JOIN decisions d ON d.number = r.number "
                        "WHERE r.other = ? ORDER BY d.number", (number,)).fetchall()
    changed = "".join(f"\n- {PASSIVE[r['kind']]} by [ADR {r['number']:04d}]({adr_file(r)})." for r in later)
    parts.append("## History\n\n" + _history_table(history) + ("\n" + changed if changed else ""))
    return link_ids(con, "\n\n".join(parts), "../constraints/") + "\n"


def _range(ids: list[str]) -> str:
    return ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"


def render_adr_index(con) -> str:
    groups = []
    for group in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        rows = con.execute("SELECT id, title FROM constraint_current WHERE group_code = ? ORDER BY position",
                           (group["code"],)).fetchall()
        if rows:
            groups.append(f"| [{group['name']}](../constraints/{group['page']}) | {_range([r['id'] for r in rows])}: "
                          + "; ".join(r["title"] for r in rows) + " |")
    records = []
    for row in published_decisions(con):
        cell = _id_list(_links(con, row["number"], row["version"], "serves", reasons=False))
        for relation, label in RELATIONS[1:]:
            if rows := _links(con, row["number"], row["version"], relation, reasons=False):
                cell += f"; {label.lower()}: {_id_list(rows)}"
        status = "Withdrawn" if row["lifecycle"] == "withdrawn" else row["status"][0].upper() + row["status"][1:]
        records.append(f"| [{row['number']:04d}]({adr_file(row)}) | {row['summary']} | {cell} | {status} | "
                       f"{row['version']} | {row['implementation_summary']} |")
    review = con.execute("SELECT * FROM needs_review ORDER BY number, constraint_id").fetchall()
    review_text = ("None: every decision has been made, or reviewed, under the current wording of the items it links." if not review else
                   "\n".join(f"- ADR {r['number']:04d}: {r['constraint_id']} {r['change']} since version {r['made_under']}"
                             for r in review))
    changes = con.execute("SELECT * FROM history WHERE lifecycle != 'proposed' AND valid_from IS NOT NULL "
                          "ORDER BY valid_from DESC, kind, id, version DESC LIMIT 15").fetchall()
    change_rows = "\n".join(
        f"| {day(r['valid_from'])} | {'ADR ' + r['id'] if r['kind'] == 'decision' else r['id']} | {r['version']} | "
        f"{r['change_reason']} |" for r in changes)
    text = f"""# Architecture decision records

{NOTICE}

These records explain the decisions of the MVP, and how each one serves the intent, the constraints and the scope. They are generated from the design records database, [docs/records/design.sqlite](../records/README.md), which is the source of truth and keeps every version of every record ([ADR 0021](0021-design-records-in-one-database.md)). **Accepted** means that the direction is agreed. It does not mean that every part is implemented: each record has an "Implementation" section that says what the code does now.

## Intent, constraints and scope

Each record links the items it serves, those it knowingly leaves unmet, and the scope items it goes beyond. The items are in [docs/constraints](../constraints/README.md), each with its pillar (intent, constraint or scope), its source, where the MVP stands and its history.

| Group | Items |
| --- | --- |
{chr(10).join(groups)}

## Records

**Status** is the state of the decision: *accepted*, *amended* (still in force, with changes recorded in a later record) or *superseded in part* (the named part is replaced by a later record; the rest stands). **Version** counts the changes to the record; each page ends with its history.

| Record | Decision | Links | Status | Version | Implementation |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(records)}

## Needs review

{review_text}

## Recent changes

| Date | Record | Version | Change |
| --- | --- | --- | --- |
{change_rows}

## Related documents

[docs/README.md](../README.md) says what the MVP is and is not. [docs/records/index.html](../records/index.html) shows the records and their history in a browser. [TODO](../../TODO.md) tracks delivery and gaps. [ARCHITECTURE](../../ARCHITECTURE.md) describes the code as it runs.

## Changing a decision

Change the database, never these pages: [docs/records/README.md](../records/README.md) shows how, with plain SQL in the `sqlite3` shell. The pre-commit hook regenerates the pages. Each change adds a version with its reason; earlier versions are kept. When a later decision replaces part of an earlier one, link the two and give the earlier one a new version with its new status.
"""
    return link_ids(con, text, "../constraints/")


# --- Constraint pages --------------------------------------------------------------------

STANDING = {
    "context": "A fact about the problem, not a requirement to meet.",
    "assumed": "The brief says it exists. The MVP does not build it; it uses a stand-in to prove the chain.",
    "met": "Met by the MVP, on the test data. For a scope item: the MVP goes this far.",
    "partly met": "Met in part. Where the MVP stands says what is missing.",
    "not met": "Not met by the MVP. For a scope item, this is the failure to flag.",
    "exceeded": "The MVP goes beyond this scope item, knowingly. Acceptable, and recorded.",
}
FILE_ROLES = {"stand-in": "Stand-in in the MVP", "enforced by": "Enforced by", "measured by": "Measured by",
              "delivered by": "Delivered by"}
HOW = {"serves": "", "cites": " (cited)", "not met": " (not met)", "exceeds": " (goes beyond it)"}


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


def _item(con, r, cid: str, current: bool) -> list[str]:
    lines = ["", f'<a id="{cid.lower()}"></a>', "", f"## {cid}. {r['title']}", "", f"> {r['statement']}", "",
             f"**Pillar:** {r['pillar']}. **Source:** {_source(con, r)}.", "",
             f"**Standing:** *{r['standing']}*. {STANDING[r['standing']]}", "",
             f"**What it means for the design:** {r['meaning']}", "",
             f"**Where the MVP stands:** {r['mvp']}", ""]
    if current:
        for role, label in FILE_ROLES.items():
            paths = [f[0] for f in con.execute(
                "SELECT path FROM constraint_file_current WHERE constraint_id = ? AND role = ? ORDER BY path", (cid, role))]
            if paths:
                lines += [f"**{label}:** " + ", ".join(_repo_link(p) for p in paths) + ".", ""]
        decisions = con.execute(
            "SELECT d.number, d.slug, d.title, l.relation FROM decision_constraint_current l "
            "JOIN decision_current d ON d.number = l.number WHERE l.constraint_id = ? "
            "ORDER BY d.number, CASE l.relation WHEN 'serves' THEN 0 WHEN 'not met' THEN 1 WHEN 'exceeds' THEN 2 ELSE 3 END",
            (cid,)).fetchall()
        seen, entries = set(), []
        for d in decisions:
            if d["number"] not in seen:
                seen.add(d["number"])
                entries.append(f"- [ADR {d['number']:04d}](../adr/{adr_file(d)}): {d['title']}{HOW[d['relation']]}")
        lines += ["**Decisions:**", "", *entries, ""] if entries else ["**Decisions:** none yet.", ""]
    lines += ["**History:**", ""]
    for v in con.execute("SELECT * FROM constraint_versions WHERE constraint_id = ? AND lifecycle != 'proposed' "
                         "ORDER BY version DESC", (cid,)):
        span = f"{day(v['valid_from'])} to {day(v['valid_to'])}" if v["valid_to"] else f"from {day(v['valid_from'])}, active"
        earlier = "" if v["statement"] == r["statement"] else f" It read: “{v['statement']}”"
        ended = f" Withdrawn: {v['end_reason']}." if v["lifecycle"] == "withdrawn" else ""
        lines.append(f"- Version {v['version']}, {span}. {v['change_reason']}{earlier}{ended}")
    return lines


def render_group(con, group) -> str:
    rows = con.execute("SELECT * FROM constraint_current WHERE group_code = ? ORDER BY position", (group["code"],)).fetchall()
    withdrawn = con.execute("""
        SELECT v.* FROM constraints c JOIN constraint_versions v ON v.constraint_id = c.id AND v.lifecycle = 'withdrawn'
         WHERE c.group_code = ? AND NOT EXISTS
               (SELECT 1 FROM constraint_versions a WHERE a.constraint_id = c.id AND a.lifecycle = 'active')
         ORDER BY c.position""", (group["code"],)).fetchall()
    lines = [f"# {group['name']} ({group['code']})", "", NOTICE, "", group["intro"], "",
             "| ID | Item | Pillar | Standing | Version |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| [{r['id']}](#{r['id'].lower()}) | {r['title']} | {r['pillar']} | {r['standing']} | {r['version']} |" for r in rows]
    for r in rows:
        lines += _item(con, r, r["id"], current=True)
    if withdrawn:
        lines += ["", "## Withdrawn", "", "These items no longer apply. They are kept, with their history, so that older records still resolve."]
        for r in withdrawn:
            lines += _item(con, r, r["constraint_id"], current=False)
    return link_ids(con, "\n".join(lines) + "\n", "")


PILLARS = (("intent", "What the system is for: the direction that every decision flows from."),
           ("constraint", "What the system must work within: the environment, the data, the rules it must keep."),
           ("scope", "How far this work goes down the road. The arbiter."))


def render_constraint_index(con) -> str:
    groups = []
    for g in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        ids = [r[0] for r in con.execute("SELECT id FROM constraint_current WHERE group_code = ? ORDER BY position", (g["code"],))]
        if ids:
            groups.append(f"| [{g['name']}]({g['page']}) | {_range(ids)} | {g['summary']} |")
    pillars = []
    for pillar, words in PILLARS:
        ids = [r[0] for r in con.execute("SELECT id FROM constraint_current WHERE pillar = ? ORDER BY group_code, position", (pillar,))]
        pillars.append(f"| **{pillar.capitalize()}** | {words} | {', '.join(ids)} |")
    legend = "\n".join(f"- *{k}*: {v}" for k, v in STANDING.items())
    return f"""# Intent, constraints and scope

{NOTICE}

The background, constraints, use case, task and scope from [the brief](../Starting_document.md), what the product owner added while the MVP was built, and the production requirements that it does not meet. They are kept, with every earlier version, in the design records database ([docs/records](../records/README.md)), with the [decision records](../adr/README.md), the fourth pillar.

| Pillar | What it is | Items |
| --- | --- | --- |
{chr(10).join(pillars)}

Decisions flow from the intent and the constraints. Scope is the arbiter of how far this work goes: going beyond a scope item is acceptable, and is recorded with an *exceeds* link; falling short of one is the failure to flag. The group in an ID (B, C, U, …) says where the item came from; the pillar says what kind of item it is.

| Group | IDs | What it holds |
| --- | --- | --- |
{chr(10).join(groups)}

## Each entry gives

- the statement, its pillar and its source;
- its standing, what it means for the design, and where the MVP stands;
- the files that stand in for it, enforce it, measure it or deliver it;
- the decision records that serve it, leave it unmet, go beyond it, or cite it;
- its history: each version, when it was active, and why it changed.

**Standing:**

{legend}

## Changing an item

Change the database, never these pages: [docs/records/README.md](../records/README.md) shows how, with plain SQL in the `sqlite3` shell. IDs are never renumbered or reused; a withdrawn item keeps its anchor and its history.
"""


# --- The viewer and the dump -------------------------------------------------------------

def viewer_data(con) -> dict:
    def rows(sql):
        return [dict(r) for r in con.execute(sql)]
    published = "JOIN decision_versions v USING (number, version) WHERE v.lifecycle != 'proposed'"
    return {
        "brief": rows("SELECT heading, text FROM brief_sections ORDER BY position"),
        "sources": rows("SELECT * FROM sources ORDER BY id"),
        "groups": rows("SELECT * FROM constraint_groups ORDER BY position"),
        "items": rows("SELECT * FROM constraints ORDER BY group_code, position"),
        "item_versions": rows("SELECT * FROM constraint_versions WHERE lifecycle != 'proposed' ORDER BY constraint_id, version"),
        "item_files": rows("SELECT f.* FROM constraint_files f JOIN constraint_versions v USING (constraint_id, version) "
                           "WHERE v.lifecycle != 'proposed' ORDER BY constraint_id, version, path"),
        "decisions": rows("SELECT * FROM decisions ORDER BY number"),
        "decision_versions": rows("SELECT * FROM decision_versions WHERE lifecycle != 'proposed' ORDER BY number, version"),
        "sections": rows(f"SELECT s.* FROM decision_sections s {published} ORDER BY number, version, position"),
        "links": rows(f"SELECT l.* FROM decision_constraints l {published} ORDER BY number, version, position"),
        "relations": rows(f"SELECT r.* FROM decision_relations r {published} ORDER BY number, version, other"),
        "files": rows(f"SELECT f.* FROM decision_files f {published} ORDER BY number, version, path"),
        "reviews": rows("SELECT * FROM decision_reviews ORDER BY reviewed_at, number, constraint_id"),
        "needs_review": rows("SELECT * FROM needs_review ORDER BY number, constraint_id"),
    }


def render_viewer(con) -> str:
    data = json.dumps(viewer_data(con), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return VIEWER_TEMPLATE.read_text().replace("/*DATA*/null", data.replace("</", "<\\/"))


def render(con) -> dict[Path, str]:
    files = {ADR_DIR / adr_file(row): render_decision(con, row) for row in published_decisions(con)}
    files[ADR_DIR / "README.md"] = render_adr_index(con)
    files[CONSTRAINT_DIR / "README.md"] = render_constraint_index(con)
    for group in con.execute("SELECT * FROM constraint_groups ORDER BY position"):
        files[CONSTRAINT_DIR / group["page"]] = render_group(con, group)
    files[VIEWER] = render_viewer(con)
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


def _schema(con) -> list[tuple]:
    return [tuple(r) for r in con.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name")]


def problems(con, root: Path = ROOT) -> list[str]:
    found = [f"broken foreign key in {row[0]} (row {row[1]})" for row in con.execute("PRAGMA foreign_key_check")]
    expected = sqlite3.connect(":memory:")
    expected.executescript(SCHEMA.read_text())
    if _schema(con) != _schema(expected):
        found.append("the database schema differs from design_records/schema.sql")
    for d in con.execute("SELECT number, version, notes FROM decision_current ORDER BY number").fetchall():
        number, version = d["number"], d["version"]
        sections = con.execute("SELECT heading, body FROM decision_sections WHERE number = ? AND version = ? ORDER BY position",
                               (number, version)).fetchall()
        text = "\n".join([d["notes"] or ""] + [s["body"] for s in sections])
        linked = {r[0] for r in con.execute("SELECT constraint_id FROM decision_constraint_current WHERE number = ?", (number,))}
        cited = {r[0] for r in con.execute(
            "SELECT constraint_id FROM decision_constraint_current WHERE number = ? AND relation = 'cites'", (number,))}
        named = mentions(con, text)
        found += [f"ADR {number:04d} mentions {c} but has no decision_constraints row for it" for c in sorted(named - linked)]
        found += [f"ADR {number:04d} cites {c} but its text does not mention it" for c in sorted(cited - named)]
        files = {r[0] for r in con.execute("SELECT path FROM decision_file_current WHERE number = ?", (number,))}
        found += [f"ADR {number:04d} names {p} but has no decision_files row for it" for p in sorted(code_paths(text) - files)]
        if tuple(s["heading"] for s in sections) != SECTION_HEADINGS:
            found.append(f"ADR {number:04d} does not have the sections {', '.join(SECTION_HEADINGS)}")
    for view in ("decision_file_current", "constraint_file_current"):
        for (path,) in con.execute(f"SELECT DISTINCT path FROM {view} ORDER BY path"):
            if not (root / path).exists():
                found.append(f"{view} names {path}, which does not exist")
    stored = [(r[0], r[1]) for r in con.execute("SELECT heading, text FROM brief_sections ORDER BY position")]
    if stored != brief_sections((root / BRIEF.relative_to(ROOT)).read_text()):
        found.append("brief_sections differ from docs/Starting_document.md")
    return found


def warnings(con) -> list[str]:
    """What the records say is open: not a failure, but not to be left on main."""
    found = [f"draft: {r['kind']} {r['id']} version {r['version']} ({r['change_reason']})"
             for r in con.execute("SELECT * FROM drafts ORDER BY kind, id")]
    found += [f"needs review: ADR {r['number']:04d} links {r['constraint_id']}, {r['change']} since version {r['made_under']}"
              for r in con.execute("SELECT * FROM needs_review ORDER BY number, constraint_id")]
    found += [f"scope not met: {r['id']} {r['title']}"
              for r in con.execute("SELECT id, title FROM constraint_current WHERE pillar = 'scope' AND standing = 'not met'")]
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
    if command not in ("generate", "check"):
        print("usage: python -m design_records [generate | check | mcp]")
        return 2
    con = connect()
    if command == "generate":
        for path in generate(con):
            print("wrote", path.relative_to(ROOT))
        found = problems(con) + broken_links(render(con))
    else:
        found = check(con)
    for warning in warnings(con):
        print("warning:", warning)
    for problem in found:
        print("problem:", problem)
    return 1 if found else 0
