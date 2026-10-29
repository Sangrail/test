"""File type detection.

A detector names the type of a file, for example "markdown", "pdf" or "dwg".
It does not decide if the type can be indexed: the indexer does that, from
the readers that it has. Thus a DWG file is detected as "dwg" and reported
as unsupported, not lost as an unknown file.

The MVP detects by file extension only. It does not read the file. A later
detector can read the first bytes of the file (libmagic, python-magic) and
also find the format version (ADR 0003). It only has to implement Detector.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol

MARKDOWN = "markdown"
PDF = "pdf"
UNKNOWN = "unknown"

# Extension -> file type. Only Markdown and PDF have readers in the MVP. The
# other types are named so that the inventory can report them by type.
EXTENSIONS: Mapping[str, str] = {
    ".md": MARKDOWN,
    ".pdf": PDF,
    ".txt": "text",
    ".docx": "word",
    ".xlsx": "excel",
    ".dwg": "dwg",
    ".dxf": "dxf",
    ".jt": "jt",
    ".catpart": "catia",
    ".catproduct": "catia",
    ".catdrawing": "catia",
    ".ifc": "ifc",
}


class Detector(Protocol):
    def detect(self, path: Path) -> str:
        """Return the file type of path, or UNKNOWN."""
        ...


class ExtensionDetector:
    """Detect the file type from the file extension. Case does not matter."""

    def __init__(self, extensions: Mapping[str, str] = EXTENSIONS):
        self.extensions = {suffix.casefold(): file_type for suffix, file_type in extensions.items()}

    def detect(self, path: Path) -> str:
        return self.extensions.get(path.suffix.casefold(), UNKNOWN)
