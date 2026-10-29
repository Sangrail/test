"""Indexing: from the document folder to the passages in the search index.

This package is one of the two lines of the service. The other line is
searching (query.py, answer.py, store.py lookups and service.search).

    detect.py     file type detection (by extension in the MVP)
    inventory.py  every file found by a scan, with its type and outcome
    readers.py    one reader for each file type that can be indexed
    indexer.py    Indexer: scan, plan the index changes, extract one file

The package reads files only. It does not import the store, the service or
the web app. SearchService publishes the Indexer's plan to the index.
"""
from .detect import EXTENSIONS, MARKDOWN, PDF, UNKNOWN, Detector, ExtensionDetector
from .indexer import Indexer, IndexPlan, UnsupportedFileType
from .inventory import INDEXABLE, UNREADABLE, UNSUPPORTED, Inventory, SourceFile
from .readers import READERS, Reader

__all__ = ["EXTENSIONS", "MARKDOWN", "PDF", "UNKNOWN", "Detector", "ExtensionDetector",
           "Indexer", "IndexPlan", "UnsupportedFileType",
           "INDEXABLE", "UNREADABLE", "UNSUPPORTED", "Inventory", "SourceFile",
           "READERS", "Reader"]
