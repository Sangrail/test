"""The web app: HTTP routes, pretend sign-in and the web pages.

All search, read and index logic is in service.py. This module only turns
HTTP requests into SearchService calls, and SearchService errors into HTTP
responses.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from .access import ACCESS_RULES, USERS, DemoSessions, MockPermissionStore, PermissionStore, folder_access
from .adapters import SQLiteAuditStore, Telemetry
from .core import AuditReader, AuditStore, Passage, SearchIndex, tokens
from .service import SearchService, ServiceError, now
from .store import SQLiteSearchIndex

log = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500, examples=["roof load"])
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1, le=1_000_000)
    mode: Literal["auto", "answer", "list"] = "auto"
    within: list[str] | None = Field(default=None, max_length=1000,
                                     description="Only these files, for example the documents of a previous list answer")

    @field_validator("query")
    @classmethod
    def meaningful_query(cls, value: str) -> str:
        if not tokens(value):
            raise ValueError("Query must contain at least one word or number")
        return value.strip()


class SearchResponse(BaseModel):
    request_id: str
    security_mode: str
    identity_validation: str
    authorisation: str
    indexed_at: str
    matched_passages: int
    truncated: bool
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_previous: bool
    evidence: list[Passage]
    user: dict
    searched_for: str
    ignored_words: list[str]
    answer: dict
    changed_files: list[str] = Field(default=[], description="Cited files that changed on disc after indexing; their evidence is refused")


class SqlRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=4000,
                     examples=["SELECT subject, material_grade, allowable_load_kn_m2, file_id, line FROM components "
                               "WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5"])
    limit: int = Field(default=100, ge=1, le=500)


class LoginRequest(BaseModel):
    user_id: str


class AdmissionMiddleware:
    """Admit a search, SQL query or evidence read only if it can be answered within the time budget.

    It runs before the route waits for a worker thread, so time spent waiting for
    a thread counts against the budget. A refused request gets 503 with a
    Retry-After header at once, and no evidence."""
    PATHS = (("POST", "/search", "search"), ("POST", "/sql", "sql"), ("GET", "/evidence/", "table_row"))

    def __init__(self, app, service: SearchService):
        self.app, self.service = app, service

    async def __call__(self, scope, receive, send):
        operation = next((name for method, path, name in self.PATHS
                          if scope["type"] == "http" and scope["method"] == method and scope["path"].startswith(path)),
                         None)
        if operation is None:
            return await self.app(scope, receive, send)
        try:
            ticket = self.service.admit(operation=operation)  # the user is not known yet: no session lookup here
        except ServiceError as error:
            response = JSONResponse({"detail": error.detail}, status_code=error.status,
                                    headers={"Retry-After": str(error.detail["retry_after_seconds"])})
            return await response(scope, receive, send)
        async def tracked_send(message):
            if message["type"] == "http.response.start":
                ticket.status = message["status"]  # the telemetry records it when the ticket is released
            await send(message)

        with ticket:
            await self.app(scope, receive, tracked_send)


class CompletionAuditMiddleware:
    """Record in the audit trail whether a search response was sent in full."""
    def __init__(self, app, telemetry: Telemetry, audit: AuditStore):
        self.app, self.telemetry, self.audit = app, telemetry, audit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/search" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        status = 500
        completed = False

        async def tracked_send(message):
            nonlocal status, completed
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True

        try:
            await self.app(scope, receive, tracked_send)
        finally:
            if "audit_request_id" in scope:
                try:
                    await run_in_threadpool(self.audit.append, {
                        "event": "search_response_send_completed" if completed else "search_response_send_incomplete",
                        "request_id": scope["audit_request_id"], "timestamp": now(),
                        "http_status": status,
                    })
                except Exception:
                    # The mandatory manifest was already committed before release.
                    # A post-send failure cannot retract bytes sent to the client.
                    self.telemetry.increment("response_completion_audit_failures_total")
                    log.error("Could not record response completion for %s", scope["audit_request_id"])


def create_app(root: Path | None = None, index: SearchIndex | None = None,
               audit: AuditStore | None = None, telemetry: Telemetry | None = None,
               permissions: PermissionStore | None = None,
               index_on_start: bool = False, audit_reader: AuditReader | None = None,
               index_lock=None, admission=None) -> FastAPI:
    root = (root or Path(os.environ.get("DOCUMENT_ROOT", "test-repository"))).resolve()
    audit = audit if audit is not None else SQLiteAuditStore(
        Path(os.environ.get("AUDIT_DB", ".runtime/audit.sqlite3")))
    audit_reader = audit_reader if audit_reader is not None else (audit if hasattr(audit, "read_page") else None)
    service = SearchService(
        root=root,
        index=index if index is not None else SQLiteSearchIndex(),
        audit=audit,
        permissions=permissions if permissions is not None else MockPermissionStore(),
        telemetry=telemetry, index_lock=index_lock, admission=admission)
    sessions = DemoSessions()

    @asynccontextmanager
    async def lifespan(app):
        if index_on_start:
            result = await run_in_threadpool(service.reindex)
            log.info("Startup index: %s files, %s passages in %.3fs",
                     result["files"], result["passages"], result["total_seconds"])
        yield

    app = FastAPI(title="Engineering evidence search — local MVP", version="0.1.0",
                  description="Local prototype with pretend login and enforced demo permissions. "
                  "Choose a demo user at /search. Index and audit APIs require Maya's index-team role. This is not production authentication.",
                  lifespan=lifespan)
    app.add_middleware(CompletionAuditMiddleware, telemetry=service.telemetry, audit=audit)
    app.add_middleware(AdmissionMiddleware, service=service)  # Outermost: refuses before any other work.
    app.state.service, app.state.sessions = service, sessions
    app.state.index, app.state.telemetry = service.index, service.telemetry
    static = Path(__file__).parent / "static"

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, error: ServiceError):
        return JSONResponse({"detail": error.detail}, status_code=error.status)

    def current_user(request):
        return sessions.resolve(request.cookies.get(sessions.cookie))

    def require_user(request):
        user = current_user(request)
        if user is None:
            service.commit_audit({"event": "identity_validation_failed", "request_id": str(uuid4()),
                                  "timestamp": now(), "actor_subject": None,
                                  "identity_validation": "missing_or_expired_demo_session"})
            raise HTTPException(401, "Choose a demo user to sign in")
        return user

    @app.middleware("http")
    async def backend_boundary(request, call_next):
        """Only the index team (Maya) can open the index, audit and API pages."""
        path = request.url.path
        protected = (path in {"/scan", "/telemetry", "/health", "/openapi.json", "/redoc"}
                     or any(path == prefix or path.startswith(prefix + "/")
                            for prefix in ("/admin", "/index", "/docs", "/audit")))
        if protected:
            user = current_user(request)
            if user is None or user["role"] != "index_team":
                event = {"event": "backend_route_access_denied", "request_id": str(uuid4()),
                         "timestamp": now(), "actor_subject": user["subject"] if user else None,
                         "identity_issuer": "local-demo", "route": path,
                         "reason": "index_team_role_required" if user else "missing_or_expired_demo_session"}
                try:
                    await run_in_threadpool(service.commit_audit, event)
                except ServiceError as error:
                    return JSONResponse({"detail": error.detail}, status_code=error.status)
                if request.method == "GET" and path in {"/admin", "/admin/", "/audit", "/audit/", "/docs", "/redoc"}:
                    return RedirectResponse("/search?reason=backend-only", status_code=303,
                                            headers={"Cache-Control": "no-store"})
                return JSONResponse({"detail": "Index-team role required" if user else "Choose a demo user to sign in"},
                                    status_code=403 if user else 401, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        if protected or path.startswith("/auth") or path == "/search":
            response.headers["Cache-Control"] = "no-store"
        return response

    # Web pages -------------------------------------------------------------

    @app.get("/static/{asset}", include_in_schema=False)
    def assets(asset: str):
        if asset not in {"style.css", "dashboard.js", "search.js", "audit.js"}:
            raise HTTPException(404, "Asset not found")
        # Revalidate each time so a browser never mixes an old script or style with a new page.
        return FileResponse(static / asset, headers={"Cache-Control": "no-cache"})

    @app.get("/", include_in_schema=False)
    def landing():
        return RedirectResponse("/search", status_code=303)

    @app.get("/search", include_in_schema=False)
    def search_page():
        return FileResponse(static / "search.html")

    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(static / "admin.html")

    @app.get("/audit", include_in_schema=False)
    def audit_page():
        return FileResponse(static / "audit.html")

    # Pretend sign-in -------------------------------------------------------

    @app.get("/auth/users", summary="The three deliberately selectable demo identities")
    def demo_users():
        # A demo aid: the sign-in screen shows which folders each demo user can
        # read, so a tester knows what to expect. It shows counts, not content.
        users = []
        for user in USERS:
            try:
                file_ids, readable = service.readable_files(user)
                users.append({**user, "folders": folder_access(file_ids, readable)})
            except ServiceError:
                users.append({**user, "folders": []})
        return {"users": users, "mode": "pretend_login"}

    @app.post("/auth/login", summary="Pretend login; does not verify a real identity")
    def login(body: LoginRequest, request: Request, response: Response):
        try:
            token, user = sessions.create(body.user_id)
        except ValueError:
            raise HTTPException(400, "Unknown demo user") from None
        sessions.revoke(request.cookies.get(sessions.cookie))
        response.set_cookie(sessions.cookie, token, max_age=sessions.ttl, httponly=True,
                            samesite="strict", secure=False, path="/")
        return {"user": user, "mode": "pretend_login"}

    @app.post("/auth/logout")
    def logout(request: Request, response: Response):
        sessions.revoke(request.cookies.get(sessions.cookie))
        response.delete_cookie(sessions.cookie, path="/")
        return {"user": None}

    @app.get("/auth/me")
    def me(request: Request):
        return {"user": current_user(request), "mode": "pretend_login"}

    # Search ----------------------------------------------------------------

    @app.post("/search", response_model=SearchResponse,
              responses={409: {"description": "Index has not been built"},
                         422: {"description": "The question is a SQL statement; ask in plain language"},
                         503: {"description": "Audit unavailable; evidence withheld"}},
              summary="Answer a plain-language question with cited evidence passages")
    def search(body: SearchRequest, request: Request):
        user = require_user(request)
        result = service.search(user, body.query, body.limit, body.page, body.mode, body.within)
        request.scope["audit_request_id"] = result["request_id"]
        return result

    @app.get("/sql/schema", summary="Tables and columns that POST /sql accepts")
    def sql_schema(request: Request, table: str | None = None):
        return service.sql_schema(require_user(request), table)

    @app.post("/sql", responses={400: {"description": "Statement refused or failed"}},
              summary="Run one SELECT over the structured data of the files the user may read")
    def sql(body: SqlRequest, request: Request):
        result = service.query_sql(require_user(request), body.sql, body.limit)
        request.scope["audit_request_id"] = result["request_id"]
        return result

    @app.get("/evidence/{file_id:path}/tables/{table_no}/rows/{row_no}",
             summary="One table row as evidence: columns, cells, line, page, file version and passage")
    def table_row(file_id: str, table_no: int, row_no: int, request: Request):
        return service.table_row_evidence(require_user(request), file_id, table_no, row_no)

    @app.get("/demo/documents", summary="Indexed documents the selected user may read")
    def readable_documents(request: Request):
        user = require_user(request)
        file_ids, readable = service.readable_files(user)
        names = {"md": "Markdown", "pdf": "PDF", "csv": "CSV", "xlsx": "Excel", "dxf": "DXF"}
        types = {name: sum(f.lower().endswith("." + suffix) for f in readable) for suffix, name in names.items()}
        types = {name: count for name, count in types.items() if count}
        return {"documents": [{"file_id": f, "title": f} for f in sorted(readable)],
                "by_type": types,
                # Only readable counts: a user does not learn how many files they cannot read.
                "by_folder": [{"folder": f["folder"], "readable": f["readable"],
                               "markdown": sum(d.startswith(f["folder"]) and d.endswith(".md") for d in readable),
                               "pdf": sum(d.startswith(f["folder"]) and d.endswith(".pdf") for d in readable)}
                              for f in folder_access(file_ids, readable) if f["readable"]]}

    # Index team: index operations and audit ---------------------------------

    @app.get("/admin/access", summary="Backend-only access rules (folder and file)")
    def access_matrix():
        rules = getattr(service.permissions, "rules", ACCESS_RULES)
        return {"users": USERS, "rules": [{"path": path or "(whole repository)", "readers": sorted(readers)}
                                          for path, readers in sorted(rules.items())]}

    @app.get("/index/status", summary="Index state and filesystem inventory as of the last scan")
    def index_status():
        return service.status()

    @app.get("/index/coverage", summary="Coverage by file type, version, status, folder and capability, "
                                        "with each file that was not fully read and why (index team only)")
    def index_coverage():
        return service.coverage()

    @app.post("/scan", summary="Rescan source files and detect changes without reindexing")
    def rescan():
        return service.scan()

    @app.post("/index", summary="Bring the index up to date with the document folder")
    def reindex():
        return service.reindex()

    @app.get("/health")
    def health():
        with service.lock:
            return {**service.state, "security_mode": "pretend_login", "indexer_workers": 1}

    @app.get("/telemetry", summary="Query distributions and indexing throughput")
    def metrics():
        return service.telemetry.snapshot()

    @app.get("/audit/events", summary="Index-team audit log; newest recorded first")
    def audit_events(page: int = Query(default=1, ge=1, le=1_000_000),
                     limit: int = Query(default=20, ge=1, le=100),
                     snapshot_id: int | None = Query(default=None, ge=0)):
        if audit_reader is None:
            raise HTTPException(503, "Audit reading is unavailable")
        try:
            return audit_reader.read_page(page, limit, snapshot_id)
        except Exception:
            raise HTTPException(503, "Audit reading is unavailable") from None

    return app
