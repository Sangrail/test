"""Markdown: UTF-8 text split at headings and blank lines, never inside code fences.

Pipe tables ("| a | b |" with a "|---|" line under the header) are also read
as tables, with the line number of each row. Their lines stay in the passages too.
"""
from __future__ import annotations

import re

from ...core import Table, TableRow
from ..detect import MARKDOWN
from ..status import MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest
from .text import split_passages

# The assumption for Markdown is good: an ATX heading names the section below it.
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+)")
PIPE_ROW = re.compile(r"^\s*\|.*\|\s*$")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def cells(line: str) -> tuple[str, ...]:
    """'| a | b \\| c |' -> ('a', 'b | c')"""
    inner = line.strip()[1:-1]
    return tuple(cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", inner))


def pipe_tables(lines: list[str]) -> list[Table]:
    tables, heading, fenced, i = [], "", False, 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (match := MARKDOWN_HEADING.match(line)):
            heading = match.group(1).strip()
        elif (not fenced and PIPE_ROW.match(line) and i + 1 < len(lines) and SEPARATOR.match(lines[i + 1])):
            columns, rows, j = cells(line), [], i + 2
            while j < len(lines) and PIPE_ROW.match(lines[j]):
                rows.append(TableRow(len(rows) + 1, cells(lines[j]), j + 1))
                j += 1
            tables.append(Table(len(tables) + 1, heading, columns, tuple(rows)))
            i = j
            continue
        i += 1
    return tables


class MarkdownReader:
    manifest = ReaderManifest("markdown-text", "2", (MARKDOWN,), Capabilities(text=True, tables=True))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            raise ReaderError(MALFORMED, "not UTF-8 text") from None
        passages = tuple(split_passages(file_id, version, lines, MARKDOWN_HEADING, fenced_code=True))
        if not passages:
            return Extraction((), NO_EXTRACTABLE_CONTENT)
        return Extraction(passages, tables=tuple(pipe_tables(lines)))
