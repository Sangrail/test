"""An MCP server over the design records, for agents working on this project.

Before changing the design or the code, an agent can ask which decisions and items of
intent, constraint and scope govern a file, read a record with its history, see what
needs review, search, run the consistency check, or query the database with read-only
SQL. It can propose a change, which becomes a draft version. It cannot activate one: a
person reads the draft and activates it in the database, so the agent cannot change the
spec to fit its code.

    uv run --frozen python -m design_records mcp
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import records

INSTRUCTIONS = """The design records of this project, and its source of truth for the design:
the items of intent, constraint and scope (IDs such as U3, C3, S5, R8), and the architecture
decision records (ADRs), each with every version, the links between them, and the files that
implement, test or stand in for them. Decisions flow from intent and constraints. Scope is the
arbiter of how far the work goes: going beyond a scope item is acceptable and must be recorded
(an "exceeds" link); falling short of one is the failure to flag.

Use them during development:
- Before changing a file, call governing_records with its path, and read what it returns.
- Before a design decision, search the records and read the items it touches.
- Before a commit, check needs_review and drafts, and say in the commit message what the change
  serves and anything it flags.
- A change that conflicts with an accepted decision needs a new decision version or record,
  not a quiet edit. Propose it with propose_change: it becomes a draft that a person activates.
