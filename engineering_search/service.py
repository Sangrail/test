"""The search service: everything that the web app and the MCP server share.

SearchService owns the index, the permissions, the audit log and the index
state. It has no web code. app.py puts HTTP routes on it, and mcp_server.py
puts MCP tools on it, so both use the same search, the same permission checks
and the same audit log.

A method that cannot complete raises ServiceError with an HTTP-style status.
The web app returns that status. The MCP server returns the detail as an error.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from threading import Lock, RLock
from time import perf_counter
from uuid import uuid4

from .access import PermissionStore
from .adapters import Telemetry
from .answer import answer as pick_answer, list_documents, manifest, understand
from .core import AuditStore, SearchIndex, evidence_manifest
from .indexing import INDEXABLE, UNREADABLE, UNSUPPORTED, Indexer, Inventory
from .jobs import JobQueue
from .query import plan

log = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServiceError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(detail)
        self.status, self.detail = status, detail


class SearchService:
    def __init__(self, root: Path, index: SearchIndex, audit: AuditStore, permissions: PermissionStore,
                 queue: JobQueue, telemetry: Telemetry | None = None, indexer: Indexer | None = None):
        self.root = root.resolve()
        self.index, self.audit, self.permissions, self.queue = index, audit, permissions, queue
        self.telemetry = telemetry if telemetry is not None else Telemetry()
        # The indexing line: finds, classifies and reads the files. The service publishes its plans.
        self.indexer = indexer if indexer is not None else Indexer(self.root)
        # lock protects the index and the state. operation_lock allows one scan,
        # index build or upload publish at a time.
        self.lock = RLock()
        self.operation_lock = Lock()
        self.state = {"ready": False, "last_indexed_at": None, "last_scanned_at": None,
                      "operation": None, "scan_error": None, "index_error": None,
                      "last_index_run": None, "last_scan_seconds": None}
        # The files found by the last scan, with their file types.
        self.inventory: Inventory | None = None
        if index.versions():  # A persisted index is searchable straight away.
            self.state.update(ready=True, last_indexed_at=getattr(index, "indexed_at", lambda: None)())

    # Audit ---------------------------------------------------------------

    def commit_audit(self, event: dict):
        """Write an audit event. If that fails, the caller gets no evidence."""
        try:
            self.audit.append(event)
        except Exception:
            self.telemetry.increment("audit_failures_total")
            raise ServiceError(503, {"message": "Audit unavailable; evidence withheld",
                                     "request_id": event["request_id"]}) from None

    # Search --------------------------------------------------------------

    def search(self, user: dict, query: str, limit: int = 10, page: int = 1,
               mode: str = "auto", within: list[str] | None = None) -> dict:
        """The one search function. The web API and the MCP server both call it.

        Order: understand the question, look it up in the index, check
        permissions, pick the answer, page the evidence, write the audit
        event, then return. No audit, no evidence.
        """
        request_id = str(uuid4())
        stage_start = perf_counter()
        with self.lock:
            if not self.state["ready"]:
                raise ServiceError(409, "Build the index with POST /index first")
            retrieval_start = perf_counter()
            # A question about a previous list ("of those, which…") is also a list question.
            intent = understand(query, "list" if within is not None and mode == "auto" else mode)
            query_plan = plan(intent.search_text)
            scope = None if within is None else set(within)
            candidates = [p for p in self.index.candidates(query_plan) if scope is None or p.file_id in scope]
            listed: set[str] = set()
            if intent.mode == "list":
                # A list answer needs documents that contain every query word somewhere.
                listed = {f for f, count in self.index.document_matches(query_plan).items()
                          if count == len(query_plan.terms) and (scope is None or f in scope)}
            retrieval_ms = (perf_counter() - retrieval_start) * 1000

            policy_start = perf_counter()
            file_ids = {p.file_id for p in candidates} | listed
            try:
                policy = self.permissions.evaluate(user["subject"], file_ids)
            except Exception:
                self.commit_audit({"event": "authorisation_unavailable", "request_id": request_id,
                                   "timestamp": now(), "actor_subject": user["subject"],
                                   "identity_issuer": "local-demo", "identity_validation": "demo_session",
                                   "authorisation": "unavailable"})
                raise ServiceError(503, "Permissions unavailable; evidence withheld") from None
            # Everything after this line uses permitted files only.
            permitted = [p for p in candidates if p.file_id in policy.allowed]
            if intent.mode == "list":
                result = list_documents(query_plan, intent.comparison,
                                        {f: self.index.passages(f) for f in sorted(listed & policy.allowed)})
            else:
                result = pick_answer(query_plan, permitted, lambda file_id: " ".join(
                    f"{p.heading} {p.text}" for p in self.index.passages(file_id)))
            result["mode"] = intent.mode
            # Pages are live views: permissions are checked again on each request.
            total = len(permitted)
            offset = (page - 1) * limit
            passages = permitted[offset:offset + limit]
            total_pages = (total + limit - 1) // limit
            policy_ms = (perf_counter() - policy_start) * 1000

            audit_start = perf_counter()
            self.commit_audit({
                "event": "search_evidence_prepared", "request_id": request_id,
                "timestamp": now(), "actor_subject": user["subject"], "identity_issuer": "local-demo",
                "identity_validation": "demo_session", "authorisation": "enforced_demo_policy",
                "security_mode": "pretend_login", "permission_version": policy.version,
                "decisions": [{"file_id": file_id, "action": "read",
                               "decision": "search_match_allowed" if file_id in policy.allowed
                               else "search_match_excluded_by_policy",
                               "reason": policy.reasons[file_id]} for file_id in sorted(file_ids)],
                "matched_passages": total, "returned_passages": len(passages),
                "page": page, "limit": limit, "query_characters": len(query),
                "answer": manifest(result), "evidence": evidence_manifest(passages)})
            audit_ms = (perf_counter() - audit_start) * 1000
            self.telemetry.record_stages({"request_id": request_id, "retrieval_ms": retrieval_ms,
                                          "authorisation_ms": policy_ms, "audit_ms": audit_ms,
                                          "service_ms": (perf_counter() - stage_start) * 1000})
            return {"request_id": request_id, "security_mode": "pretend_login",
                    "identity_validation": "demo_session", "authorisation": "enforced_demo_policy",
                    "user": user,
                    "searched_for": query_plan.searched_for(), "ignored_words": list(query_plan.ignored),
                    "answer": result,
                    "indexed_at": self.state["last_indexed_at"], "matched_passages": total,
                    "truncated": total > len(passages),
                    "page": page, "limit": limit, "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1 and total > 0,
                    "evidence": [asdict(p) for p in passages]}

    def read(self, user: dict, file_id: str, page: int | None = None) -> dict:
        """Return the indexed passages of one file (or one PDF page), if the user may read it."""
        request_id = str(uuid4())
        with self.lock:
            try:
                policy = self.permissions.evaluate(user["subject"], {file_id})
            except Exception:
                raise ServiceError(503, "Permissions unavailable; evidence withheld") from None
            # Same answer for "missing" and "not allowed", so file names do not leak.
            passages = self.index.passages(file_id, page) if file_id in policy.allowed else []
            if not passages:
                raise ServiceError(404, "No readable evidence for that file and page")
            self.commit_audit({"event": "evidence_read", "request_id": request_id, "timestamp": now(),
                               "actor_subject": user["subject"], "identity_issuer": "local-demo",
                               "permission_version": policy.version, "file_id": file_id, "page": page,
                               "evidence": evidence_manifest(passages)})
            return {"request_id": request_id, "file_id": file_id, "page": page,
                    "evidence": [asdict(p) for p in passages]}

    def readable_files(self, user: dict) -> tuple[set[str], set[str]]:
        """Return (all indexed files, the files that the user can read)."""
        with self.lock:
            file_ids = set(self.index.versions())
        try:
            return file_ids, set(self.permissions.evaluate(user["subject"], file_ids).allowed)
        except Exception:
            raise ServiceError(503, "Permissions unavailable; document list withheld") from None

    # Index operations ----------------------------------------------------

    def _begin(self, operation: str):
        if not self.operation_lock.acquire(blocking=False):
            raise ServiceError(409, "A scan or index build is already running")
        with self.lock:
            self.state["operation"] = operation

    def _end(self):
        with self.lock:
            self.state["operation"] = None
        self.operation_lock.release()

    def scan(self) -> dict:
        """Find the files in the document folder, their types and versions. Does not change the index."""
        self._begin("scanning")
        start = perf_counter()
        try:
            inventory = self.indexer.scan()
            with self.lock:
                self.inventory = inventory
                self.state.update(last_scanned_at=now(), scan_error=None,
                                  last_scan_seconds=perf_counter() - start)
        except Exception:
            with self.lock:
                self.state["scan_error"] = "Scan failed. Check that the document folder and files are readable."
            raise ServiceError(503, self.state["scan_error"]) from None
        finally:
            self._end()
        return self.status()

    def reindex(self) -> dict:
        """Bring the index up to date with the document folder.

        The indexer scans every file, detects its type, and extracts the new
        and changed files that have a reader. The service publishes the plan
        in one transaction. A file that cannot be read or extracted is
        skipped and reported.
        """
        start = perf_counter()
        self._begin("indexing")
        try:
            with self.lock:
                old = self.index.versions()
            blocked = self.queue.blocked_files()  # Uploads that the workers still own.
            read_start = perf_counter()
            plan = self.indexer.plan(old, skip=blocked)
            ingestion_seconds = max(perf_counter() - read_start, 1e-9)
            indexable = plan.inventory.indexable()
            total_bytes = sum(f.size for f in indexable.values())
            with self.lock:
                commit_start = perf_counter()
                self.queue.reconcile_ready(plan.versions)
                self.index.apply(plan.upserts, plan.removals)
                indexing_seconds = max(perf_counter() - commit_start, 1e-9)
                self.inventory = plan.inventory
                self.state.update(ready=True, last_indexed_at=now(), last_scanned_at=now(),
                                  scan_error=None, index_error=None, last_scan_seconds=ingestion_seconds)
                result = {"indexed_at": self.state["last_indexed_at"], "workers": 1,
                          "files": len(plan.versions), "read_files": len(plan.upserts), "bytes": total_bytes,
                          "failed_files": plan.failed, "scanned_files": len(indexable),
                          "file_types": plan.inventory.by_type(),
                          "unsupported_files": len(plan.inventory.with_outcome(UNSUPPORTED)),
                          "passages": self.index.passage_count(),
                          "added": plan.added, "edited": plan.edited, "deleted": len(plan.removals),
                          "ingestion_seconds": ingestion_seconds,
                          "indexing_seconds": indexing_seconds,
                          "total_seconds": perf_counter() - start,
                          "ingestion_files_per_second": len(indexable) / ingestion_seconds,
                          "ingestion_bytes_per_second": total_bytes / ingestion_seconds,
                          "indexing_files_per_second": len(plan.upserts) / indexing_seconds,
                          "indexing_passages_per_second": sum(len(d.passages) for d in plan.upserts) / indexing_seconds,
                          "index_strategy": "incremental"}
                self.state["last_index_run"] = result
            self.telemetry.record_index(result)
            return result
        except Exception:
            with self.lock:
                self.state["index_error"] = "Index refresh failed; previous snapshot retained"
            self.telemetry.increment("index_failures_total")
            log.exception("Index refresh failed; previous snapshot retained")
            raise ServiceError(503, "Index refresh failed; previous snapshot retained") from None
        finally:
            self._end()

    def status(self) -> dict:
        """The index state, and each file found by the last scan compared with the index.

        Files that cannot be indexed (no reader for the type, or unreadable)
        are listed with that status. They are not pending changes.
        """
        with self.lock:
            versions = self.index.versions()
            rows = []
            changes = {"added": 0, "edited": 0, "deleted": 0}
            inventory = self.inventory
            if inventory is not None:
                for file_id in sorted(inventory.files.keys() | versions.keys()):
                    source = inventory.files.get(file_id)
                    status = ("deleted" if source is None else source.outcome if source.outcome != INDEXABLE
                              else "added" if file_id not in versions
                              else "edited" if source.version != versions[file_id]
                              else "indexed")
                    if status in changes:
                        changes[status] += 1
                    rows.append({"file_id": file_id, "status": status,
                                 "file_type": source.file_type if source else None,
                                 "bytes": source.size if source else None})
            state = self.state
            index_status = (state["operation"] or
                            ("error" if state["scan_error"] or state["index_error"] else
                             "not_indexed" if not state["ready"] else
                             "not_scanned" if inventory is None else
                             "out_of_date" if any(changes.values()) else "up_to_date"))
            return {**state, "status": index_status, "document_root": str(self.root),
                    "source_files": len(inventory.indexable()) if inventory is not None else None,
                    "file_types": inventory.by_type() if inventory is not None else None,
                    "unsupported_files": len(inventory.with_outcome(UNSUPPORTED)) if inventory is not None else None,
                    "unreadable_files": len(inventory.with_outcome(UNREADABLE)) if inventory is not None else None,
                    "indexed_files": len(versions), "pending_changes": changes,
                    "searchable_passages": self.index.passage_count(),
                    "documents": rows, "watcher_enabled": False, "indexer_workers": 1}

    # Uploads -------------------------------------------------------------

    def save_upload(self, job: dict, content: bytes):
        """Write an uploaded Markdown file safely, then queue it for indexing."""
        path = self.root / job["file_id"]
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Upload directory must be within the source root")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        source = self.indexer.source(path, content)
        with self.operation_lock, self.lock:
            if self.inventory is not None:
                self.inventory.record(source)
            self.queue.enqueue(job["id"], len(content), source.version)

    def index_upload(self, job: dict, start: float):
        """Index one uploaded file. The upload workers call this."""
        path = self.root / job["file_id"]
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError("Upload escaped its source folder")
        document, source = self.indexer.extract(path)
        if document.source_version != job["source_version"]:
            raise ValueError("Uploaded content changed before indexing")
        # File extraction can run at the same time as other work. Publish is a
        # short serial section shared with full builds, so a rebuild cannot
        # overwrite a worker commit.
        with self.operation_lock, self.lock:
            self.index.upsert(document)
            try:
                self.queue.complete(job["id"], (perf_counter() - start) * 1000, len(document.passages))
            except Exception:
                self.index.remove(document.file_id)
                raise
            self.state.update(ready=True, last_indexed_at=now())
            if self.inventory is not None:
                self.inventory.record(source)
