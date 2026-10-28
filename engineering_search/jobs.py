"""Durable job records and a local worker pool. One application process only.

The queue boundary can later be replaced by a broker. SQLite claims are atomic;
crash recovery is performed once at startup, not via distributed worker leases.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
from threading import Event, Thread
from time import perf_counter
from typing import Protocol
from uuid import uuid4

log = logging.getLogger(__name__)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class JobQueue(Protocol):
    def create(self, filename: str) -> dict: ...
    def get(self, job_id: str) -> dict | None: ...
    def begin_receive(self, job_id: str) -> bool: ...
    def enqueue(self, job_id: str, size: int, version: str) -> None: ...
    def claim(self, worker_id: str) -> dict | None: ...
    def complete(self, job_id: str, duration_ms: float, passages: int) -> None: ...
    def fail(self, job_id: str, reason: str) -> None: ...
    def retry(self, job_id: str) -> bool: ...
    def recover(self) -> None: ...
    def snapshot(self) -> dict: ...
    def blocked_files(self) -> set[str]: ...
    def reconcile_ready(self, versions: dict[str, str]) -> None: ...


class QueueFull(Exception):
    pass


class SQLiteJobQueue:
    def __init__(self, path: Path, capacity: int = 1000):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.capacity = path, capacity
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_id TEXT NOT NULL,
                status TEXT NOT NULL, bytes INTEGER NOT NULL DEFAULT 0,
                source_version TEXT, receiving INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, queued_at TEXT, started_at TEXT, finished_at TEXT,
                worker_id TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                duration_ms REAL, queue_wait_ms REAL, passages INTEGER, error TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status, created_at)")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, filename):
        job_id = uuid4().hex
        file_id = f"uploads/{job_id}/{filename}"
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count(*) FROM jobs WHERE status IN ('uploading','queued','indexing')").fetchone()[0]
            if count >= self.capacity:
                raise QueueFull("Upload queue is full. Wait for workers to finish before uploading more files.")
            db.execute("INSERT INTO jobs(id, filename, file_id, status, created_at) VALUES (?,?,?,'uploading',?)",
                       (job_id, filename, file_id, timestamp()))
        return self.get(job_id)

    def get(self, job_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def begin_receive(self, job_id):
        with self.connection() as db:
            return db.execute("UPDATE jobs SET receiving=1 WHERE id=? AND status='uploading' AND receiving=0",
                              (job_id,)).rowcount == 1

    def enqueue(self, job_id, size, version):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='queued', bytes=?, source_version=?, queued_at=?, error=NULL WHERE id=?",
                       (size, version, timestamp(), job_id))

    def claim(self, worker_id):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY queued_at, id LIMIT 1").fetchone()
            if row is None:
                return None
            started = timestamp()
            wait = (datetime.fromisoformat(started)-datetime.fromisoformat(row["queued_at"])).total_seconds()*1000
            db.execute("UPDATE jobs SET status='indexing', worker_id=?, attempts=attempts+1, started_at=?, queue_wait_ms=? WHERE id=?",
                       (worker_id, started, wait, row["id"]))
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def complete(self, job_id, duration_ms, passages):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='ready', finished_at=?, duration_ms=?, passages=?, error=NULL WHERE id=?",
                       (timestamp(), duration_ms, passages, job_id))

    def fail(self, job_id, reason):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='failed', finished_at=?, error=? WHERE id=?",
                       (timestamp(), reason, job_id))

    def retry(self, job_id):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count(*) FROM jobs WHERE status IN ('uploading','queued','indexing')").fetchone()[0]
            if count >= self.capacity:
                raise QueueFull("Upload queue is full. Retry after workers finish.")
            return db.execute("UPDATE jobs SET status='queued', queued_at=?, error=NULL, worker_id=NULL, finished_at=NULL "
                              "WHERE id=? AND status='failed' AND source_version IS NOT NULL",
                              (timestamp(), job_id)).rowcount == 1

    def recover(self):
        with self.connection() as db:
            # The search adapter is volatile: ready jobs must be replayed too.
            db.execute("UPDATE jobs SET status='queued', queued_at=?, worker_id=NULL, error=NULL, finished_at=NULL "
                       "WHERE status IN ('queued','indexing','ready')", (timestamp(),))
            db.execute("UPDATE jobs SET status='failed', error='Upload interrupted; select the file again.', finished_at=? "
                       "WHERE status='uploading'", (timestamp(),))

    def blocked_files(self):
        with self.connection() as db:
            return {r[0] for r in db.execute("SELECT file_id FROM jobs WHERE status!='ready'")}

    def reconcile_ready(self, versions):
        with self.connection() as db:
            rows = db.execute("SELECT id, file_id, source_version FROM jobs WHERE status='ready'").fetchall()
            for row in rows:
                if versions.get(row["file_id"]) != row["source_version"]:
                    db.execute("UPDATE jobs SET status='failed', error='Source changed or was removed. Upload the current version again.', finished_at=? WHERE id=?",
                               (timestamp(), row["id"]))

    def snapshot(self):
        with self.connection() as db:
            counts = dict.fromkeys(("uploading", "queued", "indexing", "ready", "failed"), 0)
            counts.update({row[0]: row[1] for row in db.execute("SELECT status, count(*) FROM jobs GROUP BY status")})
            rows = [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC, id DESC LIMIT 30")]
            oldest = db.execute("SELECT min(queued_at) FROM jobs WHERE status='queued'").fetchone()[0]
            mean = db.execute("SELECT avg(duration_ms) FROM jobs WHERE status='ready'").fetchone()[0]
            active = [dict(row) for row in db.execute("SELECT worker_id, filename FROM jobs WHERE status='indexing'")]
            age = max(0, (datetime.now(timezone.utc)-datetime.fromisoformat(oldest)).total_seconds()) if oldest else 0
            return {"counts": counts, "jobs": rows, "active_workers": active,
                    "oldest_queued_seconds": age, "average_processing_ms": mean,
                    "capacity": self.capacity, "total_jobs": sum(counts.values())}


class WorkerPool:
    def __init__(self, queue: JobQueue, process, count: int):
        self.queue, self.process, self.count = queue, process, count
        self.stop = Event()
        self.threads = []

    def start(self):
        self.queue.recover()
        for i in range(self.count):
            thread = Thread(target=self.run, args=(f"worker-{i+1}",), daemon=True)
            self.threads.append(thread)
            thread.start()

    def run(self, worker_id):
        while not self.stop.is_set():
            try:
                job = self.queue.claim(worker_id)
                if job:
                    start = perf_counter()
                    try:
                        self.process(job, start)
                    except Exception:
                        log.exception("Indexing upload job %s failed", job["id"])
                        self.queue.fail(job["id"], "Indexing failed. Check that the uploaded file is present, unchanged, readable UTF-8 Markdown, then retry.")
                    continue
            except Exception:
                log.exception("Worker %s could not access the indexing queue", worker_id)
            self.stop.wait(.2)

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join()