Items with standing "assumed" exist in the company already (for example the connectors, C3);
the MVP only uses stand-ins for them."""

ROW_LIMIT = 200
CONSTRAINT_FIELDS = ("pillar", "title", "statement", "meaning", "standing", "mvp", "source_note")
DECISION_FIELDS = ("title", "summary", "status", "notes", "implementation_summary")


def _rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def _covers(entry: str, path: str) -> bool:
    """A stored path governs a file when it is the file or a folder that holds it."""
    entry, path = entry.rstrip("/"), path.strip().lstrip("./").rstrip("/")
    return path == entry or path.startswith(entry + "/") or entry.startswith(path + "/")


def create_server(database: Path = records.DATABASE) -> FastMCP:
    server = FastMCP("design-records", instructions=INSTRUCTIONS)

    def connect() -> sqlite3.Connection:
        con = records.connect(database)
        con.execute("PRAGMA query_only = ON")
        return con

    @server.tool()
    def overview() -> dict:
        """The current items by pillar (ID, title, standing, version), the current decisions
        (number, title, status, version), and how many need review or are drafts. Start here."""
        with connect() as con:
            pillars = {}
            for row in con.execute("SELECT id, pillar, title, standing, version FROM constraint_current "
                                   "ORDER BY group_code, position"):
                pillars.setdefault(row["pillar"], []).append({k: row[k] for k in ("id", "title", "standing", "version")})
            decisions = _rows(con.execute("SELECT number, title, status, version FROM decision_current ORDER BY number"))
            open_items = {"needs_review": con.execute("SELECT count(*) FROM needs_review").fetchone()[0],
                          "drafts": con.execute("SELECT count(*) FROM drafts").fetchone()[0]}
        return {"pillars": pillars, "decisions": decisions, "open": open_items}

    @server.tool()
    def get_constraint(constraint_id: str, version: int | None = None) -> dict:
        """One item of intent, constraint or scope (for example "U3" or "S5"): its statement, pillar,
        source, standing, what it means for the design, where the MVP stands, its files, the current
        decisions linked to it (with the version each was made under) and its history. Pass a version
        to read an earlier one."""
        cid = constraint_id.strip().upper()
        with connect() as con:
            versions = _rows(con.execute("SELECT * FROM constraint_versions WHERE constraint_id = ? ORDER BY version", (cid,)))
            if not versions:
                return {"error": f"No item {constraint_id}. Call overview for the IDs."}
            current = next((v for v in versions if v["lifecycle"] == "active"), versions[-1])
            result = next((v for v in versions if v["version"] == version), current) if version else current
            result = dict(result)
            result["files"] = _rows(con.execute(
                "SELECT path, role FROM constraint_files WHERE constraint_id = ? AND version = ? ORDER BY role, path",
                (cid, result["version"])))
            result["decisions"] = _rows(con.execute(
                "SELECT d.number, d.title, d.status, l.relation, l.reason, l.constraint_version AS made_under "
                "FROM decision_constraint_current l JOIN decision_current d ON d.number = l.number "
                "WHERE l.constraint_id = ? ORDER BY d.number", (cid,)))
            result["history"] = [{k: v[k] for k in ("version", "lifecycle", "change_reason", "changed_by", "valid_from",
                                                     "valid_to", "end_reason")} for v in versions]
        return result

    @server.tool()
    def get_decision(number: int, include_text: bool = True, version: int | None = None) -> dict:
        """One decision record by number: status, the items it serves, leaves unmet, goes beyond or
        cites (with reasons, and the item version it was made under), the records it changes and those
        that change it, its files, what needs review, its reviews, its history and (by default) its
        notes and sections. Pass a version to read an earlier one."""
        with connect() as con:
            versions = _rows(con.execute("SELECT * FROM decision_versions WHERE number = ? ORDER BY version", (number,)))
            if not versions:
                return {"error": f"No decision {number}. Call overview for the numbers."}
            current = next((v for v in versions if v["lifecycle"] == "active"), versions[-1])
            result = dict(next((v for v in versions if v["version"] == version), current) if version else current)
            n, v = number, result["version"]
            slug = con.execute("SELECT slug FROM decisions WHERE number = ?", (n,)).fetchone()[0]
            result["path"] = f"docs/adr/{n:04d}-{slug}.md"
            result["links"] = _rows(con.execute(
                "SELECT l.constraint_id, l.relation, l.reason, l.constraint_version AS made_under FROM decision_constraints l "
                "WHERE l.number = ? AND l.version = ? ORDER BY l.position", (n, v)))
            result["changes"] = _rows(con.execute(
                "SELECT kind, other AS record FROM decision_relations WHERE number = ? AND version = ? ORDER BY other", (n, v)))
            result["changed_by"] = _rows(con.execute(
                "SELECT kind, number AS record FROM decision_relation_current WHERE other = ? ORDER BY number", (n,)))
            result["files"] = _rows(con.execute(
                "SELECT path, role FROM decision_files WHERE number = ? AND version = ? ORDER BY role, path", (n, v)))
            result["needs_review"] = _rows(con.execute(
                "SELECT constraint_id, made_under, current_version, change FROM needs_review WHERE number = ?", (n,)))
            result["reviews"] = _rows(con.execute(
                "SELECT constraint_id, constraint_version, note, reviewed_by, reviewed_at FROM decision_reviews "
                "WHERE number = ? ORDER BY reviewed_at", (n,)))
            result["history"] = [{k: x[k] for k in ("version", "lifecycle", "change_reason", "changed_by", "valid_from",
                                                     "valid_to", "end_reason")} for x in versions]
            if include_text:
                result["sections"] = _rows(con.execute(
                    "SELECT heading, body FROM decision_sections WHERE number = ? AND version = ? ORDER BY position", (n, v)))
            else:
                del result["notes"]
        return result

    @server.tool()
    def governing_records(path: str) -> dict:
        """The current decisions and items linked to a repository path (a file or a folder), for
        example "engineering_search/sql.py", and the decisions that reach it through those items.
        Call this before changing a file."""
        with connect() as con:
            decisions = {}
            for row in con.execute("SELECT f.number, f.path, f.role, d.title, d.status FROM decision_file_current f "
                                   "JOIN decision_current d ON d.number = f.number ORDER BY f.number"):
                if _covers(row["path"], path):
                    entry = decisions.setdefault(row["number"], {"number": row["number"], "title": row["title"],
                                                                 "status": row["status"], "links": []})
                    entry["links"].append({"path": row["path"], "role": row["role"]})
            constraints = [dict(row) for row in con.execute(
                "SELECT f.constraint_id, c.pillar, c.title, c.standing, f.path, f.role FROM constraint_file_current f "
                "JOIN constraint_current c ON c.id = f.constraint_id ORDER BY f.constraint_id")
                if _covers(row["path"], path)]
            for entry in decisions.values():
                for relation, name in (("serves", "serves"), ("exceeds", "exceeds_scope"), ("not met", "leaves_unmet")):
                    ids = [r[0] for r in con.execute(
                        "SELECT constraint_id FROM decision_constraint_current WHERE number = ? AND relation = ? "
                        "ORDER BY position", (entry["number"], relation))]
                    if ids or relation == "serves":
                        entry[name] = ids
            via = {}
            for c in constraints:
                for row in con.execute(
                        "SELECT d.number, d.title, d.status FROM decision_constraint_current l JOIN decision_current d "
                        "ON d.number = l.number WHERE l.constraint_id = ? AND l.relation != 'cites' "
                        "ORDER BY d.number", (c["constraint_id"],)):
                    if row["number"] not in decisions:
                        via.setdefault(row["number"], {**dict(row), "via": []})["via"].append(c["constraint_id"])
        return {"path": path, "decisions": list(decisions.values()), "constraints": constraints,
                "decisions_through_constraints": [via[n] for n in sorted(via)]}

    @server.tool()
    def search_records(text: str, limit: int = 20) -> dict:
        """Find current items and decisions whose words contain the text (case-insensitive)."""
        like = f"%{text.strip()}%"
        with connect() as con:
            constraints = _rows(con.execute(
                "SELECT id, pillar, title, standing FROM constraint_current WHERE title LIKE ?1 OR statement LIKE ?1 "
                "OR meaning LIKE ?1 OR mvp LIKE ?1 ORDER BY id LIMIT ?2", (like, limit)))
            decisions = _rows(con.execute(
                "SELECT DISTINCT d.number, d.title, d.status FROM decision_current d "
                "LEFT JOIN decision_section_current s ON s.number = d.number WHERE d.title LIKE ?1 OR d.summary LIKE ?1 "
                "OR d.notes LIKE ?1 OR s.body LIKE ?1 ORDER BY d.number LIMIT ?2", (like, limit)))
        return {"constraints": constraints, "decisions": decisions}

    @server.tool()
    def history(record: str = "", limit: int = 50) -> dict:
        """Every version of the records, newest first: when each was added, changed, displaced or
        withdrawn, why, and by whom. Pass an item ID ("U3") or a decision number ("18") for one record."""
        record = record.strip().upper()
        record = f"{int(record):04d}" if record.isdigit() else record
        with connect() as con:
            rows = _rows(con.execute(
                "SELECT * FROM history WHERE (?1 = '' OR id = ?1) ORDER BY coalesce(valid_from, '9999') DESC, kind, id, "
                "version DESC LIMIT ?2", (record, limit)))
        return {"versions": rows}

    @server.tool()
    def needs_review() -> dict:
        """Active decisions that link an item whose wording or meaning has changed since the decision
        was made (or that has been withdrawn), with no review. Each needs a review, or a new version."""
        with connect() as con:
            return {"needs_review": _rows(con.execute("SELECT * FROM needs_review ORDER BY number, constraint_id"))}

    @server.tool()
    def drafts() -> dict:
        """Draft versions waiting for a person to activate or discard them."""
        with connect() as con:
            return {"drafts": _rows(con.execute("SELECT * FROM drafts ORDER BY kind, id"))}

    @server.tool()
    def propose_change(kind: str, record: str, change_reason: str, changes: dict, changed_by: str = "agent") -> dict:
        """Propose a change to an existing item ("constraint", for example "R8") or decision ("decision",
        for example "18"). It becomes, or edits, the record's draft version; it is never activated
        here. `changes` maps fields to new text. Items: pillar, title, statement, meaning, standing,
        mvp, source_note. Decisions: title, summary, status, notes, implementation_summary, a section
        heading (Context, Decision, Consequences, Implementation), and "add_links": a list of
        {"constraint_id", "relation", "reason"} with relation serves, not met, exceeds or cites.
        A person reviews the draft, then activates it (docs/records/README.md)."""
        if not change_reason.strip():
            return {"error": "Say why in change_reason."}
        changes = dict(changes)
        con = records.connect(database, readonly=False)
        try:
            with con:
                if kind == "constraint":
                    key, table, where = record.strip().upper(), "constraint_versions", "constraint_id = ?"
                    allowed = CONSTRAINT_FIELDS
                elif kind == "decision":
                    key, table, where = int(record), "decision_versions", "number = ?"
                    allowed = DECISION_FIELDS
                else:
                    return {"error": "kind is constraint or decision"}
                sections = {h: changes.pop(h) for h in records.SECTION_HEADINGS if h in changes} if kind == "decision" else {}
                add_links = changes.pop("add_links", []) if kind == "decision" else []
                unknown = set(changes) - set(allowed)
                if unknown:
                    return {"error": f"Cannot change {sorted(unknown)}. Allowed: {list(allowed)}"
                                     + (f", {list(records.SECTION_HEADINGS)}, add_links" if kind == "decision" else "")}
                draft = con.execute(f"SELECT version FROM {table} WHERE {where} AND lifecycle = 'proposed'", (key,)).fetchone()
                if draft is None:
                    con.execute("INSERT INTO drafts (kind, id, change_reason, changed_by) VALUES (?, ?, ?, ?)",
                                (kind, str(key), change_reason, changed_by))
                    draft = con.execute(f"SELECT version FROM {table} WHERE {where} AND lifecycle = 'proposed'", (key,)).fetchone()
                version = draft[0]
                fields = {**changes, "change_reason": change_reason, "changed_by": changed_by}
                con.execute(f"UPDATE {table} SET {', '.join(f'{f} = ?' for f in fields)} WHERE {where} AND version = ?",
                            (*fields.values(), key, version))
                for heading, body in sections.items():
                    con.execute("UPDATE decision_sections SET body = ? WHERE number = ? AND version = ? AND heading = ?",
                                (body, key, version, heading))
                for i, link in enumerate(add_links):
                    con.execute("INSERT INTO decision_constraints (number, version, constraint_id, relation, position, reason) "
                                "VALUES (?, ?, ?, ?, (SELECT coalesce(max(position), 0) + 1 FROM decision_constraints "
                                "WHERE number = ? AND version = ?), ?)",
                                (key, version, link["constraint_id"].upper(), link["relation"], key, version, link.get("reason")))
        except (sqlite3.Error, ValueError, KeyError) as error:
            return {"error": str(error)}
        finally:
            con.close()
        return {"draft": {"kind": kind, "record": str(key), "version": version},
                "next": "A person reviews the draft and activates it, or discards it (docs/records/README.md)."}

    @server.tool()
    def check() -> dict:
        """Run the consistency check: generated files that differ from the database, files named in
        the database that do not exist, unlinked mentions, a changed brief or schema, broken links.
        Warnings list drafts, decisions that need review, and scope items not met."""
        with connect() as con:
            found = records.check(con)
            warnings = records.warnings(con)
        return {"ok": not found, "problems": found, "warnings": warnings}

    @server.tool()
    def query_records(sql: str) -> dict:
        """Run one read-only SQL statement on the records database (at most 200 rows). Current views:
        constraint_current, decision_current, decision_section_current, decision_constraint_current,
        decision_relation_current, decision_file_current, constraint_file_current. Also: history,
        needs_review, drafts, reviews, and the tables constraint_versions, decision_versions, … (see
        design_records/schema.sql)."""
        try:
            with connect() as con:
                cursor = con.execute(sql)
                columns = [c[0] for c in cursor.description or []]
                rows = [list(r) for r in cursor.fetchmany(ROW_LIMIT + 1)]
        except sqlite3.Error as error:
            return {"error": str(error)}
        return {"columns": columns, "rows": rows[:ROW_LIMIT], "truncated": len(rows) > ROW_LIMIT}

    return server


def main() -> None:
    create_server().run()
