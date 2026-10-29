"""PDF: the text layer of each page, with pypdf. No OCR: a scanned page gives no text."""
from __future__ import annotations

from io import BytesIO
import logging
import re

from ..detect import PDF
from ..status import ENCRYPTED, INDEXED_PARTIAL, MALFORMED, NO_TEXT_LAYER
from .base import Capabilities, Extraction, ReaderError, ReaderManifest
from .text import split_passages

# The assumption for PDF headings is less ideal: numbered headings such as
# "3.1 Roof load limit" or "3.0 DESIGN PARAMETERS". No comma, colon or full stop,
# so a wrapped line such as "14 May 2024, ..." is not a heading.
PDF_HEADING = re.compile(r"^(\d+(?:\.\d+)*\s+[A-Z][A-Za-z][^,.:;]{0,60}?)\s*$")
PDF_MAX_LINES = 15


class PdfTextReader:
    manifest = ReaderManifest("pdf-text-pypdf", "1", (PDF,), Capabilities(text=True),
                              format_versions=("1.", "2."), dependencies=("pypdf",))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        logging.getLogger("pypdf").setLevel(logging.ERROR)  # Harmless font warnings in many real PDFs.
        try:
            document = PdfReader(BytesIO(raw))
            if document.is_encrypted:
                raise ReaderError(ENCRYPTED, "encrypted PDF")
            pages = [page.extract_text() or "" for page in document.pages]
        except PdfReadError as error:
            raise ReaderError(MALFORMED, type(error).__name__) from None
        passages = tuple(passage for number, text in enumerate(pages, start=1)
                         for passage in split_passages(file_id, version, text.splitlines(), PDF_HEADING,
                                                       page=number, max_lines=PDF_MAX_LINES))
        empty = [number for number, text in enumerate(pages, start=1) if not text.strip()]
        if not passages:
            return Extraction((), NO_TEXT_LAYER, (f"no text on any of {len(pages)} pages",))
        if empty:
            return Extraction(passages, INDEXED_PARTIAL,
                              (f"no text layer on pages {', '.join(map(str, empty))}",))
        return Extraction(passages)
