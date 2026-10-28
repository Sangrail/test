"""Where the running service keeps its data, shared by the web server and the MCP server.

    <state-dir>/index-<id>.sqlite3   search index (documents, passages, FTS5)
    <state-dir>/queue-<id>.sqlite3   upload job queue
    <state-dir>/audit.sqlite3        audit log

<id> is taken from the document folder path, so two document folders never
share an index.
"""
import hashlib
from pathlib import Path

from .access import MockPermissionStore
from .adapters import SQLiteAuditStore
from .app import create_app
from .jobs import SQLiteJobQueue
from .service import SearchService
from .store import SQLiteSearchIndex


def stores(documents: Path, state: Path) -> dict:
    """Open the index, queue and audit files for this document folder."""
    root = documents.expanduser().resolve()
    state = state.expanduser().resolve()
    namespace = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    return {"root": root,
            "index": SQLiteSearchIndex(state / f"index-{namespace}.sqlite3"),
            "audit": SQLiteAuditStore(state / "audit.sqlite3"),
            "queue": SQLiteJobQueue(state / f"queue-{namespace}.sqlite3")}


def build_service(documents: Path, state: Path) -> SearchService:
    """The search service without the web app. The MCP server uses this."""
    return SearchService(permissions=MockPermissionStore(), **stores(documents, state))


def build_app(documents: Path, state: Path, worker_count: int = 2, index_on_start: bool = True):
    """The web app, with its own search service. python -m engineering_search uses this."""
    return create_app(worker_count=worker_count, index_on_start=index_on_start, **stores(documents, state))
