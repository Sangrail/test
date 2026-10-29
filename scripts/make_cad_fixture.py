"""Write the sample CAD drawing in test-repository/: a DXF general arrangement of the
Harbour hangar portal frame, in the AutoCAD R12 ASCII format (AC1009), which any CAD
program or DXF viewer opens.

It has the parts a structural drawing has: frame geometry on layer FRAME, general notes
as TEXT on layer NOTES, and a title block (block TITLEBLOCK, with attribute definitions)
inserted with its attributes filled in: drawing number, revision, approval status, the
frame steel grade and the safe working load of the crane runway. The DXF reader stand-in
reads the notes and the attributes; it never reads the geometry.

All values are invented.

    uv run python scripts/make_cad_fixture.py
"""
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "test-repository/project-harbour/cad/hangar-frame-ga.dxf"

# Title block attributes: tag, value. Tags are upper case without spaces, as CAD requires.
TITLE_BLOCK = [
    ("DRAWING_NO", "HB-S-201"),
    ("TITLE", "HANGAR PORTAL FRAME GENERAL ARRANGEMENT"),
    ("PROJECT", "HARBOUR LOGISTICS HUB"),
    ("REVISION", "C"),
    ("APPROVAL_STATUS", "Approved"),
    ("ISSUE_PURPOSE", "FOR CONSTRUCTION"),
    ("APPROVED_BY", "R. OKAFOR"),
    ("DATE_APPROVED", "2026-09-14"),
    ("FRAME_STEEL_GRADE", "S355J2"),
    ("CRANE_SAFE_WORKING_LOAD", "50 kN"),
    ("NOTICE", "SYNTHETIC TEST DATA - NOT FOR ENGINEERING USE"),
]
NOTES = [
    "GENERAL NOTES",
    "1. ALL DIMENSIONS IN MILLIMETRES UNLESS NOTED OTHERWISE.",
    "2. RAFTERS AND COLUMNS: UNIVERSAL BEAMS TO BS EN 10025-2.",
    "3. HOLDING DOWN BOLTS M24 GRADE 8.8, FOUR PER BASE.",
    "4. CRANE RUNWAY BEAMS SUPPORTED ON COLUMN BRACKETS AT 7.5 M ABOVE FLOOR.",
    "5. SYNTHETIC TEST DATA - NOT FOR ENGINEERING USE.",
]
# A portal frame: two columns, two rafters, crane brackets (mm).
FRAME = [((0, 0), (0, 9000)), ((24000, 0), (24000, 9000)), ((0, 9000), (12000, 11000)),
         ((24000, 9000), (12000, 11000)), ((0, 7500), (600, 7500)), ((24000, 7500), (23400, 7500))]


def pair(code: int, value) -> str:
    return f"{code:>3}\n{value}\n"


def line(start, end, layer="FRAME") -> str:
    return (pair(0, "LINE") + pair(8, layer) + pair(10, f"{start[0]:.1f}") + pair(20, f"{start[1]:.1f}") + pair(30, "0.0")
            + pair(11, f"{end[0]:.1f}") + pair(21, f"{end[1]:.1f}") + pair(31, "0.0"))


def text(x, y, height, value, layer="NOTES") -> str:
    return (pair(0, "TEXT") + pair(8, layer) + pair(10, f"{x:.1f}") + pair(20, f"{y:.1f}") + pair(30, "0.0")
            + pair(40, f"{height:.1f}") + pair(1, value))


def attribute(kind: str, x, y, tag, value, prompt=None) -> str:
    body = (pair(0, kind) + pair(8, "TITLE") + pair(10, f"{x:.1f}") + pair(20, f"{y:.1f}") + pair(30, "0.0")
            + pair(40, "250.0") + pair(1, value))
    if kind == "ATTDEF":
        body += pair(3, prompt)
    return body + pair(2, tag) + pair(70, 0)


def table(name: str, entries: list[str]) -> str:
    return pair(0, "TABLE") + pair(2, name) + pair(70, len(entries)) + "".join(entries) + pair(0, "ENDTAB")


def drawing() -> str:
    header = (pair(0, "SECTION") + pair(2, "HEADER") + pair(9, "$ACADVER") + pair(1, "AC1009")
              + pair(9, "$INSBASE") + pair(10, "0.0") + pair(20, "0.0") + pair(30, "0.0")
              + pair(9, "$EXTMIN") + pair(10, "-1000.0") + pair(20, "-9000.0") + pair(30, "0.0")
              + pair(9, "$EXTMAX") + pair(10, "40000.0") + pair(20, "12000.0") + pair(30, "0.0")
              + pair(9, "$INSUNITS") + pair(70, 4) + pair(0, "ENDSEC"))
    ltype = pair(0, "LTYPE") + pair(2, "CONTINUOUS") + pair(70, 0) + pair(3, "Solid line") + pair(72, 65) \
        + pair(73, 0) + pair(40, "0.0")
    layers = [pair(0, "LAYER") + pair(2, name) + pair(70, 0) + pair(62, colour) + pair(6, "CONTINUOUS")
              for name, colour in (("0", 7), ("FRAME", 1), ("NOTES", 3), ("TITLE", 5))]
    style = pair(0, "STYLE") + pair(2, "STANDARD") + pair(70, 0) + pair(40, "0.0") + pair(41, "1.0") + pair(50, "0.0") \
        + pair(71, 0) + pair(42, "250.0") + pair(3, "txt") + pair(4, "")
    tables = (pair(0, "SECTION") + pair(2, "TABLES") + table("LTYPE", [ltype]) + table("LAYER", layers)
              + table("STYLE", [style]) + pair(0, "ENDSEC"))
    rows = [(26000.0, -1000.0 - 600.0 * i) for i in range(len(TITLE_BLOCK))]
    border = [((25500, -500), (39500, -500)), ((39500, -500), (39500, -7000)), ((39500, -7000), (25500, -7000)),
              ((25500, -7000), (25500, -500))]
    block = (pair(0, "BLOCK") + pair(8, "0") + pair(2, "TITLEBLOCK") + pair(70, 2) + pair(10, "0.0") + pair(20, "0.0")
             + pair(30, "0.0") + pair(3, "TITLEBLOCK") + "".join(line(a, b, "TITLE") for a, b in border)
             + "".join(attribute("ATTDEF", x, y, tag, "", tag.replace("_", " ").title())
                       for (x, y), (tag, _) in zip(rows, TITLE_BLOCK))
             + pair(0, "ENDBLK") + pair(8, "0"))
    blocks = pair(0, "SECTION") + pair(2, "BLOCKS") + block + pair(0, "ENDSEC")
    insert = (pair(0, "INSERT") + pair(8, "TITLE") + pair(66, 1) + pair(2, "TITLEBLOCK") + pair(10, "0.0")
              + pair(20, "0.0") + pair(30, "0.0")
              + "".join(attribute("ATTRIB", x, y, tag, value) for (x, y), (tag, value) in zip(rows, TITLE_BLOCK))
              + pair(0, "SEQEND") + pair(8, "TITLE"))
    notes = "".join(text(0.0, -1500.0 - 500.0 * i, 250.0 if i else 350.0, note) for i, note in enumerate(NOTES))
    entities = pair(0, "SECTION") + pair(2, "ENTITIES") + "".join(line(a, b) for a, b in FRAME) + notes + insert \
        + pair(0, "ENDSEC")
    return header + tables + blocks + entities + pair(0, "EOF")


if __name__ == "__main__":
    PATH.write_text(drawing())
    print("wrote", PATH)
