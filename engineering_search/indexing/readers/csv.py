"""CSV: the file as one logical table (rows in the shared table_rows store; no database
table per file), and one passage per data row for text search.

The first non-empty row is the header. Each passage is the row as written,
with the header as its heading, so the column names are searchable and an
answer can cite the exact lines. A quoted cell may hold a line break: the row
then spans several lines of the file, is still one row, and cites all its
lines; its passage is those lines joined with spaces, so it reads as one line.
"""
from __future__ import annotations

import csv
import io

from ...core import Passage, Table, TableRow
from ..detect import CSV
from ..status import INDEXED_PARTIAL, MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest


class CsvReader:
    manifest = ReaderManifest("csv-table", "2", (CSV,), Capabilities(text=True, tables=True))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        try:
            text = raw.decode("utf-8-sig")  # A byte order mark from Excel is dropped.
        except UnicodeDecodeError:
            raise ReaderError(MALFORMED, "not UTF-8 text") from None
        lines = text.splitlines()
        try:
            dialect = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        records = []  # (first line, last line, cells); csv.reader counts the lines a quoted line break adds
        reader, last = csv.reader(io.StringIO(text), dialect), 0
        for row in reader:
            first, last = last + 1, reader.line_num
            if any(cell.strip() for cell in row):
                records.append((first, last, row))
        if not records:
            return Extraction((), NO_EXTRACTABLE_CONTENT)

        def written(first: int, last: int) -> str:
            return " ".join(lines[first - 1:last])

        header_first, header_last, header = records[0]
        columns = tuple(cell.strip() for cell in header)
        rows, passages, short = [], [], []
        for first, last, row in records[1:]:
            if len(row) != len(columns):
                short.append(first)
            cells = tuple(cell.strip() for cell in row) + ("",) * (len(columns) - len(row))
            rows.append(TableRow(len(rows) + 1, cells[:len(columns)], first))
            passages.append(Passage(file_id, version, written(header_first, header_last), first, last,
                                    written(first, last)))
        table = Table(1, file_id.rsplit("/", 1)[-1], columns, tuple(rows))
        if short:
            return Extraction(tuple(passages), INDEXED_PARTIAL,
                              (f"rows with a different number of cells than the header: lines "
                               f"{', '.join(map(str, short[:20]))}",), (table,))
        return Extraction(tuple(passages), tables=(table,))
