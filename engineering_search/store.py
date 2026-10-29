"""SQLite store for documents and passages, with an FTS5 inverted index.

One file (or memory) holds:
  documents     one row per source file and version
  passages      the verbatim passages returned as evidence
  passages_fts  FTS5 inverted index over heading, text and file name
  files         the last published inventory: every file found, with its status (JSON)
  source_tables, table_rows, facts
                tables read from documents, their rows, and typed facts from the rows

A search looks words up in the inverted index. It never scans passage text.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from threading import RLock

from .core import Document, Passage
from .query import QueryPlan, plan

# Most passages a single query returns, after the permission and scope filter.
CANDIDATE_LIMIT = 1000

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
    file_id TEXT PRIMARY KEY,
    source_version TEXT NOT NULL,
    passages INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY,
    file_id TEXT NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    source_version TEXT NOT NULL,
    heading TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    page INTEGER,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS passages_by_file ON passages(file_id);
CREATE TABLE IF NOT EXISTS files (file_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_tables (
    file_id TEXT NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    table_no INTEGER NOT NULL,
    name TEXT NOT NULL,
    columns TEXT NOT NULL,
    PRIMARY KEY (file_id, table_no)
);
CREATE TABLE IF NOT EXISTS table_rows (
    file_id TEXT NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    table_no INTEGER NOT NULL,
    row_no INTEGER NOT NULL,
    line INTEGER NOT NULL,
    page INTEGER,
    cells TEXT NOT NULL,
    PRIMARY KEY (file_id, table_no, row_no)
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    file_id TEXT NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    table_no INTEGER NOT NULL,
    row_no INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    parameter TEXT NOT NULL,
    role TEXT NOT NULL,
    value TEXT NOT NULL,
    number REAL,
    unit TEXT,
    si_value REAL,
    dimension TEXT,
    project TEXT
);
CREATE INDEX IF NOT EXISTS facts_by_file ON facts(file_id);
CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
    heading, text, source, tokenize = 'porter unicode61');
"""

# Column weights for BM25: heading, text, file name.
WEIGHTS = (3.0, 1.0, 0.5)


def source_words(file_id: str) -> str:
    """'project-northgate/northgate-warehouse.pdf' -> 'project northgate northgate warehouse'"""
    return " ".join(re.findall(r"[^\W_]+", file_id.rsplit(".", 1)[0]))


