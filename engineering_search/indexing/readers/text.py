"""Split lines of text into passages at headings and blank lines. Shared by the readers."""
from __future__ import annotations

import re

from ...core import Passage


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
