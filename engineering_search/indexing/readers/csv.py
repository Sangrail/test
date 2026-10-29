"""CSV: the file as one logical table (rows in the shared table_rows store; no database
table per file), and one passage per data row for text search.

The first non-empty row is the header. Each passage is the row's original
line, with the header line as its heading, so the column names are searchable
and an answer can cite the exact line.
"""
from __future__ import annotations

import csv
import io

from ...core import Passage, Table, TableRow
from ..detect import CSV
from ..status import INDEXED_PARTIAL, MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest


class CsvReader:
    manifest = ReaderManifest("csv-table", "1", (CSV,), Capabilities(text=True, tables=True))

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
        records = [(number, row) for number, row in enumerate(csv.reader(io.StringIO(text), dialect), start=1)
                   if any(cell.strip() for cell in row)]
        if not records:
            return Extraction((), NO_EXTRACTABLE_CONTENT)
        header_line, header = records[0]
        columns = tuple(cell.strip() for cell in header)
        rows, passages, short = [], [], []
        for number, row in records[1:]:
            if len(row) != len(columns):
                short.append(number)
            cells = tuple(cell.strip() for cell in row) + ("",) * (len(columns) - len(row))
            rows.append(TableRow(len(rows) + 1, cells[:len(columns)], number))
            # csv.reader line numbers match the text lines while no quoted cell spans lines.
            passages.append(Passage(file_id, version, lines[header_line - 1], number, number, lines[number - 1]))
        table = Table(1, file_id.rsplit("/", 1)[-1], columns, tuple(rows))
        if short:
            return Extraction(tuple(passages), INDEXED_PARTIAL,
                              (f"rows with a different number of cells than the header: lines "
                               f"{', '.join(map(str, short[:20]))}",), (table,))
        return Extraction(tuple(passages), tables=(table,))
