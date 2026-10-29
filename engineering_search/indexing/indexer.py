"""The indexer: turns the document folder into changes for the search index.

    scan()          find every file, detect its type and version, choose a reader
    plan(indexed)   compare the scan with the index; extract new and changed files
    extract(path)   read one file into a Document: passages, tables and facts

The detector and the reader registry are injected (defaults: ContentDetector
and default_registry()). The indexer reads files. It never writes the index,
and it has no locks or web code. The caller publishes a plan with
index.apply(plan.upserts, plan.removals, files). Thus a test needs only a folder.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import logging
import os
from pathlib import Path
from typing import Mapping

from ..core import Document
from .detect import HEAD_BYTES, ContentDetector, Detector
from .facts import extract_facts
from .inventory import Inventory, SourceFile
from .readers import Reader, ReaderError, ReaderRegistry, default_registry
from .status import CLASSIFIED, INDEXED, READ_ERROR, READER_CRASH

log = logging.getLogger(__name__)


class UnsupportedFileType(ValueError):
    pass


@dataclass(frozen=True)
class IndexPlan:
    inventory: Inventory        # every file, with its status after this plan
    upserts: list[Document]     # new and changed files, extracted
    removals: list[str]         # indexed files that are gone, or can no longer be indexed
    versions: dict[str, str]    # file ID -> version of each file in the index after publish
    failed: list[dict]          # {"file_id", "error"} for files that a reader should have read
    added: int
    edited: int


class Indexer:
    def __init__(self, root: Path, detector: Detector | None = None, registry: ReaderRegistry | None = None):
        self.root = root.resolve()
        self.detector = detector if detector is not None else ContentDetector()
        self.registry = registry if registry is not None else default_registry()

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

    def _classify(self, path: Path, raw: bytes | None = None) -> tuple[SourceFile, Reader | None]:
        """Detect the type of one file and choose its reader. Read and hash it only if a reader fits."""
        file_id = path.relative_to(self.root).as_posix()
        try:
            if raw is None:
                with path.open("rb") as stream:
                    head = stream.read(HEAD_BYTES)
                size = path.stat().st_size
            else:
                head, size = raw[:HEAD_BYTES], len(raw)
        except OSError as error:
            return SourceFile(file_id, self.detector.detect(path, b"").file_type, 0, READ_ERROR,
                              error=type(error).__name__), None
        signature = self.detector.detect(path, head)
        found = SourceFile(file_id, signature.file_type, size, signature.status or CLASSIFIED,
                           format_version=signature.format_version, observation=signature.observation)
        if signature.status:
            return found, None
        selection = self.registry.select(signature)
        if selection.reader is None:
            return replace(found, status=selection.status), None
        manifest = selection.reader.manifest
        try:
            raw = path.read_bytes() if raw is None else raw
        except OSError as error:
            return replace(found, status=READ_ERROR, error=type(error).__name__), None
        return replace(found, size=len(raw), version=hashlib.sha256(raw).hexdigest(),
                       reader=f"{manifest.reader_id}@{manifest.reader_version}"), selection.reader

    def source(self, path: Path, raw: bytes | None = None) -> SourceFile:
        return self._classify(path, raw)[0]

    def scan(self) -> Inventory:
        """Find the files, their types, versions and readers. Does not extract and does not change the index."""
        return Inventory(self.source(path) for path in self.paths())

    def extract(self, path: Path) -> tuple[Document, SourceFile]:
        """Read one file into a Document with its chosen reader.

        Raises UnsupportedFileType if no reader fits, and ReaderError if the reader
        rejects the content. The returned SourceFile has the extraction status.
        """
        raw = path.read_bytes()
        source, reader = self._classify(path, raw)
        if reader is None:
            raise UnsupportedFileType(f"{source.file_type} file: {source.status}")
        extraction = reader.read(source.file_id, source.version, raw)
        document = Document(source.file_id, source.version, extraction.passages, extraction.tables,
                            extract_facts(extraction.tables))
        return (document,
                replace(source, status=extraction.status, warnings=extraction.warnings))

    def plan(self, indexed: Mapping[str, str],
             previous: Mapping[str, SourceFile] | None = None) -> IndexPlan:
        """Scan, then work out what to change in an index that holds `indexed` (file ID -> version).

        Only new and changed files are extracted, files whose extraction status is
        not known (`previous`, the last published inventory), and files whose
        chosen reader or reader version changed. A file that cannot
        be read or extracted is reported in `failed` with its status and is not in the
        index after publish. A file deleted from the folder is removed.
        """
        previous = previous or {}
        inventory = self.scan()
        upserts, versions, failed = [], {}, []
        for source in list(inventory.files.values()):
            if source.status not in INDEXED:
                if source.status == READ_ERROR:
                    log.warning("Could not read %s: %s", source.file_id, source.error)
                    failed.append({"file_id": source.file_id, "error": source.status})
                continue
            known = previous.get(source.file_id)
            if (indexed.get(source.file_id) == source.version and known is not None
                    and known.version == source.version and known.reader == source.reader
                    and known.status in INDEXED - {CLASSIFIED}):
                versions[source.file_id] = source.version
                inventory.record(replace(source, status=known.status, warnings=known.warnings))
                continue
            try:
                document, extracted = self.extract(self.root / source.file_id)
            except ReaderError as error:  # The reader rejected this file: MALFORMED, ENCRYPTED, UNSUPPORTED_VERSION.
                inventory.record(replace(source, status=error.status, error=str(error)[:200]))
                failed.append({"file_id": source.file_id, "error": error.status})
                continue
            except Exception as error:  # One bad file must not stop the whole build.
                log.warning("Could not extract %s: %s", source.file_id, error)
                inventory.record(replace(source, status=READER_CRASH, error=type(error).__name__))
                failed.append({"file_id": source.file_id, "error": READER_CRASH})
                continue
            inventory.record(extracted)
            upserts.append(document)
            versions[source.file_id] = document.source_version
        return IndexPlan(inventory=inventory, upserts=upserts,
                         removals=sorted(indexed.keys() - versions.keys()),
                         versions=versions, failed=failed,
                         added=len(versions.keys() - indexed.keys()),
                         edited=sum(indexed[k] != v for k, v in versions.items() if k in indexed))
