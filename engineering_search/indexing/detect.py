"""File type detection.

A detector names the type of a file, for example "markdown", "pdf" or "jt",
and its format version when the content states one. It does not decide if the
type can be indexed: the reader registry does that. Thus a DWG file is detected
as "dwg" and reported as NO_READER, not lost as an unknown file.

ContentDetector (the default) treats the extension as a hint and checks the
first bytes for the formats that have a signature:

    PDF    "%PDF-1.7"                        -> pdf, version 1.7
    XLSX   ZIP with xl/workbook.xml          -> excel
    DOCX   ZIP with word/document.xml        -> word
    JT     "Version 9.5 JT" in the 80-byte header -> jt, version 9.5
    DXF    "0 SECTION" pairs, $ACADVER AC1009      -> dxf, version AC1009 (ASCII);
           "AutoCAD Binary DXF"                    -> dxf, version "binary"

When the content has a signature, the content decides the type. When the
extension claims a signed format but the signature is absent, the status is
FORMAT_MISMATCH (or INVALID_HEADER if the header starts right but is broken).
Text formats (Markdown, CSV) have no signature; the extension decides.

The JT probe reads the version string only. It is not a JT parser, and a
detected version says nothing about whether a reader can read the file.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping, Protocol
import zipfile

from .status import FORMAT_MISMATCH, INVALID_HEADER

MARKDOWN = "markdown"
PDF = "pdf"
CSV = "csv"
EXCEL = "excel"
WORD = "word"
JT = "jt"
DXF = "dxf"
UNKNOWN = "unknown"

# Extension -> file type. The registry decides which types have a reader.
EXTENSIONS: Mapping[str, str] = {
    ".md": MARKDOWN,
    ".pdf": PDF,
    ".csv": CSV,
    ".txt": "text",
    ".docx": WORD,
    ".xlsx": EXCEL,
    ".dwg": "dwg",
    ".dxf": DXF,
    ".jt": JT,
    ".catpart": "catia",
    ".catproduct": "catia",
    ".catdrawing": "catia",
    ".ifc": "ifc",
}

HEAD_BYTES = 512  # the most a detector reads from a file
PDF_HEADER = re.compile(rb"^%PDF-(\d+\.\d+)")
# The JT file header starts with an 80-character version string, e.g.
# "Version 9.5 JT" padded with spaces. Checked against public descriptions of
# the format only; confirm against the Siemens JT specification before production.
JT_HEADER = re.compile(rb"^Version (\d+)\.(\d+)\s+JT")
# An ASCII DXF starts with group code 0 and SECTION (after optional 999 comments);
# the HEADER section names the release in $ACADVER, for example AC1009 (R12).
DXF_START = re.compile(rb"^\s*(?:999\r?\n[^\n]*\n\s*)*0\r?\nSECTION\r?\n")
DXF_VERSION = re.compile(rb"\$ACADVER\r?\n\s*1\r?\n(AC\d{4})")
DXF_BINARY = b"AutoCAD Binary DXF"
SIGNED = {PDF, EXCEL, WORD, JT, DXF}  # file types whose content has a signature
OOXML = {"xl/workbook.xml": EXCEL, "word/document.xml": WORD}


@dataclass(frozen=True)
class FileSignature:
    file_type: str
    format_version: str | None = None
    status: str | None = None     # FORMAT_MISMATCH or INVALID_HEADER; None when the type is clear
    observation: str = ""         # short, safe evidence for the coverage report


class Detector(Protocol):
    def detect(self, path: Path, head: bytes) -> FileSignature:
        """Name the type of path. head is its first HEAD_BYTES bytes."""
        ...


class ExtensionDetector:
    """Detect the file type from the file extension only. Case does not matter."""

    def __init__(self, extensions: Mapping[str, str] = EXTENSIONS):
        self.extensions = {suffix.casefold(): file_type for suffix, file_type in extensions.items()}

    def detect(self, path: Path, head: bytes = b"") -> FileSignature:
        return FileSignature(self.extensions.get(path.suffix.casefold(), UNKNOWN))


class ContentDetector:
    """The extension as a hint, checked against the content signature."""

    def __init__(self, extensions: Mapping[str, str] = EXTENSIONS):
        self.by_extension = ExtensionDetector(extensions)

    def detect(self, path: Path, head: bytes) -> FileSignature:
        hint = self.by_extension.detect(path).file_type
        found = probe(path, head)
        if found is not None:
            if found.status and hint in OOXML.values():  # an .xlsx or .docx whose ZIP is broken
                return FileSignature(hint, None, found.status, found.observation)
            if hint in SIGNED and found.file_type != hint:
                return FileSignature(hint, None, FORMAT_MISMATCH,
                                     f"extension says {hint}, content is {found.file_type}")
            return found
        if hint in SIGNED:
            broken = (hint == PDF and head.startswith(b"%PDF")) or (hint == JT and head.startswith(b"Version"))
            return FileSignature(hint, None, INVALID_HEADER if broken else FORMAT_MISMATCH,
                                 f"no {hint} signature in the first bytes")
        return FileSignature(hint)


def probe(path: Path, head: bytes) -> FileSignature | None:
    """The type that the content signature shows, or None if it shows none."""
    if match := PDF_HEADER.match(head):
        version = match.group(1).decode()
        return FileSignature(PDF, version, observation=f"%PDF-{version}")
    if match := JT_HEADER.match(head[:80]):
        version = f"{int(match.group(1))}.{int(match.group(2))}"
        return FileSignature(JT, version, observation=f"header 'Version {version} JT'")
    if head.startswith(DXF_BINARY):
        return FileSignature(DXF, "binary", observation="binary DXF sentinel")
    if DXF_START.match(head):
        version = DXF_VERSION.search(head)
        found = version.group(1).decode() if version else None
        return FileSignature(DXF, found, observation=f"DXF sections, $ACADVER {found or 'not in the first bytes'}")
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
        except (zipfile.BadZipFile, OSError):
            return FileSignature("zip", status=INVALID_HEADER, observation="broken ZIP container")
        for member, file_type in OOXML.items():
            if member in names:
                return FileSignature(file_type, observation=f"ZIP with {member}")
        return FileSignature("zip", observation="ZIP container")
    return None
