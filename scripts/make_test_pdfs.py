"""Write the synthetic test PDFs in test-repository/.

The PDFs have a real text layer, several pages, numbered section headings and
tables set in a fixed-width font. No PDF library is needed to create them.
Output is deterministic: running the script twice gives identical files.

    uv run python scripts/make_test_pdfs.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "test-repository"
BANNER = "SYNTHETIC TEST DATA - NOT FOR ENGINEERING USE"

# Each page is a list of (style, text). Styles: title, h (heading), p (prose), t (table row), gap.
DOCUMENTS = {
    "project-riverside/riverside-footbridge-load-rating.pdf": {
        "title": "Riverside Footbridge RFB-01 - Load Rating Report",
        "footer": "RFB-LR-003 Revision C",
        "pages": [
            [("title", "Riverside Footbridge RFB-01 - Load Rating Report"),
             ("p", "Document RFB-LR-003, Revision C, March 2024. Project: Riverside."),
             ("p", BANNER), ("gap", ""),
             ("h", "1 Introduction"),
             ("p", "This report rates the Riverside footbridge RFB-01 for pedestrian and"),
             ("p", "maintenance vehicle use after the 2023 principal inspection."),
             ("gap", ""),
             ("h", "2 Structure description"),
             ("p", "Two spans of 18.5 m. Deck: 200 mm reinforced concrete slab, concrete"),
             ("p", "class C32/40. Main girders: welded plate girders, steel grade S355J2+N"),
             ("p", "to EN 10025-2. Bearings: elastomeric, type EB-3.")],
            [("h", "3 Load rating summary"),
             ("t", "Load case            Rating factor   Limit          Result"),
             ("t", "Pedestrian crowd     1.32            5.0 kN/m²      Pass"),
             ("t", "Maintenance vehicle  1.08            3.5 t gross    Pass"),
             ("t", "Emergency vehicle    0.86            12 t gross     Fail - restricted"),
             ("gap", ""),
             ("h", "4 Load limit"),
             ("p", "The maximum permitted pedestrian live load is 5.0 kN/m². Vehicles above"),
             ("p", "3.5 t gross weight are prohibited. Weight limit signs are required at"),
             ("p", "both abutments.")],
            [("h", "5 Approval"),
             ("p", "Approval status: APPROVED by the Riverside Bridge Authority on"),
             ("p", "14 May 2024, reference RBA-2024-117. The approval is subject to the"),
             ("p", "vehicle restriction in section 4."),
             ("gap", ""),
             ("h", "6 Next inspection"),
             ("p", "The next principal inspection is due in May 2026.")],
        ],
    },
    "project-northgate/northgate-warehouse-structural-calculations.pdf": {
        "title": "Northgate Distribution Warehouse - Structural Calculations",
        "footer": "NDW-CALC-001 Revision B",
        "pages": [
            [("title", "Northgate Distribution Warehouse - Structural Calculations"),
             ("p", "Document NDW-CALC-001, Revision B, January 2024. Project: Northgate."),
             ("p", BANNER), ("gap", ""),
             ("h", "1 Scope"),
             ("p", "Structural design of a single-storey steel portal frame warehouse with"),
             ("p", "an internal storage mezzanine and a two-storey office block."),
             ("gap", ""),
             ("h", "2 Design standards"),
             ("p", "Eurocodes EN 1990, EN 1991 and EN 1993 with the UK National Annexes.")],
            [("h", "3 Design loads"),
             ("t", "Area                 Imposed load    Notes"),
             ("t", "Roof (no access)     0.6 kN/m²       Category H"),
             ("t", "Mezzanine floor      7.5 kN/m²       Storage, category E1"),
             ("t", "Office floor         2.5 kN/m²       Category B"),
             ("t", "Roof snow            0.5 kN/m²       Characteristic value"),
             ("gap", ""),
             ("h", "3.1 Roof load limit"),
             ("p", "The roof is designed for an imposed load of 0.6 kN/m². It is not"),
             ("p", "designed for plant or solar panels. Any additional roof load needs a"),
             ("p", "new structural assessment.")],
            [("h", "4 Materials"),
             ("t", "Element              Specification"),
             ("t", "Portal frames        S355 hot-rolled structural steel"),
             ("t", "Purlins              S390GD cold-formed galvanised steel"),
             ("t", "Floor slab           C30/37 concrete with B500B reinforcement"),
             ("gap", ""),
             ("h", "4.1 Foundations"),
             ("p", "Pad foundations. Allowable bearing pressure: 150 kPa, from the"),
             ("p", "geotechnical report NDW-GI-02.")],
            [("h", "5 Compliance"),
             ("p", "Building control approval status: PENDING. Submitted on 2 February"),
             ("p", "2024, reference BC-NDW-0042. The fire engineering review is still"),
             ("p", "outstanding.")],
        ],
    },
    "registers/material-approval-register.pdf": {
        "title": "Material Approval Register",
        "footer": "MAR register, issue 7",
        "pages": [
            [("title", "Material Approval Register"),
             ("p", "Issue 7, March 2024. Covers projects Riverside and Northgate."),
             ("p", BANNER), ("gap", ""),
             ("h", "1 Register"),
             ("t", "Ref     Material                    Project     Status     Date"),
             ("t", "MAR-01  Structural steel S355J2+N   Riverside   Approved   2024-02-10"),
             ("t", "MAR-02  Concrete C32/40             Riverside   Approved   2024-02-10"),
             ("t", "MAR-03  Reinforcement B500B         Northgate   Approved   2024-01-22"),
             ("t", "MAR-04  Purlins S390GD              Northgate   Approved   2024-01-22"),
             ("t", "MAR-05  Chemical anchors HX-200     Northgate   Pending    -"),
             ("t", "MAR-06  Joint sealant PU-40         Riverside   Rejected   2024-03-05"),
             ("t", "MAR-07  Joint sealant PU-55         Riverside   Pending    -")],
            [("h", "2 Notes"),
             ("p", "MAR-06 was rejected because the sealant failed the UV ageing test."),
             ("p", "PU-55 (MAR-07) is proposed as the replacement and awaits approval."),
             ("p", "MAR-05 anchors await the manufacturer's European Technical Assessment.")],
        ],
    },
}

FONTS = {"title": ("F3", 15), "h": ("F3", 11), "p": ("F1", 10), "t": ("F2", 9), "gap": ("F1", 10)}
LEADING = {"title": 24, "h": 18, "p": 14, "t": 13, "gap": 10}


def pdf_string(text: str) -> bytes:
    raw = text.encode("cp1252")
    return b"(" + raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def page_stream(lines, footer: str) -> bytes:
    out, y = [], 790
    for style, text in lines:
        font, size = FONTS[style]
        if style != "gap":
            out.append(b"BT /%s %d Tf 56 %d Td " % (font.encode(), size, y) + pdf_string(text) + b" Tj ET")
        y -= LEADING[style]
    out.append(b"BT /F1 8 Tf 56 40 Td " + pdf_string(footer) + b" Tj ET")
    return b"\n".join(out)


def build(spec: dict) -> bytes:
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog = add(b"")  # filled in once the page tree exists
    pages = add(b"")
    fonts = [add(b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>" % name)
             for name in (b"Helvetica", b"Courier", b"Helvetica-Bold")]
    resources = b"<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>" % tuple(fonts)
    kids = []
    count = len(spec["pages"])
    for number, lines in enumerate(spec["pages"], start=1):
        stream = page_stream(lines, f"{spec['footer']}    Page {number} of {count}    {BANNER}")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources %s /Contents %d 0 R >>"
                        % (pages, resources, content)))
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages
    objects[pages - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    info = add(b"<< /Title " + pdf_string(spec["title"]) + b" /Producer (make_test_pdfs.py) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, catalog, info, xref)
    return bytes(out)


def main():
    for relative, spec in DOCUMENTS.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(build(spec))
        print(f"Wrote {path.relative_to(ROOT.parent)} ({len(spec['pages'])} pages)")


if __name__ == "__main__":
    main()
