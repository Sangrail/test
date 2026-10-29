"""Markdown: UTF-8 text split at headings and blank lines, never inside code fences."""
from __future__ import annotations

import re

from ..detect import MARKDOWN
from ..status import MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest
from .text import split_passages

# The assumption for Markdown is good: an ATX heading names the section below it.
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+)")


class MarkdownReader:
    manifest = ReaderManifest("markdown-text", "1", (MARKDOWN,), Capabilities(text=True))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            raise ReaderError(MALFORMED, "not UTF-8 text") from None
        passages = tuple(split_passages(file_id, version, lines, MARKDOWN_HEADING, fenced_code=True))
        return Extraction(passages) if passages else Extraction((), NO_EXTRACTABLE_CONTENT)
