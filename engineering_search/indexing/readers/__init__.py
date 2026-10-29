"""Readers: one class per way of reading a file type, listed in registry.py.

These readers are stand-ins. The brief says connectors and APIs already extract
metadata, text and properties from supported files; the MVP reads Markdown, PDF text,
CSV, XLSX and the notes and title block of a DXF drawing itself, only to show the
flow from file to cited answer. A connector
plugs in here as one more reader that returns an Extraction (ADR 0001).

    base.py       ReaderManifest, Capabilities, Extraction, ReaderError, Reader
    text.py       split lines into passages (shared)
    markdown.py   MarkdownReader (text and pipe tables)
    pdf.py        PdfTextReader (pypdf text layer)
    csv.py        CsvReader (one table, a passage per row)
    xlsx.py       XlsxReader (openpyxl; a table per sheet, a passage per row)
    dxf.py        DxfTextReader (ASCII DXF notes, and title-block attributes as a table)
    registry.py   ReaderRegistry and default_registry(), the factory
"""
from .base import Capabilities, Extraction, Reader, ReaderError, ReaderManifest
from .csv import CsvReader
from .dxf import DxfTextReader
from .markdown import MarkdownReader
from .pdf import PdfTextReader
from .xlsx import XlsxReader
from .registry import ReaderRegistry, Selection, default_registry

__all__ = ["Capabilities", "Extraction", "Reader", "ReaderError", "ReaderManifest",
           "CsvReader", "DxfTextReader", "MarkdownReader", "PdfTextReader", "XlsxReader", "ReaderRegistry", "Selection", "default_registry"]
