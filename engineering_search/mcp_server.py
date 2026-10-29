"""MCP server: lets a chat agent (Claude Desktop, Claude Code, others) search the documents.

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

INSTRUCTIONS = """Answer questions about engineering documents (Markdown and PDF).
Call search_evidence with the user's question in plain language.
- For one value (a load limit, a material, an approval status), the result has
  answer.type "answer": a sentence or table row copied exactly from a document,
  with its file, page (PDF), lines and SHA-256 file version.
- For "which documents..." questions, answer.type is "list": one entry per
  matching document, each with the exact line that qualifies it. Comparisons
  such as "greater than 5 kN/m²" are applied by the service.
  A list holds at most 200 documents per page; answer.count is the total, and
  `page` 2, 3... returns the next documents when answer.truncated is true.
- For a follow-up about a previous list ("of those, which..."), pass the
  file_id values of that list as `within`.
Quote values exactly and cite file and page. answer.status is one of:
- "found": the cited sentence states the value and names what it is about.
- "unverified": the document contains every question word, but the cited
  sentence does not name some of them (unbound_words), e.g. a load that may be
  for the floor, not the roof. Give the value only with that warning.
- "partial": the closest match lacks some question words (missing_words). Say
  which, and do not present it as the answer.
- "not_found": say that no readable document states it.
Do not guess or calculate values.
Use read_evidence to read a whole page or file around a result."""


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
            return service.read(user, file_id, page)
        except ServiceError as error:
            return {"error": error.detail}

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--documents", type=Path,
                        default=Path(os.environ.get("DOCUMENT_ROOT", "test-repository")))
    parser.add_argument("--state-dir", type=Path, default=Path(os.environ.get("STATE_DIR", ".runtime")))
    parser.add_argument("--user", default=os.environ.get("SEARCH_USER", "jp"),
                        help="Whose file permissions apply (pretend login)")
    args = parser.parse_args()
    # stdout carries the MCP protocol, so all logging goes to stderr.
    logging.basicConfig(level=logging.WARNING)
    create_server(args.documents, args.state_dir, args.user).run("stdio")


if __name__ == "__main__":
    main()
