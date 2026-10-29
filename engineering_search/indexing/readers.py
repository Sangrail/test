"""Readers: one function for each file type that can be indexed.

A reader takes the bytes of one file and returns its passages. It does not
open the file, so a test can give it bytes directly.
"""
from __future__ import annotations

import re
from typing import Callable, Mapping

from ..core import Passage
from .detect import MARKDOWN, PDF

# (file_id, source_version, raw bytes) -> passages
Reader = Callable[[str, str, bytes], list[Passage]]

# The assumption for Markdown is good. The assumption for PDF heading is less ideal.
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


def read_markdown(file_id: str, version: str, raw: bytes) -> list[Passage]:
    """UTF-8 Markdown, split at headings and blank lines, never inside code fences."""
    return split_passages(file_id, version, raw.decode("utf-8").splitlines(),
                          MARKDOWN_HEADING, fenced_code=True)


def read_pdf(file_id: str, version: str, raw: bytes) -> list[Passage]:
    """The text layer of each page, split at numbered headings and blank lines."""
    return [passage for number, text in enumerate(pdf_pages(raw), start=1)
            for passage in split_passages(file_id, version, text.splitlines(), PDF_HEADING,
                                          page=number, max_lines=PDF_MAX_LINES)]


# File type -> reader. A file type without a reader is not indexed.
READERS: Mapping[str, Reader] = {MARKDOWN: read_markdown, PDF: read_pdf}
