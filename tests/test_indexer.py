"""The indexer on its own: no web app and no index database.

The indexer finds the files, detects their types, and plans the changes to
an index. These tests give it a folder and a dict of indexed versions.
"""
from pathlib import Path

import pytest

from engineering_search.indexing import (MARKDOWN, PDF, UNKNOWN, ExtensionDetector, Indexer,
                                         ReaderRegistry, UnsupportedFileType)
from engineering_search.indexing.readers import MarkdownReader, ReaderManifest
from engineering_search.indexing.status import (CLASSIFIED, FORMAT_MISMATCH, INDEXED_FULL, MALFORMED, NO_EXTRACTABLE_CONTENT,
                                                NO_READER, READ_ERROR, UNSUPPORTED_FORMAT)

TEST_REPOSITORY = Path(__file__).resolve().parents[1] / "test-repository"


def write(root: Path, name: str, content: str | bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


def test_the_detector_names_the_type_from_the_extension_in_any_case():
    def detect(name):
        return ExtensionDetector().detect(Path(name)).file_type
    assert detect("a/roof.md") == MARKDOWN
    assert detect("a/ROOF.MD") == MARKDOWN
    assert detect("calc.Pdf") == PDF
    assert detect("plan.dwg") == "dwg"   # named, but no reader
    assert detect("model.CATPart") == "catia"
    assert detect("notes.xyz") == UNKNOWN
    assert detect("Makefile") == UNKNOWN


def test_the_scan_lists_every_file_by_type_and_hashes_only_files_with_a_reader(tmp_path):
    write(tmp_path, "a.md", "# A\n\nAlpha.\n")
    write(tmp_path, "sub/b.PDF", b"%PDF-1.4 not really")
    write(tmp_path, "sub/plan.dwg", b"\x00\x01")
    write(tmp_path, "readme.txt", "plain text")
    write(tmp_path, "data.xyz", "?")
    inventory = Indexer(tmp_path).scan()
    assert inventory.by_type() == {"dwg": 1, "markdown": 1, "pdf": 1, "text": 1, "unknown": 1}
    assert set(inventory.indexable()) == {"a.md", "sub/b.PDF"}
    assert set(inventory.with_status(NO_READER)) == {"sub/plan.dwg", "readme.txt"}
    assert set(inventory.with_status(UNSUPPORTED_FORMAT)) == {"data.xyz"}
    a, pdf, dwg = inventory.files["a.md"], inventory.files["sub/b.PDF"], inventory.files["sub/plan.dwg"]
    assert a.status == CLASSIFIED and len(a.version) == 64 and a.size == 12 and a.reader == "markdown-text@2"
    assert pdf.format_version == "1.4" and pdf.reader == "pdf-text-pypdf@1"
    assert dwg.status == NO_READER and dwg.version is None and dwg.size == 2


def test_files_without_a_reader_are_listed_from_their_first_bytes_only(tmp_path, monkeypatch):
    write(tmp_path, "plan.dwg", b"\x00" * 100_000)
    original = Path.read_bytes

    def guarded(path):
        assert path.suffix != ".dwg", "a file without a reader was read in full"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    found = Indexer(tmp_path).scan().files["plan.dwg"]
    assert found.status == NO_READER and found.size == 100_000


def test_the_scan_skips_hidden_files_hidden_folders_and_symbolic_links(tmp_path):
    write(tmp_path, "a.md", "# A\n")
    write(tmp_path, ".DS_Store", b"\x00")
    write(tmp_path, ".git/notes.md", "# Hidden\n")
    outside = write(tmp_path.parent / f"{tmp_path.name}-outside", "secret.md", "# Secret\n")
    (tmp_path / "link.md").symlink_to(outside)
    assert set(Indexer(tmp_path).scan().files) == {"a.md"}


def test_the_test_repository_has_every_kind_of_file_and_gap():
    inventory = Indexer(TEST_REPOSITORY).scan()
    assert inventory.by_type() == {"csv": 2, "dxf": 1, "excel": 1, "jt": 2, "markdown": 135, "pdf": 6, "text": 2}
    assert len(inventory.indexable()) == 145
    assert set(inventory.with_status(NO_READER)) == {"TEST-DATA.txt", "public-fhwa/SOURCES.txt",
                                                     "project-harbour/cad/hangar-frame.jt"}
    assert set(inventory.with_status(FORMAT_MISMATCH)) == {"project-harbour/cad/old-export.jt"}


def test_a_plan_extracts_only_new_and_changed_files_and_removes_deleted_ones(tmp_path):
    write(tmp_path, "keep.md", "# Keep\n\nSame.\n")
    write(tmp_path, "edit.md", "# Edit\n\nOld.\n")
    write(tmp_path, "gone.md", "# Gone\n\nBye.\n")
    write(tmp_path, "plan.dwg", b"\x00")
    indexer = Indexer(tmp_path)

    first = indexer.plan({})
    assert sorted(d.file_id for d in first.upserts) == ["edit.md", "gone.md", "keep.md"]
    assert first.removals == [] and first.added == 3 and first.edited == 0
    assert "plan.dwg" not in first.versions

    # Nothing changed: nothing extracted, and each file keeps its extraction status.
    unchanged = indexer.plan(first.versions, previous=first.inventory.files)
    assert unchanged.upserts == []
    assert unchanged.inventory.files["keep.md"].status == INDEXED_FULL
    # Without the previous inventory the extraction status is unknown, so the files are read again.
    assert len(indexer.plan(first.versions).upserts) == 3

    write(tmp_path, "edit.md", "# Edit\n\nNew.\n")
    (tmp_path / "gone.md").unlink()
    write(tmp_path, "new.md", "# New\n\nHello.\n")
    second = indexer.plan(first.versions, previous=first.inventory.files)
    assert sorted(d.file_id for d in second.upserts) == ["edit.md", "new.md"]
    assert second.removals == ["gone.md"]
    assert second.added == 1 and second.edited == 1
    assert set(second.versions) == {"keep.md", "edit.md", "new.md"}


def test_a_file_that_cannot_be_read_is_reported_and_the_others_are_indexed(tmp_path, monkeypatch):
    write(tmp_path, "valid.md", "# Valid\n\nLoad 5 kN.\n")
    locked = write(tmp_path, "locked.md", "# Locked\n")
    original = Path.read_bytes

    def refuse(path):
        if path == locked:
            raise PermissionError("denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", refuse)
    plan = Indexer(tmp_path).plan({"locked.md": "previous"})
    assert [d.file_id for d in plan.upserts] == ["valid.md"]
    assert plan.failed == [{"file_id": "locked.md", "error": READ_ERROR}]
    locked_file = plan.inventory.files["locked.md"]
    assert locked_file.status == READ_ERROR and locked_file.error == "PermissionError"
    assert plan.removals == ["locked.md"]  # The old version is not kept as if it were current.


def test_a_file_that_cannot_be_extracted_is_reported_with_its_reason(tmp_path):
    write(tmp_path, "valid.md", "# Valid\n\nText.\n")
    write(tmp_path, "empty.md", "# Only a heading\n")
    write(tmp_path, "invalid.md", b"\xff")
    write(tmp_path, "broken.pdf", b"%PDF-1.4 header, then no PDF body")
    write(tmp_path, "renamed.pdf", b"PK\x03\x04 a ZIP file named .pdf")
    plan = Indexer(tmp_path).plan({})
    assert sorted(d.file_id for d in plan.upserts) == ["empty.md", "valid.md"]
    assert sorted(plan.failed, key=lambda f: f["file_id"]) == [
        {"file_id": "broken.pdf", "error": MALFORMED}, {"file_id": "invalid.md", "error": MALFORMED}]
    files = plan.inventory.files
    assert files["empty.md"].status == NO_EXTRACTABLE_CONTENT
    assert files["renamed.pdf"].status == FORMAT_MISMATCH  # Never given to the PDF reader.


def test_the_detector_and_the_readers_can_be_replaced(tmp_path):
    write(tmp_path, "notes.txt", "Heading\n\nRoof load 5 kN/m².\n")
    write(tmp_path, "a.md", "# A\n")
    class TextReader(MarkdownReader):
        manifest = ReaderManifest("plain-text", "1", ("text",), MarkdownReader.manifest.capabilities)

    indexer = Indexer(tmp_path, detector=ExtensionDetector({".txt": "text"}), registry=ReaderRegistry([TextReader()]))
    plan = indexer.plan({})
    assert [d.file_id for d in plan.upserts] == ["notes.txt"]
    assert plan.inventory.files["notes.txt"].reader == "plain-text@1"
    assert plan.inventory.files["a.md"].status == UNSUPPORTED_FORMAT  # This detector does not know .md.


def test_extract_reads_one_file_and_rejects_a_type_without_a_reader(tmp_path):
    path = write(tmp_path, "roof.md", "# Roof\n\nLoad limit 42 kN.\n")
    document, source = Indexer(tmp_path).extract(path)
    assert document.file_id == source.file_id == "roof.md"
    assert document.source_version == source.version and source.file_type == MARKDOWN
    assert [p.text for p in document.passages] == ["Load limit 42 kN."]
    with pytest.raises(UnsupportedFileType):
        Indexer(tmp_path).extract(write(tmp_path, "plan.dwg", b"\x00"))


def test_a_reader_takes_bytes_and_needs_no_file():
    passages = MarkdownReader().read("x.md", "v1", "# Roof\n\nLoad 5 kN.\n\n```\n# not a heading\n```\n".encode()).passages
    assert [(p.heading, p.text) for p in passages] == [
        ("Roof", "Load 5 kN."), ("Roof", "```\n# not a heading\n```")]


def test_a_missing_document_folder_fails_the_scan(tmp_path):
    with pytest.raises(ValueError):
        Indexer(tmp_path / "missing").scan()
