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
class TableRow:
    row: int                     # 1-based data row number within its table
    cells: tuple[str, ...]       # the original cell text, in column order
    line: int                    # source line (Markdown, CSV) or sheet row number (XLSX)
    page: int | None = None      # PDF page, or sheet number for a workbook


@dataclass(frozen=True)
class Table:
    table: int                   # 1-based number of the table in its document
    name: str                    # the heading above it, or the sheet name
    columns: tuple[str, ...]     # the original header text
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class Fact:
    """One typed value from one table cell, with what it is about and where it is.

    Facts are extracted at index time by deterministic rules (indexing/facts.py),
    from table rows only. A fact never comes from free text."""
    table: int
    row: int
    column: str                  # the original column header
    subject: str                 # what the row is about, e.g. "B-104"
    parameter: str               # controlled name, e.g. "allowable_distributed_load"
    role: str                    # capacity, demand, specification, status or measurement
    value: str                   # the original cell text
    number: float | None = None  # parsed number, with its sign
    unit: str | None = None      # the original unit
    si_value: float | None = None
    dimension: str | None = None  # pressure, line load, force, mass, length
    project: str | None = None   # from a project column of the row, if there is one


@dataclass(frozen=True)
class Document:
    file_id: str
    source_version: str
    passages: tuple[Passage, ...]
    tables: tuple[Table, ...] = ()
    facts: tuple[Fact, ...] = ()


class SearchIndex(Protocol):
    """apply publishes all changes atomically, or leaves the old index intact."""
    def versions(self) -> dict[str, str]: ...
    def apply(self, upserts: list[Document], removals: list[str], files: list[dict] | None = None) -> None: ...
    def files(self) -> list[dict]: ...
    def structured(self, files: set[str]) -> dict[str, list[tuple]]: ...
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
