"""The indexer: turns the document folder into changes for the search index.

    scan()          find every file, detect its type, hash the files that can be indexed
    plan(indexed)   compare the scan with the index; extract new and changed files
    extract(path)   read one file into a Document (also used for uploads)

The indexer reads files. It never writes the index, and it has no locks,
queue or web code. The caller publishes a plan with
index.apply(plan.upserts, plan.removals). Thus a test needs only a folder.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path
from typing import Mapping

from ..core import Document
from .detect import Detector, ExtensionDetector
from .inventory import INDEXABLE, UNREADABLE, UNSUPPORTED, Inventory, SourceFile
from .readers import READERS, Reader

log = logging.getLogger(__name__)


class UnsupportedFileType(ValueError):
    pass


@dataclass(frozen=True)
class IndexPlan:
    inventory: Inventory
    upserts: list[Document]     # new and changed files, extracted
    removals: list[str]         # indexed files that are gone, or can no longer be indexed
    versions: dict[str, str]    # file ID -> version of each file in the index after publish
    failed: list[dict]          # {"file_id", "error"} for files that could not be read or extracted
    added: int
    edited: int


class Indexer:
    def __init__(self, root: Path, detector: Detector | None = None,
                 readers: Mapping[str, Reader] = READERS):
        self.root = root.resolve()
        self.detector = detector if detector is not None else ExtensionDetector()
        self.readers = readers

    def paths(self) -> list[Path]:
        """Every regular file below the root. No symbolic links, no hidden files.

        An unreadable folder fails the scan: its files would otherwise look deleted.
        """
        if not self.root.is_dir():
            raise ValueError("Configured document root is not a directory")

        def failed(error: OSError) -> None:
            raise error

        paths = []
        for directory, folders, names in os.walk(self.root, followlinks=False, onerror=failed):
            folders[:] = [f for f in folders if not f.startswith(".")]
            for name in names:
                path = Path(directory) / name
                if (not name.startswith(".") and not path.is_symlink() and path.is_file()
                        and path.resolve().is_relative_to(self.root)):
                    paths.append(path)
        return sorted(paths)

    def source(self, path: Path, raw: bytes | None = None) -> SourceFile:
        """Detect the type of one file. Read and hash it only if a reader exists."""
        file_id = path.relative_to(self.root).as_posix()
        file_type = self.detector.detect(path)
        try:
            if file_type not in self.readers:
                return SourceFile(file_id, file_type, path.stat().st_size, UNSUPPORTED)
            raw = path.read_bytes() if raw is None else raw
        except OSError as error:
            return SourceFile(file_id, file_type, 0, UNREADABLE, error=type(error).__name__)
        return SourceFile(file_id, file_type, len(raw), INDEXABLE, hashlib.sha256(raw).hexdigest())

    def scan(self) -> Inventory:
        """Find the files and their types. Does not extract and does not change the index."""
        return Inventory(self.source(path) for path in self.paths())

    def extract(self, path: Path) -> tuple[Document, SourceFile]:
        """Read one file into a Document with the reader for its file type."""
        file_type = self.detector.detect(path)
        reader = self.readers.get(file_type)
        if reader is None:
            raise UnsupportedFileType(f"No reader for {file_type} files")
        raw = path.read_bytes()
        source = self.source(path, raw)
        return Document(source.file_id, source.version, tuple(reader(source.file_id, source.version, raw))), source

    def plan(self, indexed: Mapping[str, str], skip: set[str] = frozenset()) -> IndexPlan:
        """Scan, then work out what to change in an index that holds `indexed` (file ID -> version).

        Only new and changed files are extracted. A file that cannot be read
        or extracted is reported in `failed` and is not in the index after
        publish. Files in `skip` (uploads that the workers still own) are not touched.
        """
        inventory = self.scan()
        upserts, versions, failed = [], {}, []
        for source in inventory.files.values():
            if source.file_id in skip:
                continue
            if source.outcome == UNREADABLE:
                log.warning("Could not read %s: %s", source.file_id, source.error)
                failed.append({"file_id": source.file_id, "error": source.error})
                continue
            if source.outcome != INDEXABLE:
                continue
            if indexed.get(source.file_id) == source.version:
                versions[source.file_id] = source.version
                continue
            try:
                document, _ = self.extract(self.root / source.file_id)
            except Exception as error:  # One bad file must not stop the whole build.
                log.warning("Could not extract %s: %s", source.file_id, error)
                failed.append({"file_id": source.file_id, "error": type(error).__name__})
                continue
            upserts.append(document)
            versions[source.file_id] = document.source_version
        return IndexPlan(inventory=inventory, upserts=upserts,
                         removals=sorted(indexed.keys() - versions.keys() - skip),
                         versions=versions, failed=failed,
                         added=len(versions.keys() - indexed.keys()),
                         edited=sum(indexed[k] != v for k, v in versions.items() if k in indexed))
