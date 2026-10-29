"""Constrained SQL over the structured data that one user may read.

An MCP client (Claude Code, Codex, Pi) answers a structured question such as
"Which S355 components have an allowable load under 5 kN/m²?" by writing a
SELECT statement. The statement runs here, against a projection: a fresh
in-memory SQLite database built for that one request, holding only the rows
of files that the user may read. Permissions are applied when the projection
is built, before any WHERE, JOIN, ORDER BY, LIMIT, COUNT or aggregate runs, so
a query cannot see, count or join a forbidden row.

Defences on top of the projection:
  - one statement, SELECT only (an authoriser allows reads of the projection
    tables and a list of plain functions; it denies everything else);
  - PRAGMA query_only, so even an allowed statement cannot write;
  - a step budget (progress handler), so a runaway query stops;
  - a row limit and a statement length limit.

Tables (see SCHEMA for every column):
  documents   one row per readable file
  facts       typed values from table cells, with subject, parameter, role, SI value
  components  one row per table row that has facts: grade, loads (kN/m²), status
  table_rows  every table row, with its original cells as JSON
  source_tables  every table, with its column names as JSON
Every row carries file_id with line and page, so each answer can be cited.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Iterable

MAX_SQL_CHARACTERS = 4000
MAX_ROWS = 500
STEP_BUDGET = 2_000_000          # SQLite VM steps, checked every 1000
DEFAULT_ROWS = 100

SCHEMA = {
    "documents": {
        "description": "One row per file that the user may read and that is in the index.",
        "columns": {
            "file_id": "TEXT. Path of the file in the document repository, e.g. 'project-harbour/x.csv'.",
            "project": "TEXT. Project from the top folder 'project-<name>' (e.g. 'Harbour'), else NULL.",
            "folder": "TEXT. Top folder of the file.",
            "file_type": "TEXT. markdown, pdf, csv or excel.",
            "source_version": "TEXT. SHA-256 of the file content that was read.",
            "passages": "INTEGER. Number of text passages read from the file.",
        },
    },
    "facts": {
        "description": "Typed values read from table cells by fixed rules at index time. "
                       "One row per cell. Never from free text.",
        "columns": {
            "file_id": "TEXT. The file the value is in.",
            "table_no": "INTEGER. Table number in the file (1-based).",
            "row_no": "INTEGER. Data row number in the table (1-based).",
            "line": "INTEGER. Line of the row in the file (sheet row for a workbook).",
            "page": "INTEGER. PDF page, or sheet number for a workbook; NULL for text files.",
            "column_name": "TEXT. The original column header (or row label in a key-value table).",
            "subject": "TEXT. What the row is about, e.g. a component mark 'B-104'.",
            "parameter": "TEXT. material_grade, allowable_distributed_load, load_capacity, roof_imposed_load, "
                         "imposed_load, applied_load, settlement, deflection, compliance_status, or the "
                         "column name for other quantities.",
            "role": "TEXT. capacity, demand, specification, status, measurement or unknown. "
                    "Never compare a capacity with a demand.",
            "value": "TEXT. The cell as written, e.g. 'S355J2' or '4.5'.",
            "number": "REAL. The parsed number, with its sign, in the original unit.",
            "unit": "TEXT. The original unit, e.g. 'kN/m²'.",
            "si_value": "REAL. The number in SI: pressure in Pa (5 kN/m² = 5000), length in m, force in N.",
            "dimension": "TEXT. pressure, line load, force, mass or length.",
            "project": "TEXT. The project of the row: from a Project column if the table has one, "
                       "else from the file's folder; NULL if neither.",
            "project_source": "TEXT. 'row', 'folder' or NULL.",
        },
    },
    "components": {
        "description": "View: one row per table row that has facts, with the common parameters as columns. "
                       "Loads are in kN/m². Use this for questions about components.",
        "columns": {
            "file_id": "TEXT.", "table_no": "INTEGER.", "row_no": "INTEGER.", "line": "INTEGER.", "page": "INTEGER.",
            "subject": "TEXT. Component mark or row subject.",
            "project": "TEXT. As in facts.project.",
            "material_grade": "TEXT. e.g. 'S355J2+N', 'C30/37'. Match S355 with LIKE 'S355%'.",
            "allowable_load_kn_m2": "REAL. Allowable distributed load (a capacity), kN/m².",
            "imposed_load_kn_m2": "REAL. Imposed load (a demand), kN/m², roof or other.",
            "compliance_status": "TEXT. As written, e.g. 'Approved', 'Pending'.",
        },
    },
    "table_rows": {
        "description": "Every row of every table, with its original cells.",
        "columns": {
            "file_id": "TEXT.", "table_no": "INTEGER.", "row_no": "INTEGER.", "line": "INTEGER.", "page": "INTEGER.",
            "cells_json": "TEXT. JSON array of the cell texts; read one with json_extract(cells_json, '$[0]').",
        },
    },
    "source_tables": {
        "description": "Every table: its name (heading or sheet) and column headers.",
        "columns": {
            "file_id": "TEXT.", "table_no": "INTEGER.", "name": "TEXT.",
            "columns_json": "TEXT. JSON array of the column headers.",
        },
    },
}

DDL = """
CREATE TABLE documents (file_id TEXT PRIMARY KEY, project TEXT, folder TEXT, file_type TEXT,
                        source_version TEXT, passages INTEGER);
