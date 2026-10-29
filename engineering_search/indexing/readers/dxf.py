"""DXF: the text and the title-block attributes of an ASCII drawing exchange file.

A stand-in for a CAD connector (the brief says connectors extract metadata, text and
properties from supported files). It reads the two places where a drawing states
parameters in words: the TEXT and MTEXT entities (general notes) and the attributes of
block references (ATTRIB), which is how a title block carries the drawing number, the
revision, the approval status and values such as a safe working load. Geometry is not
read.

DXF is a list of group-code and value pairs, two lines each. The reader cites the line
of the value in the file, so the quoted evidence is exactly what that line holds:
    - each note is a passage, headed by its layer;
    - each block reference with attributes is a Property/Value table, named after the
      drawing number and revision when the title block has them. The property is the
      tag with its underscores as spaces, so the fact rules can read it;
    - each attribute is also a passage, headed by the table name, whose text is the
      tag and the value as written ("CRANE_SAFE_WORKING_LOAD | 50 kN", like the cells
      of a spreadsheet row). It cites the line of the value; the tag is in the same
      ATTRIB entity, a few lines away.
Only entities in the ENTITIES section are read; a block's own definitions (ATTDEF
defaults) are templates, not the drawing's values. Binary DXF is not read.
"""
from __future__ import annotations

import re

from ...core import Passage, Table, TableRow
from ..detect import DXF
from ..status import MALFORMED, NO_EXTRACTABLE_CONTENT
from .base import Capabilities, Extraction, ReaderError, ReaderManifest

BINARY = b"AutoCAD Binary DXF"
# MTEXT formatting: \P is a new paragraph; {\f...;}, \H...; and the like are formatting.
MTEXT_PARAGRAPH = re.compile(r"\\P", re.I)
MTEXT_CODE = re.compile(r"\\[A-OQ-Za-oq-z][^;\\{}]*;|[{}]")


def pairs(text: str) -> list[tuple[int, str, int]]:
    """(group code, value, line number of the value), for every pair in the file."""
    lines = text.splitlines()
    if len(lines) % 2:
        lines = lines[:-1]  # A trailing blank line after EOF.
    found = []
    for i in range(0, len(lines), 2):
        try:
            code = int(lines[i].strip())
        except ValueError:
            raise ReaderError(MALFORMED, f"line {i + 1} is not a group code") from None
        found.append((code, lines[i + 1].strip(), i + 2))
    return found


def entities(found: list[tuple[int, str, int]]) -> list[list[tuple[int, str, int]]]:
    """The entities of the ENTITIES section, each as its list of pairs, starting with code 0."""
    result, section, current = [], None, None
    for index, (code, value, line) in enumerate(found):
        if code == 0:
            if current is not None:
                result.append(current)
                current = None
            if value == "SECTION":
                section = next((v for c, v, _ in found[index + 1:index + 2] if c == 2), None)
            elif value == "ENDSEC":
                section = None
            elif section == "ENTITIES":
                current = [(code, value, line)]
        elif current is not None:
            current.append((code, value, line))
    return result


def first(entity, code: int) -> tuple[str, int] | None:
    return next(((v, line) for c, v, line in entity if c == code), None)


def label(tag: str) -> str:
    words = tag.replace("_", " ").strip().lower()
    return words[:1].upper() + words[1:]


class DxfTextReader:
    manifest = ReaderManifest("dxf-text", "1", (DXF,), Capabilities(text=True, tables=True, metadata=True))

    def read(self, file_id: str, version: str, raw: bytes) -> Extraction:
        if raw.startswith(BINARY):
            raise ReaderError(MALFORMED, "binary DXF is not read by this stand-in")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")  # Drawings before AutoCAD 2007 use the ANSI code page.
        passages: list[Passage] = []
        blocks: list[tuple[str, list[tuple[str, str, int]]]] = []  # tag, value, value line
        for entity in entities(pairs(text)):
            kind = entity[0][1]
            layer = (first(entity, 8) or ("0", 0))[0]
            if kind == "TEXT" and (value := first(entity, 1)) and value[0]:
                passages.append(Passage(file_id, version, f"Drawing notes (layer {layer})", value[1], value[1], value[0]))
            elif kind == "MTEXT":
                chunks = [(v, line) for c, v, line in entity if c in (3, 1)]
                if chunks:
                    body = MTEXT_CODE.sub("", MTEXT_PARAGRAPH.sub("\n", "".join(v for v, _ in chunks))).strip()
                    if body:
                        passages.append(Passage(file_id, version, f"Drawing notes (layer {layer})",
                                                chunks[0][1], chunks[-1][1], body))
            elif kind == "INSERT":
                blocks.append(((first(entity, 2) or ("", 0))[0], []))
            elif kind == "ATTRIB" and blocks and (tag := first(entity, 2)) and (value := first(entity, 1)):
                blocks[-1][1].append((tag[0], value[0], value[1]))
        tables = []
        for name, attributes in blocks:
            if not attributes:
                continue
            values = {tag.upper(): value for tag, value, _ in attributes}
            number, revision = values.get("DRAWING_NO"), values.get("REVISION")
            table_name = (f"Drawing {number}" + (f" rev {revision}" if revision else "") + " title block"
                          if number else f"Block {name} attributes")
            rows = tuple(TableRow(i, (label(tag), value), line) for i, (tag, value, line) in enumerate(attributes, start=1))
            tables.append(Table(len(tables) + 1, table_name, ("Property", "Value"), rows))
            passages += [Passage(file_id, version, table_name, line, line, f"{tag} | {value}")
                         for tag, value, line in attributes if value]
        if not passages:
            return Extraction((), NO_EXTRACTABLE_CONTENT)
        return Extraction(tuple(sorted(passages, key=lambda p: p.start_line)), tables=tuple(tables))
