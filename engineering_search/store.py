"""SQLite store for documents and passages, with an FTS5 inverted index.

One file (or memory) holds:
  documents     one row per source file and version
  passages      the verbatim passages returned as evidence
  passages_fts  FTS5 inverted index over heading, text and file name

A search looks words up in the inverted index. It never scans passage text.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from threading import RLock

from .core import Document, Passage
from .query import QueryPlan, plan

# Most passages a single query ranks, after the permission and scope filter.
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

    def apply(self, upserts: list[Document], removals: list[str]) -> None:
        """Publish all changes in one transaction, or none of them."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                for file_id in removals:
                    self._delete(file_id)
                for document in upserts:
                    self._delete(document.file_id)
                    self._insert(document)
                self._db.execute("INSERT OR REPLACE INTO meta VALUES ('indexed_at', ?)",
                                 (datetime.now(timezone.utc).isoformat(),))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def upsert(self, document: Document) -> None:
        self.apply([document], [])

    def remove(self, file_id: str) -> None:
        self.apply([], [file_id])

    # Reads ------------------------------------------------------------------

    def versions(self) -> dict[str, str]:
        with self._lock:
            return dict(self._db.execute("SELECT file_id, source_version FROM documents"))

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

        `files` is applied inside the index query, before the CANDIDATE_LIMIT, so
        passages outside it can never push the passages inside it out of the result.
        Rank: passages that contain more of the query words first, then BM25.
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
            ranked = self._db.execute(
                "SELECT rowid, bm25(passages_fts, ?, ?, ?) FROM passages_fts"
                f" WHERE passages_fts MATCH ?{scope} ORDER BY 2 LIMIT ?",
                (*WEIGHTS, query_plan.fts(), CANDIDATE_LIMIT)).fetchall()
            if not ranked:
                return []
            # Count how many query words each passage contains. Each count is
            # one more index lookup per word, not a scan.
            coverage = dict.fromkeys((rowid for rowid, _ in ranked), 0)
            marks = ",".join("?" * len(coverage))
            if len(query_plan.terms) > 1:
                for term in query_plan.terms:
                    for (rowid,) in self._db.execute(
                            f"SELECT rowid FROM passages_fts WHERE passages_fts MATCH ? AND rowid IN ({marks})",
                            (term.fts(), *coverage)):
                        coverage[rowid] += 1
            rows = {row[0]: row for row in self._db.execute(
                "SELECT id, file_id, source_version, heading, start_line, end_line, text, page"
                f" FROM passages WHERE id IN ({marks})", list(coverage))}
        order = sorted(ranked, key=lambda r: (-coverage[r[0]], r[1], rows[r[0]][1], rows[r[0]][4]))
        return [Passage(*rows[rowid][1:]) for rowid, _ in order]

    def search(self, query: str, limit: int) -> tuple[list[Passage], int]:
        passages = self.candidates(query)
        return passages[:limit], len(passages)
