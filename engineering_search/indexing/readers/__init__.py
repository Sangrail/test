"""Readers: one class per way of reading a file type, listed in registry.py.

    base.py       ReaderManifest, Capabilities, Extraction, ReaderError, Reader
    text.py       split lines into passages (shared)
    markdown.py   MarkdownReader
    pdf.py        PdfTextReader (pypdf text layer)
    registry.py   ReaderRegistry and default_registry(), the factory
"""
from .base import Capabilities, Extraction, Reader, ReaderError, ReaderManifest
from .markdown import MarkdownReader
from .pdf import PdfTextReader
from .registry import ReaderRegistry, Selection, default_registry

__all__ = ["Capabilities", "Extraction", "Reader", "ReaderError", "ReaderManifest",
           "MarkdownReader", "PdfTextReader", "ReaderRegistry", "Selection", "default_registry"]
