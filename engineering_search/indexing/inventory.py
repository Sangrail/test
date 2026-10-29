"""The inventory: every file found by a scan, with its type, version and status."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .status import INDEXED


@dataclass(frozen=True)
class SourceFile:
    file_id: str                       # path relative to the document folder, with "/"
    file_type: str                     # from the detector, for example "markdown" or "jt"
    size: int                          # bytes
    status: str                        # see status.py
    version: str | None = None         # SHA-256 of the content, for files with a reader only
    error: str | None = None           # short reason for a failed file; never document text
    format_version: str | None = None  # from the content, for example "1.7" for a PDF
    reader: str | None = None          # "reader_id@reader_version" of the chosen reader
    observation: str = ""              # what the detector saw, for example "%PDF-1.7"
    warnings: tuple[str, ...] = ()     # parts the reader could not read

    def __post_init__(self):
        object.__setattr__(self, "warnings", tuple(self.warnings))


class Inventory:
    """The files of one scan, by file ID. Uploads add to it with record()."""

    def __init__(self, files: Iterable[SourceFile] = ()):
        self.files: dict[str, SourceFile] = {f.file_id: f for f in files}

    def record(self, source: SourceFile) -> None:
        self.files[source.file_id] = source

    def with_status(self, *statuses: str) -> dict[str, SourceFile]:
        return {k: f for k, f in self.files.items() if f.status in statuses}

    def indexable(self) -> dict[str, SourceFile]:
        """Files that a reader of this build reads; they are in the index after a refresh."""
        return self.with_status(*INDEXED)

    def by_type(self) -> dict[str, int]:
        """Number of files of each file type, indexable or not."""
        return dict(sorted(Counter(f.file_type for f in self.files.values()).items()))

    def by_status(self) -> dict[str, int]:
        return dict(sorted(Counter(f.status for f in self.files.values()).items()))

    def __len__(self) -> int:
        return len(self.files)
