"""The evidence model and the replaceable boundaries.

No dependency on the web framework. Finding and reading files is in the
indexing package (engineering_search/indexing/)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Protocol


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


@dataclass(frozen=True)
class Passage:
    file_id: str
    source_version: str
    heading: str
    start_line: int
    end_line: int
    text: str
    page: int | None = None  # 1-based page number for PDF; None for Markdown


@dataclass(frozen=True)
class Document:
    file_id: str
    source_version: str
    passages: tuple[Passage, ...]


class SearchIndex(Protocol):
    """apply publishes all changes atomically, or leaves the old index intact."""
    def versions(self) -> dict[str, str]: ...
    def apply(self, upserts: list[Document], removals: list[str]) -> None: ...
    def upsert(self, document: Document) -> None: ...
    def remove(self, file_id: str) -> None: ...
    def passage_count(self) -> int: ...
    def search(self, query: str, limit: int) -> tuple[list[Passage], int]: ...
    def candidates(self, query: str, files: set[str] | None = None) -> list[Passage]: ...
    def document_matches(self, query) -> dict[str, int]: ...
    def passages(self, file_id: str, page: int | None = None) -> list[Passage]: ...


class AuditStore(Protocol):
    """append must return only after committing the event durably."""
    def append(self, event: dict) -> None: ...


class AuditReader(Protocol):
    """Read newest committed events first within a fixed upper event ID."""
    def read_page(self, page: int, limit: int, snapshot_id: int | None = None) -> dict: ...


def evidence_manifest(passages: list[Passage]) -> list[dict]:
    # No raw document content in routine audit events.
    return [{k: v for k, v in asdict(p).items() if k not in ("text", "heading")}
            for p in passages]
