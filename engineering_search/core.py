"""Source discovery, Markdown and PDF extraction, and replaceable boundaries.

No dependency on the web framework."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import re
from typing import Protocol


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


@dataclass(frozen=True)
class Passage:
    file_id: str
    source_version: str
    heading: str
    start_line: int
    end_line: int
    text: str
    page: int | None = None  # 1-based page number for PDF; None for Markdown


@dataclass(frozen=True)
class Document:
    file_id: str
    source_version: str
    passages: tuple[Passage, ...]


class SearchIndex(Protocol):
    """apply publishes all changes atomically, or leaves the old index intact."""
    def versions(self) -> dict[str, str]: ...
    def apply(self, upserts: list[Document], removals: list[str]) -> None: ...
    def upsert(self, document: Document) -> None: ...
    def remove(self, file_id: str) -> None: ...
    def passage_count(self) -> int: ...
    def search(self, query: str, limit: int) -> tuple[list[Passage], int]: ...
    def candidates(self, query: str) -> list[Passage]: ...
    def passages(self, file_id: str, page: int | None = None) -> list[Passage]: ...


class AuditStore(Protocol):
    """append must return only after committing the event durably."""
    def append(self, event: dict) -> None: ...


class AuditReader(Protocol):
    """Read newest committed events first within a fixed upper event ID."""
    def read_page(self, page: int, limit: int, snapshot_id: int | None = None) -> dict: ...


SOURCE_SUFFIXES = (".md", ".pdf")


def source_files(root: Path) -> list[Path]:
    """One discovery rule for scans and builds; unreadable folders fail the scan."""
    if not root.is_dir():
        raise ValueError("Configured document root is not a directory")

    def failed(error: OSError) -> None:
        raise error

    paths = []
    for directory, _, names in os.walk(root, followlinks=False, onerror=failed):
        for name in names:
            path = Path(directory) / name
            if (path.suffix.casefold() in SOURCE_SUFFIXES and not path.is_symlink()
                    and path.is_file() and path.resolve().is_relative_to(root)):
                paths.append(path)
    return sorted(paths)


def scan_files(root: Path) -> dict[str, dict]:
    """Observe file contents without modifying the search index."""
    observed = {}
    for path in source_files(root):
        raw = path.read_bytes()
        observed[path.relative_to(root).as_posix()] = {
            "source_version": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return observed


MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+)")
# Numbered PDF headings such as "3.1 Roof load limit" or "3.0 DESIGN PARAMETERS".
# No comma, colon or full stop, so a wrapped line such as "14 May 2024, ..." is not a heading.
PDF_HEADING = re.compile(r"^(\d+(?:\.\d+)*\s+[A-Z][A-Za-z][^,.:;]{0,60}?)\s*$")
PDF_MAX_LINES = 15


def split_passages(file_id: str, version: str, lines: list[str], heading_pattern: re.Pattern,
                   page: int | None = None, fenced_code: bool = False,
                   max_lines: int | None = None) -> list[Passage]:
    """Split lines into passages at headings and blank lines.

    A heading line is not part of a passage; it becomes the passage heading.
    Line numbers are 1-based. For a PDF they count lines of that page's text.
    """
    heading = ""
    start: int | None = None
    passages: list[Passage] = []
    fenced = False

    def flush(end: int) -> None:
        nonlocal start
        if start is not None:
            passages.append(Passage(file_id, version, heading, start + 1, end,
                                    "\n".join(lines[start:end]), page))
            start = None

    for i, line in enumerate(lines):
        is_fence = fenced_code and line.lstrip().startswith(("```", "~~~"))
        match = None if fenced else heading_pattern.match(line)
        if match and len(line) < 100:
            flush(i)
            heading = match.group(1).strip()
        elif not line.strip() and not fenced:
            flush(i)
        else:
            if start is None:
                start = i
            elif max_lines and i - start >= max_lines:
                flush(i)
                start = i
        if is_fence:
            fenced = not fenced
    flush(len(lines))
    return passages


def pdf_pages(raw: bytes) -> list[str]:
    """Text layer of each page. No OCR: a scanned page gives no text."""
    from io import BytesIO
    import logging

    from pypdf import PdfReader

    # pypdf logs harmless font warnings for many real PDFs.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    return [page.extract_text() or "" for page in PdfReader(BytesIO(raw)).pages]


def extract(path: Path, root: Path) -> tuple[Document, int]:
    """Read one Markdown or PDF file into passages."""
    raw = path.read_bytes()
    file_id = path.relative_to(root).as_posix()
    version = hashlib.sha256(raw).hexdigest()
    if path.suffix.casefold() == ".pdf":
        passages = [passage for number, text in enumerate(pdf_pages(raw), start=1)
                    for passage in split_passages(file_id, version, text.splitlines(), PDF_HEADING,
                                                  page=number, max_lines=PDF_MAX_LINES)]
    else:
        passages = split_passages(file_id, version, raw.decode("utf-8").splitlines(),
                                  MARKDOWN_HEADING, fenced_code=True)
    return Document(file_id, version, tuple(passages)), len(raw)


def evidence_manifest(passages: list[Passage]) -> list[dict]:
    # No raw document content in routine audit events.
    return [{k: v for k, v in asdict(p).items() if k not in ("text", "heading")}
            for p in passages]