class SQLiteSearchIndex:
    """Thread-safe. Pass a file path to keep the index between restarts."""

    def __init__(self, path: Path | str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._lock = RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=30)
        self._db.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(SCHEMA)

    # Writes -----------------------------------------------------------------

    def _delete(self, file_id: str) -> None:
        rows = self._db.execute("SELECT id FROM passages WHERE file_id = ?", (file_id,)).fetchall()
        self._db.executemany("DELETE FROM passages_fts WHERE rowid = ?", rows)
        self._db.execute("DELETE FROM documents WHERE file_id = ?", (file_id,))

    def _insert(self, document: Document) -> None:
        self._db.execute("INSERT INTO documents VALUES (?, ?, ?)",
                         (document.file_id, document.source_version, len(document.passages)))
        source = source_words(document.file_id)
        for p in document.passages:
            rowid = self._db.execute(
                "INSERT INTO passages (file_id, source_version, heading, start_line, end_line, page, text)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p.file_id, p.source_version, p.heading, p.start_line, p.end_line, p.page, p.text)).lastrowid
            self._db.execute("INSERT INTO passages_fts (rowid, heading, text, source) VALUES (?, ?, ?, ?)",
                             (rowid, p.heading, p.text, source))
        for t in document.tables:
            self._db.execute("INSERT INTO source_tables VALUES (?, ?, ?, ?)",
                             (document.file_id, t.table, t.name, json.dumps(t.columns)))
            self._db.executemany("INSERT INTO table_rows VALUES (?, ?, ?, ?, ?, ?)",
                                 [(document.file_id, t.table, r.row, r.line, r.page, json.dumps(r.cells))
                                  for r in t.rows])
        self._db.executemany(
            "INSERT INTO facts (file_id, table_no, row_no, column_name, subject, parameter, role, value,"
            " number, unit, si_value, dimension, project) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(document.file_id, f.table, f.row, f.column, f.subject, f.parameter, f.role, f.value,
              f.number, f.unit, f.si_value, f.dimension, f.project) for f in document.facts])

    def apply(self, upserts: list[Document], removals: list[str], files: list[dict] | None = None) -> None:
        """Publish all changes in one transaction, or none of them.

        files, if given, replaces the stored inventory (one dict per file, with a "file_id").
        """
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                for file_id in removals:
                    self._delete(file_id)
                for document in upserts:
                    self._delete(document.file_id)
                    self._insert(document)
                if files is not None:
                    self._db.execute("DELETE FROM files")
                    self._db.executemany("INSERT OR REPLACE INTO files VALUES (?, ?)",
                                         [(f["file_id"], json.dumps(f, sort_keys=True)) for f in files])
                self._db.execute("INSERT OR REPLACE INTO meta VALUES ('indexed_at', ?)",
                                 (datetime.now(timezone.utc).isoformat(),))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def remove(self, file_id: str) -> None:
        self.apply([], [file_id])

    # Reads ------------------------------------------------------------------

    def versions(self) -> dict[str, str]:
        with self._lock:
            return dict(self._db.execute("SELECT file_id, source_version FROM documents"))

    def structured(self, files: set[str]) -> dict[str, list[tuple]]:
        """The tables, rows and facts of `files` only, as rows for a projection.

        Keys and columns:
          documents  (file_id, source_version, passages)
          tables     (file_id, table_no, name, columns_json)
          rows       (file_id, table_no, row_no, line, page, cells_json)
          facts      (file_id, table_no, row_no, column_name, subject, parameter, role, value,
                      number, unit, si_value, dimension, project)
        """
        queries = {
            "documents": "SELECT d.file_id, d.source_version, d.passages FROM documents d",
            "tables": "SELECT d.file_id, d.table_no, d.name, d.columns FROM source_tables d",
            "rows": "SELECT d.file_id, d.table_no, d.row_no, d.line, d.page, d.cells FROM table_rows d",
            "facts": "SELECT d.file_id, d.table_no, d.row_no, d.column_name, d.subject, d.parameter, d.role,"
                     " d.value, d.number, d.unit, d.si_value, d.dimension, d.project FROM facts d",
        }
        if not files:
            return {name: [] for name in queries}
        with self._lock:
            self._db.execute("CREATE TEMP TABLE IF NOT EXISTS scope (file_id TEXT PRIMARY KEY)")
            self._db.execute("DELETE FROM temp.scope")
            self._db.executemany("INSERT INTO temp.scope VALUES (?)", [(f,) for f in files])
            return {name: self._db.execute(f"{sql} JOIN temp.scope s ON s.file_id = d.file_id"
                                           " ORDER BY 1, 2, 3").fetchall()
                    for name, sql in queries.items()}

    def files(self) -> list[dict]:
        """The last published inventory."""
        with self._lock:
            return [json.loads(record) for (record,) in self._db.execute("SELECT record FROM files ORDER BY file_id")]

    def passage_count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT count(*) FROM passages").fetchone()[0]

    def indexed_at(self) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE key = 'indexed_at'").fetchone()
            return row[0] if row else None

    def passages(self, file_id: str, page: int | None = None) -> list[Passage]:
        """All passages of one file (or one PDF page), in reading order."""
        with self._lock:
            rows = self._db.execute(
                "SELECT file_id, source_version, heading, start_line, end_line, text, page FROM passages"
                " WHERE file_id = ? AND (? IS NULL OR page = ?) ORDER BY id", (file_id, page, page))
            return [Passage(*row) for row in rows]

    def document_matches(self, query_plan: QueryPlan) -> dict[str, int]:
        """For each document, how many query terms it contains anywhere (text, heading or file name)."""
        counts: dict[str, int] = {}
        with self._lock:
            for term in query_plan.terms:
                for (file_id,) in self._db.execute(
                        "SELECT DISTINCT p.file_id FROM passages_fts JOIN passages p ON p.id = passages_fts.rowid"
                        " WHERE passages_fts MATCH ?", (term.fts(),)):
                    counts[file_id] = counts.get(file_id, 0) + 1
        return counts

    def candidates(self, query: str | QueryPlan, files: set[str] | None = None) -> list[Passage]:
        """Passages that contain any query word, best first, from `files` only (None: all files).

        Rank: passages that contain more of the query words first, then BM25. The
        BM25 statistics (how common each word is, how long passages are) come from
        the passages in `files` that match the query, copied into a temporary index,
        never from the whole index: a forbidden file must not change the order of a
        user's results (K13, ADR 0004). The copy costs time in proportion to the
        number of permitted matches. CANDIDATE_LIMIT applies after the ranking.
        """
        query_plan = plan(query) if isinstance(query, str) else query
        if not query_plan.terms or files is not None and not files:
            return []
        with self._lock:
            scope = ""
            if files is not None:
                self._db.execute("CREATE TEMP TABLE IF NOT EXISTS scope (file_id TEXT PRIMARY KEY)")
                self._db.execute("DELETE FROM temp.scope")
                self._db.executemany("INSERT INTO temp.scope VALUES (?)", [(f,) for f in files])
                scope = (" AND rowid IN (SELECT p.id FROM passages p"
                         " JOIN temp.scope s ON s.file_id = p.file_id)")
            self._db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.ranking USING fts5("
                             "heading, text, source, tokenize = 'porter unicode61')")
            self._db.execute("DELETE FROM temp.ranking")
            self._db.execute("INSERT INTO temp.ranking (rowid, heading, text, source)"
                             f" SELECT rowid, heading, text, source FROM passages_fts WHERE passages_fts MATCH ?{scope}",
                             (query_plan.fts(),))
            ranked = self._db.execute("SELECT rowid, bm25(ranking, ?, ?, ?) FROM temp.ranking WHERE ranking MATCH ?",
                                      (*WEIGHTS, query_plan.fts())).fetchall()
            if not ranked:
                return []
            # Count how many query words each passage contains: one lookup per word.
            coverage = dict.fromkeys((rowid for rowid, _ in ranked), 0)
            if len(query_plan.terms) > 1:
                for term in query_plan.terms:
                    for (rowid,) in self._db.execute("SELECT rowid FROM temp.ranking WHERE ranking MATCH ?",
                                                     (term.fts(),)):
                        coverage[rowid] += 1
            self._db.execute("CREATE TEMP TABLE IF NOT EXISTS ranked (id INTEGER PRIMARY KEY)")
            self._db.execute("DELETE FROM temp.ranked")
            self._db.executemany("INSERT INTO temp.ranked VALUES (?)", [(rowid,) for rowid in coverage])
            rows = {row[0]: row for row in self._db.execute(
                "SELECT p.id, p.file_id, p.source_version, p.heading, p.start_line, p.end_line, p.text, p.page"
                " FROM passages p JOIN temp.ranked r ON r.id = p.id")}
        order = sorted(ranked, key=lambda r: (-coverage[r[0]], r[1], rows[r[0]][1], rows[r[0]][4]))
        return [Passage(*rows[rowid][1:]) for rowid, _ in order[:CANDIDATE_LIMIT]]

    def search(self, query: str, limit: int) -> tuple[list[Passage], int]:
        passages = self.candidates(query)
        return passages[:limit], len(passages)
