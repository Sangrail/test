"""The reader registry: the one place that lists the readers.

default_registry() is the factory. To add a reader, write it in this package
and add it to that list. Several readers may read one file type, for example
two PDF readers for different versions; the first that fits is chosen, so list
the preferred reader first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..detect import UNKNOWN, FileSignature
from ..status import CLASSIFIED, DEPENDENCY_MISSING, NO_READER, UNSUPPORTED_FORMAT, UNSUPPORTED_VERSION
from .base import Reader
from .csv import CsvReader
from .markdown import MarkdownReader
from .pdf import PdfTextReader
from .xlsx import XlsxReader


@dataclass(frozen=True)
class Selection:
    reader: Reader | None
    status: str   # CLASSIFIED when a reader is chosen, otherwise why not


class ReaderRegistry:
    def __init__(self, readers: Iterable[Reader]):
        self.readers = list(readers)

    def select(self, signature: FileSignature) -> Selection:
        """The first reader for the file type and version whose packages are installed."""
        for_type = [r for r in self.readers if signature.file_type in r.manifest.file_types]
        if not for_type:
            return Selection(None, UNSUPPORTED_FORMAT if signature.file_type == UNKNOWN else NO_READER)
        for_version = [r for r in for_type if r.manifest.supports(signature.format_version)]
        if not for_version:
            return Selection(None, UNSUPPORTED_VERSION)
        installed = [r for r in for_version if not r.manifest.missing_dependencies()]
        if not installed:
            return Selection(None, DEPENDENCY_MISSING)
        return Selection(installed[0], CLASSIFIED)

    def file_types(self) -> set[str]:
        return {t for r in self.readers for t in r.manifest.file_types}

    def manifests(self) -> list[dict]:
        return [r.manifest.describe() for r in self.readers]


def default_registry() -> ReaderRegistry:
    """Every reader of this build, preferred first for each file type."""
    return ReaderRegistry([
        MarkdownReader(),
        PdfTextReader(),
        CsvReader(),
        XlsxReader(),
    ])
