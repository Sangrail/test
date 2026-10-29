from __future__ import annotations

from collections import deque
import fcntl
import json
import math
from pathlib import Path
import sqlite3
import statistics
import threading
from threading import Lock


class FileLock:
    """A lock that other processes see: the web server and each MCP server can share
    one index file, so only one of them may plan and publish index changes at a time.

    Each acquire opens its own file descriptor, so threads also exclude each other."""
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._held = threading.local()

    def __enter__(self):
        stream = self.path.open("a")
        fcntl.flock(stream, fcntl.LOCK_EX)
        self._held.stream = stream
        return self

    def __exit__(self, *exc) -> None:
        stream = self._held.stream
        fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()


class SQLiteAuditStore:
    """Local durable prototype log; not a tamper-proof production audit service."""
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        db = self._connect()
        try:
            with db:
                db.execute("CREATE TABLE IF NOT EXISTS events "
                           "(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        finally:
            db.close()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def append(self, event: dict) -> None:
        db = self._connect()
        try:
            with db:
                db.execute("INSERT INTO events(payload) VALUES (?)",
                           (json.dumps(event, sort_keys=True),))
        finally:
            db.close()

    def read_page(self, page: int, limit: int, snapshot_id: int | None = None) -> dict:
        db = self._connect()
        try:
            # Count and page share a read snapshot; later pages reuse its upper ID.
            db.execute("BEGIN")
            maximum = db.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]
            boundary = maximum if snapshot_id is None else min(snapshot_id, maximum)
            total = db.execute("SELECT COUNT(*) FROM events WHERE id <= ?", (boundary,)).fetchone()[0]
            rows = db.execute("SELECT id, payload FROM events WHERE id <= ? ORDER BY id DESC LIMIT ? OFFSET ?",
                              (boundary, limit, (page - 1) * limit)).fetchall()
            pages = (total + limit - 1) // limit
            return {"events": [{"id": identity, "payload": json.loads(payload)} for identity, payload in rows],
                    "page": page, "limit": limit, "total_events": total, "total_pages": pages,
                    "snapshot_id": boundary, "sort": "recorded_desc",
                    "has_next": page < pages, "has_previous": page > 1 and total > 0}
        finally:
            db.close()


class Telemetry:
    def __init__(self) -> None:
        self.lock = Lock()
        self.queries: deque[tuple[float, int]] = deque(maxlen=10000)
        self.stages: deque[dict] = deque(maxlen=10000)
        self.index_runs: deque[dict] = deque(maxlen=100)
        self.counters = {"queries_total": 0, "query_errors_total": 0,
                         "audit_failures_total": 0, "index_failures_total": 0,
                         "response_completion_audit_failures_total": 0}

    def increment(self, name: str) -> None:
        with self.lock:
            self.counters[name] += 1

    def query(self, elapsed_ms: float, status: int) -> None:
        with self.lock:
            self.queries.append((elapsed_ms, status))
            self.counters["queries_total"] += 1
            if status >= 400:
                self.counters["query_errors_total"] += 1

    def record_stages(self, data: dict) -> None:
        with self.lock:
            self.stages.append(data)

    def record_index(self, data: dict) -> None:
        with self.lock:
            self.index_runs.append(data)

    def snapshot(self) -> dict:
        with self.lock:
            values = sorted(v for v, _ in self.queries)
            return {
                "window": "Last 10000 queries and 100 indexing runs, since process start",
                "query_timer": "Server request receipt through response send; excludes client network time",
                "query_ms": {"count": len(values),
                             "min": min(values) if values else None,
                             "max": max(values) if values else None,
                             "median": statistics.median(values) if values else None,
                             "average": statistics.mean(values) if values else None,
                             "p95": values[math.ceil(len(values) * .95) - 1] if values else None},
                "counters": dict(self.counters),
                "recent_search_stages": list(self.stages)[-20:],
                "index_runs": list(self.index_runs),
            }