CREATE TABLE source_tables (file_id TEXT, table_no INTEGER, name TEXT, columns_json TEXT);
CREATE TABLE table_rows (file_id TEXT, table_no INTEGER, row_no INTEGER, line INTEGER, page INTEGER,
                         cells_json TEXT);
CREATE TABLE facts (file_id TEXT, table_no INTEGER, row_no INTEGER, line INTEGER, page INTEGER,
                    column_name TEXT, subject TEXT, parameter TEXT, role TEXT, value TEXT, number REAL,
                    unit TEXT, si_value REAL, dimension TEXT, project TEXT, project_source TEXT);
CREATE VIEW components AS
SELECT file_id, table_no, row_no, line, page,
       MAX(subject) AS subject, MAX(project) AS project,
       MAX(CASE WHEN parameter = 'material_grade' THEN value END) AS material_grade,
       MAX(CASE WHEN parameter = 'allowable_distributed_load' THEN si_value / 1000.0 END) AS allowable_load_kn_m2,
       MAX(CASE WHEN parameter IN ('imposed_load', 'roof_imposed_load') THEN si_value / 1000.0 END)
           AS imposed_load_kn_m2,
       MAX(CASE WHEN parameter = 'compliance_status' THEN value END) AS compliance_status
FROM facts GROUP BY file_id, table_no, row_no;
"""

TABLES = set(SCHEMA)
FUNCTIONS = {"count", "sum", "avg", "min", "max", "total", "group_concat", "lower", "upper", "length",
             "substr", "substring", "instr", "trim", "ltrim", "rtrim", "replace", "coalesce", "ifnull",
             "nullif", "round", "abs", "like", "glob", "json_extract", "json_array_length", "printf",
             "cast", "iif", "typeof"}


class SqlError(ValueError):
    """The statement was refused or failed. The message is safe to show to the client."""


def project_of(folder: str) -> str | None:
    """'project-harbour' -> 'Harbour'"""
    match = re.fullmatch(r"project-(.+)", folder)
    return match.group(1).replace("-", " ").title() if match else None


class Projection:
    """A read-only in-memory database with the structured rows of the given files only."""

    def __init__(self, structured: dict[str, list[tuple]], file_types: dict[str, str]):
        self._db = sqlite3.connect(":memory:")
        self._db.executescript(DDL)
        lines = {(r[0], r[1], r[2]): (r[3], r[4]) for r in structured["rows"]}
        folders = {}
        for file_id, version, passages in structured["documents"]:
            folder = file_id.split("/")[0] if "/" in file_id else ""
            folders[file_id] = folder
            self._db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                             (file_id, project_of(folder), folder, file_types.get(file_id), version, passages))
        self._db.executemany("INSERT INTO source_tables VALUES (?, ?, ?, ?)", structured["tables"])
        self._db.executemany("INSERT INTO table_rows VALUES (?, ?, ?, ?, ?, ?)", structured["rows"])
        facts = []
        for (file_id, table_no, row_no, column, subject, parameter, role, value, number, unit, si_value,
             dimension, row_project) in structured["facts"]:
            line, page = lines.get((file_id, table_no, row_no), (None, None))
            folder_project = project_of(folders.get(file_id, ""))
            project, source = ((row_project, "row") if row_project else
                               (folder_project, "folder") if folder_project else (None, None))
            facts.append((file_id, table_no, row_no, line, page, column, subject, parameter, role, value,
                          number, unit, si_value, dimension, project, source))
        self._db.executemany("INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", facts)
        self._db.commit()
        self._db.execute("PRAGMA query_only = ON")
        self._db.set_authorizer(self._authorise)
        self._steps = 0
        self._db.set_progress_handler(self._count_steps, 1000)

    def _authorise(self, action, arg1, arg2, database, trigger_or_view):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and (arg1 in TABLES or arg1 in ("sqlite_master", "sqlite_schema")):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and arg2 and arg2.lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    def _count_steps(self):
        self._steps += 1000
        return 1 if self._steps > STEP_BUDGET else 0  # non-zero aborts the statement

    def counts(self) -> dict[str, int]:
        return {name: self._db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in sorted(TABLES)}

    def query(self, sql: str, params: Iterable = (), limit: int = DEFAULT_ROWS) -> dict:
        sql = sql.strip().rstrip(";").strip()
        if not sql:
            raise SqlError("Empty statement")
        if len(sql) > MAX_SQL_CHARACTERS:
            raise SqlError(f"Statement longer than {MAX_SQL_CHARACTERS} characters")
        if not re.match(r"(?is)^(select|with)\b", sql):
            raise SqlError("Only a single SELECT statement is allowed")
        limit = max(1, min(int(limit), MAX_ROWS))
        self._steps = 0
        try:
            cursor = self._db.execute(sql, tuple(params))
            rows = cursor.fetchmany(limit + 1)
        except sqlite3.DatabaseError as error:
            if self._steps > STEP_BUDGET:
                raise SqlError("The query took too long and was stopped; narrow it") from None
            message = str(error)
            if "not authorized" in message or "prohibited" in message:
                message = ("Not allowed: only SELECT on documents, facts, components, table_rows and "
                           "source_tables, with plain functions")
            raise SqlError(message[:300]) from None
        except sqlite3.Warning as error:  # "You can only execute one statement at a time."
            raise SqlError(str(error)[:300]) from None
        columns = [d[0] for d in cursor.description or ()]
        return {"columns": columns, "rows": [list(r) for r in rows[:limit]],
                "row_count": min(len(rows), limit), "truncated": len(rows) > limit}

    def close(self) -> None:
        self._db.close()


def describe(table: str | None = None) -> dict:
    """The schema for clients: every table, or one."""
    if table is None:
        return {"tables": {name: spec["description"] for name, spec in SCHEMA.items()},
                "notes": ["Only SELECT. Only rows from files you may read are present.",
                          "Each row has file_id with line and page: cite them, or call get_document_evidence.",
                          "Loads: facts.si_value is in Pa (5 kN/m² = 5000); components loads are in kN/m².",
                          "Capacity (allowable) and demand (imposed) are different parameters."]}
    if table not in SCHEMA:
        raise SqlError(f"Unknown table {table!r}; tables are {', '.join(SCHEMA)}")
    return {"table": table, **SCHEMA[table]}
