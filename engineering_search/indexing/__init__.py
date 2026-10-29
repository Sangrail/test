"""Indexing: from the document folder to the passages in the search index.

This package is one of the two lines of the service. The other line is
searching (query.py, answer.py, store.py lookups and service.search).

    detect.py     file type and format version, from the extension and the first bytes
    status.py     the status of each file: classification, extraction, gaps
    inventory.py  every file found by a scan, with its type, version and status
    readers/      the readers, their manifests, and the registry that lists them
    indexer.py    Indexer: scan, plan the index changes, extract one file
    coverage.py   the coverage report: what was read, what was not, and why

The package reads files only. It does not import the store, the service or
the web app. SearchService publishes the Indexer's plan to the index.
"""
from .coverage import coverage_report
from .detect import (CSV, EXCEL, EXTENSIONS, JT, MARKDOWN, PDF, UNKNOWN, ContentDetector, Detector,
                     ExtensionDetector, FileSignature)
from .indexer import Indexer, IndexPlan, UnsupportedFileType
from .inventory import Inventory, SourceFile
from .readers import ReaderRegistry, default_registry
from . import status

__all__ = ["coverage_report", "CSV", "EXCEL", "EXTENSIONS", "JT", "MARKDOWN", "PDF", "UNKNOWN",
           "ContentDetector", "Detector", "ExtensionDetector", "FileSignature",
           "Indexer", "IndexPlan", "UnsupportedFileType", "Inventory", "SourceFile",
           "ReaderRegistry", "default_registry", "status"]
