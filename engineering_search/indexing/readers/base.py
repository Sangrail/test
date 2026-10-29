"""What every reader declares (its manifest) and returns (an Extraction).

A reader is an object with a `manifest` and a `read(file_id, version, raw)`
method. It takes the bytes of one file, so a test can give it bytes directly.
The manifest says which file types and format versions it reads, what it can
extract, and which Python packages it needs. The registry uses the manifest to
choose a reader; the coverage report shows it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
from typing import Protocol

from ...core import Passage, Table
from ..status import INDEXED_FULL


@dataclass(frozen=True)
class Capabilities:
    """What a reader can extract. Each one is reported separately in the coverage report."""
    text: bool = False
    tables: bool = False
    metadata: bool = False
    geometry: bool = False

    def names(self) -> list[str]:
        return [name for name, value in vars(self).items() if value]


@dataclass(frozen=True)
class ReaderManifest:
    reader_id: str
    reader_version: str
    file_types: tuple[str, ...]
    capabilities: Capabilities
    # Format versions this reader is tested with, by prefix ("1." covers 1.0 to 1.7).
    # None: the format has no version (Markdown, CSV) or every version is read.
    format_versions: tuple[str, ...] | None = None
    dependencies: tuple[str, ...] = ()  # importable module names

    def supports(self, format_version: str | None) -> bool:
        if self.format_versions is None or format_version is None:
            return True
        return any(format_version.startswith(prefix) for prefix in self.format_versions)

    def missing_dependencies(self) -> list[str]:
        return [module for module in self.dependencies if find_spec(module) is None]

    def describe(self) -> dict:
        return {"reader": f"{self.reader_id}@{self.reader_version}", "file_types": list(self.file_types),
                "format_versions": list(self.format_versions) if self.format_versions else "any",
                "capabilities": self.capabilities.names(), "dependencies": list(self.dependencies),
                "installed": not self.missing_dependencies()}


@dataclass(frozen=True)
class Extraction:
    """What a reader got from one file.

    status is INDEXED_FULL, INDEXED_PARTIAL (some pages, sheets or rows could not be
    read; `warnings` says which), NO_TEXT_LAYER or NO_EXTRACTABLE_CONTENT. A reader
    that cannot read the file at all raises ReaderError instead.
    """
    passages: tuple[Passage, ...]
    status: str = INDEXED_FULL
    warnings: tuple[str, ...] = field(default=())
    tables: tuple[Table, ...] = field(default=())  # rows and columns, for facts and SQL


class ReaderError(Exception):
    """The reader could not read the file. `status` is MALFORMED or ENCRYPTED."""
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


class Reader(Protocol):
    manifest: ReaderManifest

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction: ...
