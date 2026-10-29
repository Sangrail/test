"""XLSX workbooks with openpyxl: one table per sheet, one passage per data row.

The first non-empty row of a sheet is its header. A cell value is the value
that Excel cached when the file was last saved. A formula without a cached
value (a file written by a tool that does not calculate) is not evaluated: the
cell is left empty and the file is INDEXED_PARTIAL with a warning naming the cells.
For a workbook, a passage's page is the sheet number and its lines are sheet rows.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from zipfile import BadZipFile

from ...core import Passage, Table, TableRow
from ..detect import EXCEL
from ..status import ENCRYPTED, INDEXED_FULL, INDEXED_PARTIAL, MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest


def display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip()


class XlsxReader:
    manifest = ReaderManifest("xlsx-openpyxl", "1", (EXCEL,), Capabilities(text=True, tables=True),
                              dependencies=("openpyxl",))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        from openpyxl import load_workbook

        try:
            values = load_workbook(BytesIO(raw), data_only=True, read_only=True)
            formulas = load_workbook(BytesIO(raw), data_only=False, read_only=True)
        except BadZipFile:
            raise ReaderError(MALFORMED, "not a readable workbook") from None
        except KeyError as error:  # A ZIP without the workbook parts, or an encrypted workbook.
            raise ReaderError(ENCRYPTED if "EncryptedPackage" in str(error) else MALFORMED, str(error)[:100]) from None
        tables, passages, warnings, missing = [], [], [], []
        for sheet_number, sheet in enumerate(values.worksheets, start=1):
            if sheet.sheet_state != "visible":
                warnings.append(f"hidden sheet '{sheet.title}' was read")
            formula_rows = formulas[sheet.title].iter_rows()
            header, rows = None, []
            for row_cells, formula_cells in zip(sheet.iter_rows(), formula_rows):
                texts = []
                for cell, source in zip(row_cells, formula_cells):
                    text = display(cell.value)
                    if not text and isinstance(source.value, str) and source.value.startswith("="):
                        missing.append(f"{sheet.title}!{source.coordinate}")
                    texts.append(text)
                if not any(texts):
                    continue
                line = row_cells[0].row
                if header is None:
                    header = tuple(texts)
                    continue
                cells = tuple(texts[:len(header)]) + ("",) * (len(header) - len(texts))
                rows.append(TableRow(len(rows) + 1, cells, line, sheet_number))
                passages.append(Passage(file_id, version, f"{sheet.title}: {' | '.join(header)}", line, line,
                                        " | ".join(cells), sheet_number))
            if header is not None:
                tables.append(Table(len(tables) + 1, sheet.title, header, tuple(rows)))
        if missing:
            warnings.append(f"formulas without a cached value, left empty: {', '.join(missing[:20])}")
        if not passages:
            return Extraction((), NO_EXTRACTABLE_CONTENT, tuple(warnings), tuple(tables))
        return Extraction(tuple(passages), INDEXED_PARTIAL if missing else INDEXED_FULL,
                          tuple(warnings), tuple(tables))
