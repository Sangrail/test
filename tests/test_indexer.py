"""The indexer on its own: no web app, no index database, no queue.

The indexer finds the files, detects their types, and plans the changes to
an index. These tests give it a folder and a dict of indexed versions.
"""
from pathlib import Path

import pytest

from engineering_search.indexing import (INDEXABLE, MARKDOWN, PDF, UNKNOWN, UNREADABLE, UNSUPPORTED,
                                         ExtensionDetector, Indexer, UnsupportedFileType)
from engineering_search.indexing.readers import read_markdown

TEST_REPOSITORY = Path(__file__).resolve().parents[1] / "test-repository"


def write(root: Path, name: str, content: str | bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


def test_the_detector_names_the_type_from_the_extension_in_any_case():
    detector = ExtensionDetector()
    assert detector.detect(Path("a/roof.md")) == MARKDOWN
    assert detector.detect(Path("a/ROOF.MD")) == MARKDOWN
    assert detector.detect(Path("calc.Pdf")) == PDF
    assert detector.detect(Path("plan.dwg")) == "dwg"   # named, but no reader
    assert detector.detect(Path("model.CATPart")) == "catia"
    assert detector.detect(Path("notes.xyz")) == UNKNOWN
    assert detector.detect(Path("Makefile")) == UNKNOWN


def test_the_scan_lists_every_file_by_type_and_hashes_only_indexable_files(tmp_path):
    write(tmp_path, "a.md", "# A\n\nAlpha.\n")
    write(tmp_path, "sub/b.PDF", b"%PDF-1.4 not really")
    write(tmp_path, "sub/plan.dwg", b"\x00\x01")
    write(tmp_path, "readme.txt", "plain text")
    write(tmp_path, "data.xyz", "?")
    inventory = Indexer(tmp_path).scan()
    assert inventory.by_type() == {"dwg": 1, "markdown": 1, "pdf": 1, "text": 1, "unknown": 1}
    assert set(inventory.indexable()) == {"a.md", "sub/b.PDF"}
    assert set(inventory.with_outcome(UNSUPPORTED)) == {"sub/plan.dwg", "readme.txt", "data.xyz"}
    a, dwg = inventory.files["a.md"], inventory.files["sub/plan.dwg"]
    assert a.outcome == INDEXABLE and len(a.version) == 64 and a.size == 12
    assert dwg.outcome == UNSUPPORTED and dwg.version is None and dwg.size == 2


def test_unsupported_files_are_listed_without_being_read(tmp_path, monkeypatch):
    write(tmp_path, "plan.dwg", b"\x00")
    original = Path.read_bytes

    def guarded(path):
        assert path.suffix != ".dwg", "an unsupported file was read"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert Indexer(tmp_path).scan().files["plan.dwg"].outcome == UNSUPPORTED


def test_the_scan_skips_hidden_files_hidden_folders_and_symbolic_links(tmp_path):
    write(tmp_path, "a.md", "# A\n")
    write(tmp_path, ".DS_Store", b"\x00")
    write(tmp_path, ".git/notes.md", "# Hidden\n")
    outside = write(tmp_path.parent / f"{tmp_path.name}-outside", "secret.md", "# Secret\n")
    (tmp_path / "link.md").symlink_to(outside)
    assert set(Indexer(tmp_path).scan().files) == {"a.md"}


def test_the_test_repository_has_markdown_pdf_and_two_unsupported_text_files():
    inventory = Indexer(TEST_REPOSITORY).scan()
    assert inventory.by_type() == {"markdown": 133, "pdf": 5, "text": 2}
    assert len(inventory.indexable()) == 138
    assert set(inventory.with_outcome(UNSUPPORTED)) == {"TEST-DATA.txt", "public-fhwa/SOURCES.txt"}


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

    assert indexer.plan(first.versions).upserts == []  # Nothing changed: nothing extracted.

    write(tmp_path, "edit.md", "# Edit\n\nNew.\n")
    (tmp_path / "gone.md").unlink()
    write(tmp_path, "new.md", "# New\n\nHello.\n")
    second = indexer.plan(first.versions)
    assert sorted(d.file_id for d in second.upserts) == ["edit.md", "new.md"]
    assert second.removals == ["gone.md"]
    assert second.added == 1 and second.edited == 1
    assert set(second.versions) == {"keep.md", "edit.md", "new.md"}


def test_a_plan_does_not_touch_skipped_files(tmp_path):
    write(tmp_path, "uploads/job/a.md", "# A\n")
    plan = Indexer(tmp_path).plan({"uploads/job/a.md": "old"}, skip={"uploads/job/a.md"})
    assert plan.upserts == [] and plan.removals == [] and plan.versions == {}


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
    assert plan.failed == [{"file_id": "locked.md", "error": "PermissionError"}]
    assert plan.inventory.files["locked.md"].outcome == UNREADABLE
    assert plan.removals == ["locked.md"]  # The old version is not kept as if it were current.


def test_a_file_that_cannot_be_extracted_is_reported(tmp_path):
    write(tmp_path, "valid.md", "# Valid\n")
    write(tmp_path, "invalid.md", b"\xff")
    write(tmp_path, "broken.pdf", b"not a pdf")
    plan = Indexer(tmp_path).plan({})
    assert [d.file_id for d in plan.upserts] == ["valid.md"]
    assert sorted(plan.failed, key=lambda f: f["file_id"]) == [
        {"file_id": "broken.pdf", "error": "PdfStreamError"},
        {"file_id": "invalid.md", "error": "UnicodeDecodeError"}]


def test_the_detector_and_the_readers_can_be_replaced(tmp_path):
    write(tmp_path, "notes.txt", "Heading\n\nRoof load 5 kN/m².\n")
    write(tmp_path, "a.md", "# A\n")
    indexer = Indexer(tmp_path, detector=ExtensionDetector({".txt": "text"}),
                      readers={"text": read_markdown})
    plan = indexer.plan({})
    assert [d.file_id for d in plan.upserts] == ["notes.txt"]
    assert plan.inventory.files["a.md"].outcome == UNSUPPORTED  # This detector does not know .md.


def test_extract_reads_one_file_and_rejects_a_type_without_a_reader(tmp_path):
    path = write(tmp_path, "roof.md", "# Roof\n\nLoad limit 42 kN.\n")
    document, source = Indexer(tmp_path).extract(path)
    assert document.file_id == source.file_id == "roof.md"
    assert document.source_version == source.version and source.file_type == MARKDOWN
    assert [p.text for p in document.passages] == ["Load limit 42 kN."]
    with pytest.raises(UnsupportedFileType):
        Indexer(tmp_path).extract(write(tmp_path, "plan.dwg", b"\x00"))


def test_a_reader_takes_bytes_and_needs_no_file():
    passages = read_markdown("x.md", "v1", "# Roof\n\nLoad 5 kN.\n\n```\n# not a heading\n```\n".encode())
    assert [(p.heading, p.text) for p in passages] == [
        ("Roof", "Load 5 kN."), ("Roof", "```\n# not a heading\n```")]


def test_a_missing_document_folder_fails_the_scan(tmp_path):
    with pytest.raises(ValueError):
        Indexer(tmp_path / "missing").scan()
