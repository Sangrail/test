"""Readers: one class per way of reading a file type, listed in registry.py.

    base.py       ReaderManifest, Capabilities, Extraction, ReaderError, Reader
    text.py       split lines into passages (shared)
    markdown.py   MarkdownReader (text and pipe tables)
    pdf.py        PdfTextReader (pypdf text layer)
    csv.py        CsvReader (one table, a passage per row)
    xlsx.py       XlsxReader (openpyxl; a table per sheet, a passage per row)
    registry.py   ReaderRegistry and default_registry(), the factory
"""
from .base import Capabilities, Extraction, Reader, ReaderError, ReaderManifest
from .csv import CsvReader
from .markdown import MarkdownReader
from .pdf import PdfTextReader
from .xlsx import XlsxReader
from .registry import ReaderRegistry, Selection, default_registry

__all__ = ["Capabilities", "Extraction", "Reader", "ReaderError", "ReaderManifest",
           "CsvReader", "MarkdownReader", "PdfTextReader", "XlsxReader", "ReaderRegistry", "Selection", "default_registry"]
