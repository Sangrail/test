"""MCP server: lets a chat agent (Claude Code, Codex, Pi, others) search the documents and
query their tables with constrained SQL.

It calls the same SearchService (service.py) as the web page, with the same
index, permissions and audit log. It does not start the web app. It talks MCP over stdio, so the chat client starts
it as a local process:

    uv run python -m engineering_search.mcp_server --user jp

SECURITY HOLE: the --user flag stands in for real identity and nothing
verifies it. The person who uses the chat client is not matched to the file
permissions: anyone who can edit the client configuration can read as any
user. Before real restricted files, run a remote server behind the company
sign-in (OAuth) and take the user from the verified token. See docs/MCP.md.
"""
import argparse
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .access import USERS
from .runtime import build_service
from .service import ServiceError

INSTRUCTIONS = """Answer questions about engineering documents: Markdown, PDF, CSV and XLSX.
There are two ways in. Choose by the question.

1. Unstructured (text): search_evidence with the question in plain language.
   For one value (a load limit, a material, an approval status) answer.type is
   "answer": a sentence or row copied exactly from a document, with file, page,
   lines and SHA-256 file version. For "which documents..." answer.type is
   "list", one entry per document with the line that qualifies it; comparisons
   such as "greater than 5 kN/m²" are applied by the service. A list holds at
   most 200 documents per page; answer.count is the total; pass page 2, 3...
   when answer.truncated is true. For "of those, which...", pass the file_id
   values of the previous list as `within`.
   answer.status is one of:
   - "found": the cited sentence states the value and names what it is about.
   - "unverified": the document has every question word, but the cited sentence
     does not name some of them (unbound_words), e.g. a load that may be for the
     floor, not the roof. Give the value only with that warning.
   - "partial": the closest match lacks some question words (missing_words).
     Say which; do not present it as the answer.
   - "not_found": say that no readable document states it.

2. Structured (tables): for filters, joins and counts over component schedules,
   registers and tables ("which S355 components have an allowable load under
   5 kN/m²?"), write ONE SQLite SELECT and run it with query_sql. Call
   describe_schema first (and describe_table for columns). The `components`
   view has one row per table row: subject, project, material_grade,
   allowable_load_kn_m2 (a capacity), imposed_load_kn_m2 (a demand),
   compliance_status, file_id, line, page. `facts` has one row per typed cell,
   with si_value in SI units (Pa for pressure). Only rows from files the user
   may read are present. Never compare a capacity with a demand. Match grades
   with LIKE 'S355%'. Normalise units, not intent: 5 N/m² is not 5 kN/m².
   Select file_id, table_no, row_no and line so each row can be cited; use
   get_document_evidence to show the exact row and passage for a citation.

If a tool returns an error with "busy": true, the service is at capacity: tell
the user, with retry_after_seconds, and do not retry in a loop.

Quote values exactly and cite file and line (and page or sheet). Do not guess
or calculate values. Use read_evidence to read a whole page or file. Tables
come only from files a reader could read: say so if the user may need data
from scans or CAD files, which are not read."""


def create_server(documents: Path, state: Path, user_id: str) -> FastMCP:
    user = next((u for u in USERS if u["id"] == user_id), None)
    if user is None:
        raise ValueError(f"Unknown user {user_id!r}; choose one of {[u['id'] for u in USERS]}")
    service = build_service(documents, state)
    service.reindex()  # Hashes every file, extracts only new or changed files; the index is kept between runs.
    server = FastMCP("engineering-search", instructions=INSTRUCTIONS)

    @server.tool()
    def search_evidence(question: str, mode: str = "auto", within: list[str] | None = None,
                        limit: int = 10, page: int = 1) -> dict:
        """Answer a plain-language question from the documents, with exact sources.

        mode: "auto" (default), "answer" (one value) or "list" (all matching documents).
        within: only these file_id values, for a follow-up about a previous list.
        Returns `answer` (the value, or the list of documents) and `evidence`
        (supporting passages, best first). Each source has file_id, page (PDF
        only), start_line, end_line, text and source_version.
        """
        if mode not in ("auto", "answer", "list"):
            return {"error": "mode must be auto, answer or list"}
        try:
            with service.admit():
                result = service.search(user, question, max(1, min(limit, 50)), max(1, page), mode, within)
        except ServiceError as error:
            return {"error": error.detail}
        keep = ("answer", "searched_for", "ignored_words", "matched_passages", "page", "total_pages",
                "indexed_at", "request_id", "evidence")
        return {key: result[key] for key in keep}

    @server.tool()
    def read_evidence(file_id: str, page: int | None = None) -> dict:
        """Read all indexed passages of one file, or of one page of a PDF."""
        try:
            with service.admit():
                return service.read(user, file_id, page)
        except ServiceError as error:
            return {"error": error.detail}

    @server.tool()
    def describe_schema() -> dict:
        """The tables that query_sql can read, with a description of each, and notes on units and citations."""
        return service.sql_schema(user)

    @server.tool()
    def list_tables() -> list[str]:
        """The names of the tables and views that query_sql can read."""
        return list(service.sql_schema(user)["tables"])

    @server.tool()
    def describe_table(table: str) -> dict:
        """The columns of one table or view, with type, meaning and units."""
        try:
            return service.sql_schema(user, table)
        except ServiceError as error:
            return {"error": error.detail}

    @server.tool()
    def query_sql(sql: str, limit: int = 100) -> dict:
        """Run ONE SQLite SELECT over the structured data (tables and typed facts) of the files the
        user may read. Returns columns, rows, row_count and truncated. Limit: 1 to 500 rows.
        Example: SELECT subject, material_grade, allowable_load_kn_m2, file_id, table_no, row_no, line
        FROM components WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5"""
        try:
            with service.admit():
                return service.query_sql(user, sql, max(1, min(limit, 500)))
        except ServiceError as error:
            return {"error": error.detail}

    @server.tool()
    def get_document_evidence(file_id: str, table_no: int, row_no: int) -> dict:
        """The evidence for one table row from a query_sql result: column names, cells as read,
        line, page (or sheet), the typed facts, the file's SHA-256 version and the verbatim passage."""
        try:
            with service.admit():
                return service.table_row_evidence(user, file_id, table_no, row_no)
        except ServiceError as error:
            return {"error": error.detail}

    if user["role"] == "index_team":  # Obviously MVP - not secure!!! The report names files, so other users do not get the tool.
        @server.tool()
        def get_index_coverage(gaps_limit: int = 50) -> dict:
            """Index coverage: files by type, format version, status, folder and capability,
            the readers and what they can extract, and the files that were not fully read,
            with the reason and a hint (up to gaps_limit of them)."""
            report = service.coverage()
            return {**report, "gaps": report["gaps"][:max(0, gaps_limit)], "gaps_total": len(report["gaps"])}

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--documents", type=Path,
                        default=Path(os.environ.get("DOCUMENT_ROOT", "test-repository")))
    parser.add_argument("--state-dir", type=Path, default=Path(os.environ.get("STATE_DIR", ".runtime")))

    # Obviously, we're simulating the user here. In reality, the MCP server would
    # get the logged-in user or the authenticated user for the person requesting the service.
    parser.add_argument("--user", default=os.environ.get("SEARCH_USER", "jp"),
                        help="Whose file permissions apply (pretend login)")
    args = parser.parse_args()
    # stdout carries the MCP protocol, so all logging goes to stderr.
    logging.basicConfig(level=logging.WARNING)
    create_server(args.documents, args.state_dir, args.user).run("stdio")


if __name__ == "__main__":
    main()
