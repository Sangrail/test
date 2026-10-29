# CAD fixtures for the coverage report

SYNTHETIC TEST DATA - not for engineering use.

hangar-frame-ga.dxf is a valid DXF drawing (AutoCAD R12, ASCII), written by
scripts/make_cad_fixture.py. Its general notes and its title block (drawing number,
revision, approval status, frame steel grade, crane safe working load) are read by the
DXF stand-in reader; its geometry is not read. Any CAD program or DXF viewer opens it.

The .jt files in this folder are NOT valid JT files. hangar-frame.jt holds only
a synthetic 80-character header ("Version 10.0 JT") so that the content detector
can be tested. old-export.jt is a text note saved with a .jt extension. No JT
content is read from either file; the coverage report lists them as gaps.
