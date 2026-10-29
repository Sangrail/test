"""Write the structured test fixtures in test-repository/: schedules as CSV, XLSX and
Markdown tables, a cross-project register, a scanned PDF and synthetic JT headers.

All values are invented. They are chosen so that the question "Which S355
components have an allowable load under 5 kN/m²?" has a known answer, with traps:
a concrete slab with a low imposed (demand) load, a floor design load in prose,
a capacity just above 5, a formula with no cached value, a file only some users
may read, and a register with rows for several projects.

    uv run python scripts/make_structured_fixtures.py
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1] / "test-repository"
BANNER = "SYNTHETIC TEST DATA - not for engineering use."

TEXT_FILES = {
    "project-harbour/harbour-component-schedule.csv": """\
Component,Type,Location,Material grade,Allowable UDL (kN/m²),Design imposed load (kN/m²),Status
B-101,Beam,Level 1 grid A,S275,5.5,,Approved
B-104,Beam,Level 2 grid C,S355J2,4.5,,Approved
B-105,Beam,Level 2 grid D,S355,6.0,,Approved
B-106,Beam,Mezzanine edge,S355J2+N,3.5,,Pending
C-201,Column,Grid C2,S355,,,Approved
F-021,Floor slab,Level 1,C30/37,,3.2,Approved
F-022,Floor slab,Level 2,C30/37,7.5,2.5,Approved
""",
    "project-harbour/harbour-design-basis.md": f"""\
# Harbour logistics hub design basis

{BANNER}

## Floor loading

The floor design load is 4.0 kN/m² on all warehouse slabs.

## Mezzanine members

| Member | Steel grade | Allowable UDL |
|---|---|---|
| M-401 | S355 | 4.2 kN/m² |
| M-402 | S275 | 4.0 kN/m² |

## Ground conditions

| Location | Predicted settlement (mm) |
|---|---|
| Grid A1 | -12 |
| Grid C4 | -8 |
""",
    "project-harbour/cad/FIXTURES.md": f"""\
# CAD fixtures for the coverage report

{BANNER}

The .jt files in this folder are NOT valid JT files. hangar-frame.jt holds only
a synthetic 80-character header ("Version 10.0 JT") so that the content detector
can be tested. old-export.jt is a text note saved with a .jt extension. No JT
content is read from either file; the coverage report lists them as gaps.
""",
    "registers/component-register.csv": """\
Project,Component,Material grade,Allowable UDL (kN/m²),Status
Harbour,B-104,S355J2,4.5,Approved
Cedar,CB-12,S355,4.8,Approved
Cedar,CB-14,S355,5.6,Approved
Riverside,RG-02,S355J2+N,3.9,Pending
""",
    "project-harbour/cad/old-export.jt": "Export note: this geometry was re-exported as STEP. Not a JT file.\n",
}


def roof_schedule() -> bytes:
    """One sheet of roof members. R-313's load is a formula with no cached value, as
    a script-written workbook has: the reader must leave it empty and say so."""
    book = Workbook()
    sheet = book.active
    sheet.title = "Roof members"
    sheet.append(["Member", "Material grade", "Allowable load (kN/m²)", "Roof imposed load (kN/m²)", "Status"])
    for row in (["R-310", "S355", 3.8, 1.5, "Approved"], ["R-311", "S355", 5.2, 1.5, "Approved"],
                ["R-312", "S460", 4.0, 1.5, "Approved"], ["R-313", "S355", "=3.5*1", 1.5, "Pending"]):
        sheet.append(row)
    book.properties.created = book.properties.modified = datetime(2026, 10, 29)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def scanned_pdf() -> bytes:
    """Two pages with no text layer, like a scan without OCR."""
    writer = PdfWriter()
    writer.add_blank_page(595, 842)
    writer.add_blank_page(595, 842)
    writer.add_metadata({"/Title": "Harbour site survey (scan)"})
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def jt_header() -> bytes:
    header = "Version 10.0 JT".ljust(80).encode()
    return header + b"\nSYNTHETIC HEADER-ONLY FIXTURE: NOT A VALID JT FILE\n"


def main():
    files = {**{name: text.encode() for name, text in TEXT_FILES.items()},
             "project-harbour/harbour-roof-schedule.xlsx": roof_schedule(),
             "project-harbour/scans/site-survey-scan.pdf": scanned_pdf(),
             "project-harbour/cad/hangar-frame.jt": jt_header()}
    for name, content in files.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"wrote {name} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
