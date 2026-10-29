"""A read-only MCP server over the design records, for agents working on this project.

Before changing the design or the code, an agent can ask which decisions and constraints
govern a file, read a decision with its links, search the records, run the consistency
check, or query the database with read-only SQL. It never writes: changes go through the
database and `python -m design_records generate`, so the check sees them.

    uv run --frozen python -m design_records mcp
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import records

INSTRUCTIONS = """The design records of this project: the brief, the constraints (background B,
constraints from the brief C, use case U, task T, scope S, requirements added during the MVP R,
production requirements P) and the architecture decision records (ADRs), with links between them
and to the files that implement, test or stand in for them.

Use them during development:
- Before changing a file, call governing_records with its path, and read the decisions it returns.
- Before a design decision, search the records and read the constraints it touches.
- A change that conflicts with an accepted decision needs a new decision record, not a quiet edit.
- The records are read-only here. To change them, edit design/records/records.sqlite and run
  `uv run --frozen python -m design_records generate`; then call check.
Constraints with standing "assumed" exist in the company already (for example the connectors, C3);
the MVP only uses stand-ins for them."""

ROW_LIMIT = 200


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
        """Every constraint group with its constraints (ID, title, standing), and every decision
        (number, title, status). Start here."""
        with connect() as con:
            groups = _rows(con.execute("SELECT code, name, summary FROM constraint_groups ORDER BY position"))
            for group in groups:
                group["constraints"] = _rows(con.execute(
                    "SELECT id, title, standing FROM constraints WHERE group_code = ? ORDER BY position", (group["code"],)))
            decisions = _rows(con.execute("SELECT number, title, status FROM decisions ORDER BY number"))
        return {"constraint_groups": groups, "decisions": decisions}

    @server.tool()
    def get_constraint(constraint_id: str) -> dict:
        """One constraint (for example "U3" or "C3"): its statement, source, standing, what it means
        for the design, where the MVP stands, the decisions linked to it and its files."""
        with connect() as con:
            row = con.execute("SELECT * FROM constraints WHERE id = ?", (constraint_id.strip().upper(),)).fetchone()
            if row is None:
                return {"error": f"No constraint {constraint_id}. Call overview for the IDs."}
            result = dict(row)
            result["decisions"] = _rows(con.execute(
                "SELECT d.number, d.title, d.status, dc.relation, dc.reason FROM decision_constraints dc "
                "JOIN decisions d ON d.number = dc.number WHERE dc.constraint_id = ? ORDER BY d.number", (row["id"],)))
            result["files"] = _rows(con.execute(
                "SELECT path, role FROM constraint_files WHERE constraint_id = ? ORDER BY role, path", (row["id"],)))
        return result

    @server.tool()
    def get_decision(number: int, include_text: bool = True) -> dict:
        """One decision record by number: status, the constraints it serves, leaves unmet or cites
        (with reasons), the records it supersedes or amends and those that supersede or amend it,
        its files, and (by default) its notes and sections."""
        with connect() as con:
            row = con.execute("SELECT * FROM decisions WHERE number = ?", (number,)).fetchone()
            if row is None:
                return {"error": f"No decision {number}. Call overview for the numbers."}
            result = dict(row)
            result["path"] = f"docs/adr/{records.adr_file(row)}"
            result["constraints"] = _rows(con.execute(
                "SELECT dc.constraint_id, c.title, dc.relation, dc.reason FROM decision_constraints dc "
                "JOIN constraints c ON c.id = dc.constraint_id WHERE dc.number = ? ORDER BY dc.position", (number,)))
            result["changes"] = _rows(con.execute(
                "SELECT kind, other AS record FROM decision_relations WHERE number = ? ORDER BY other", (number,)))
            result["changed_by"] = _rows(con.execute(
                "SELECT kind, number AS record FROM decision_relations WHERE other = ? ORDER BY number", (number,)))
            result["files"] = _rows(con.execute(
                "SELECT path, role FROM decision_files WHERE number = ? ORDER BY role, path", (number,)))
            if include_text:
                result["sections"] = _rows(con.execute(
                    "SELECT heading, body FROM decision_sections WHERE number = ? ORDER BY position", (number,)))
            else:
                del result["notes"]
        return result

    @server.tool()
    def governing_records(path: str) -> dict:
        """The decisions and constraints linked to a repository path (a file or a folder), for
        example "engineering_search/sql.py". Call this before changing a file."""
        with connect() as con:
            decisions = {}
            for row in con.execute("SELECT f.number, f.path, f.role, d.title, d.status FROM decision_files f "
                                   "JOIN decisions d ON d.number = f.number ORDER BY f.number"):
                if _covers(row["path"], path):
                    entry = decisions.setdefault(row["number"], {"number": row["number"], "title": row["title"],
                                                                 "status": row["status"], "links": []})
                    entry["links"].append({"path": row["path"], "role": row["role"]})
            constraints = [dict(row) for row in con.execute(
                "SELECT f.constraint_id, c.title, c.standing, f.path, f.role FROM constraint_files f "
                "JOIN constraints c ON c.id = f.constraint_id ORDER BY f.constraint_id")
                if _covers(row["path"], path)]
            for entry in decisions.values():
                entry["serves"] = [r[0] for r in con.execute(
                    "SELECT constraint_id FROM decision_constraints WHERE number = ? AND relation = 'serves' "
                    "ORDER BY position", (entry["number"],))]
            via = {}
            for c in constraints:
                for row in con.execute(
                        "SELECT d.number, d.title, d.status FROM decision_constraints dc JOIN decisions d "
                        "ON d.number = dc.number WHERE dc.constraint_id = ? AND dc.relation != 'cites' "
                        "ORDER BY d.number", (c["constraint_id"],)):
                    if row["number"] not in decisions:
                        via.setdefault(row["number"], {**dict(row), "via": []})["via"].append(c["constraint_id"])
        return {"path": path, "decisions": list(decisions.values()), "constraints": constraints,
                "decisions_through_constraints": [via[n] for n in sorted(via)]}

    @server.tool()
    def search_records(text: str, limit: int = 20) -> dict:
        """Find constraints and decisions whose words contain the text (case-insensitive)."""
        like = f"%{text.strip()}%"
        with connect() as con:
            constraints = _rows(con.execute(
                "SELECT id, title, standing FROM constraints WHERE title LIKE ?1 OR statement LIKE ?1 "
                "OR meaning LIKE ?1 OR mvp LIKE ?1 ORDER BY id LIMIT ?2", (like, limit)))
            decisions = _rows(con.execute(
                "SELECT DISTINCT d.number, d.title, d.status FROM decisions d "
                "LEFT JOIN decision_sections s ON s.number = d.number WHERE d.title LIKE ?1 OR d.summary LIKE ?1 "
                "OR d.notes LIKE ?1 OR s.body LIKE ?1 ORDER BY d.number LIMIT ?2", (like, limit)))
        return {"constraints": constraints, "decisions": decisions}

    @server.tool()
    def check() -> dict:
        """Run the consistency check: generated pages that differ from the database, files named
        in the database that do not exist, unlinked mentions, a changed brief, broken links."""
        with connect() as con:
            found = records.check(con)
        return {"ok": not found, "problems": found}

    @server.tool()
    def query_records(sql: str) -> dict:
        """Run one read-only SQL statement on the records database (at most 200 rows). Tables:
        sources, brief_sections, constraint_groups, constraints, decisions, decision_sections,
        decision_constraints, decision_relations, decision_files, constraint_files."""
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
