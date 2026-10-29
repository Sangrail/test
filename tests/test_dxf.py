"""The DXF stand-in: a parameter held in a CAD drawing is answered without opening it.

The drawing is test-repository/project-harbour/cad/hangar-frame-ga.dxf, written by
scripts/make_cad_fixture.py. The checks read the file's lines directly, so a cited line
must hold the quoted value."""
from pathlib import Path

import pytest

from engineering_search.indexing.detect import ContentDetector
from engineering_search.indexing.facts import extract_facts
from engineering_search.indexing.readers import ReaderError
from engineering_search.indexing.readers.dxf import DxfTextReader
from engineering_search.indexing.status import FORMAT_MISMATCH, NO_EXTRACTABLE_CONTENT

DRAWING = Path(__file__).resolve().parents[1] / "test-repository/project-harbour/cad/hangar-frame-ga.dxf"


def read(raw: bytes):
    return DxfTextReader().read("drawing.dxf", "v1", raw)


def test_title_block_attributes_are_a_table_that_cites_the_value_line():
    raw = DRAWING.read_bytes()
    lines = raw.decode().splitlines()
    extraction = read(raw)
    (table,) = extraction.tables
    assert table.name == "Drawing HB-S-201 rev C title block"
    rows = {row.cells[0]: row for row in table.rows}
    assert rows["Crane safe working load"].cells[1] == "50 kN"
    assert lines[rows["Crane safe working load"].line - 1] == "50 kN"
    assert lines[rows["Crane safe working load"].line + 1] == "CRANE_SAFE_WORKING_LOAD"  # its tag, two lines on
    assert lines[rows["Approval status"].line - 1] == "Approved"


def test_an_attribute_passage_quotes_its_tag_and_value_from_the_cited_lines():
    raw = DRAWING.read_bytes()
    lines = raw.decode().splitlines()
    (passage,) = [p for p in read(raw).passages if p.text.startswith("CRANE_SAFE_WORKING_LOAD")]
    assert passage.text == "CRANE_SAFE_WORKING_LOAD | 50 kN"
    assert passage.start_line == passage.end_line and lines[passage.start_line - 1] == "50 kN"
    assert lines[passage.start_line + 1] == "CRANE_SAFE_WORKING_LOAD"  # the tag, in the same entity
    assert passage.heading == "Drawing HB-S-201 rev C title block"


def test_notes_are_passages_and_geometry_is_not_read():
    extraction = read(DRAWING.read_bytes())
    notes = [p for p in extraction.passages if p.heading == "Drawing notes (layer NOTES)"]
    assert any("HOLDING DOWN BOLTS M24 GRADE 8.8" in p.text for p in notes)
    assert not any(p.text.replace(".", "").isdigit() for p in extraction.passages)  # no coordinates


def test_title_block_values_become_typed_facts():
    facts = {f.parameter: f for f in extract_facts(read(DRAWING.read_bytes()).tables)}
    assert facts["load_capacity"].value == "50 kN" and facts["load_capacity"].si_value == 50_000
    assert facts["material_grade"].value == "S355J2"
    assert facts["compliance_status"].value == "Approved"
    assert {f.subject for f in facts.values()} == {"Drawing HB-S-201 rev C title block"}


def test_block_definitions_are_templates_and_not_read():
    raw = DRAWING.read_bytes()
    extraction = read(raw)
    attribute_lines = {p.start_line for p in extraction.passages if "title block" in p.heading}
    blocks_end = raw.decode().splitlines().index("ENTITIES")
    assert min(attribute_lines) > blocks_end  # nothing from the BLOCKS section (empty ATTDEF defaults)


def test_mtext_formatting_is_removed():
    raw = b"  0\nSECTION\n  2\nENTITIES\n  0\nMTEXT\n  8\nNOTES\n  3\n{\\fArial;MAX DECK LOAD }\n  1\n\\P10 kN/m\xc2\xb2\n  0\nENDSEC\n  0\nEOF\n"
    (passage,) = read(raw).passages
    assert passage.text == "MAX DECK LOAD \n10 kN/m²"
    assert (passage.start_line, passage.end_line) == (10, 12)


def test_a_drawing_with_no_text_has_no_content():
    raw = b"  0\nSECTION\n  2\nENTITIES\n  0\nLINE\n  8\n0\n 10\n0.0\n 20\n0.0\n 11\n1.0\n 21\n1.0\n  0\nENDSEC\n  0\nEOF\n"
    assert read(raw).status == NO_EXTRACTABLE_CONTENT


def test_binary_dxf_is_refused():
    with pytest.raises(ReaderError):
        read(b"AutoCAD Binary DXF\r\n\x1a\x00" + b"\x00" * 20)


def test_dxf_is_detected_by_content(tmp_path):
    detector = ContentDetector()
    assert (detector.detect(DRAWING, DRAWING.read_bytes()[:512]).format_version) == "AC1009"
    fake = tmp_path / "note.dxf"
    fake.write_text("not a drawing")
    assert detector.detect(fake, fake.read_bytes()).status == FORMAT_MISMATCH
