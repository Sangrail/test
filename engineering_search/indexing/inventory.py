"""The inventory: every file found by a scan, with its file type and outcome."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

# Outcomes of a scan for one file.
INDEXABLE = "indexable"      # a reader exists and the bytes were read and hashed
UNSUPPORTED = "unsupported"  # no reader for the file type; the file is not read
UNREADABLE = "unreadable"    # a reader exists, but the file could not be read


@dataclass(frozen=True)
class SourceFile:
    file_id: str                 # path relative to the document folder, with "/"
    file_type: str               # from the detector, for example "markdown" or "dwg"
    size: int                    # bytes
    outcome: str                 # INDEXABLE, UNSUPPORTED or UNREADABLE
    version: str | None = None   # SHA-256 of the content, for INDEXABLE files only
    error: str | None = None     # the error type, for UNREADABLE files only


class Inventory:
    """The files of one scan, by file ID. Uploads add to it with record()."""

    def __init__(self, files: Iterable[SourceFile] = ()):
        self.files: dict[str, SourceFile] = {f.file_id: f for f in files}

    def record(self, source: SourceFile) -> None:
        self.files[source.file_id] = source

    def with_outcome(self, outcome: str) -> dict[str, SourceFile]:
        return {k: f for k, f in self.files.items() if f.outcome == outcome}

    def indexable(self) -> dict[str, SourceFile]:
        return self.with_outcome(INDEXABLE)

    def by_type(self) -> dict[str, int]:
        """Number of files of each file type, indexable or not."""
        return dict(sorted(Counter(f.file_type for f in self.files.values()).items()))

    def __len__(self) -> int:
        return len(self.files)
