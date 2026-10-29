"""Content detection, reader choice, extraction statuses and the coverage report.

The JT files here are synthetic headers made for the detector tests only. They
are not valid JT files, and no test claims that JT content can be read.
"""
from io import BytesIO
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from engineering_search.access import MockPermissionStore
from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.indexing import ContentDetector, Indexer, ReaderRegistry, coverage_report
from engineering_search.indexing.detect import JT
from engineering_search.indexing.readers import Capabilities, Extraction, MarkdownReader, ReaderManifest
from engineering_search.indexing.status import (CLASSIFIED, DEPENDENCY_MISSING, ENCRYPTED, FORMAT_MISMATCH,
                                                INDEXED_FULL, INDEXED_PARTIAL, INVALID_HEADER, NO_READER,
                                                NO_TEXT_LAYER, UNSUPPORTED_VERSION)
from engineering_search.service import SearchService
from engineering_search.store import SQLiteSearchIndex

RIVERSIDE = Path(__file__).resolve().parents[1] / "test-repository/project-riverside/riverside-footbridge-load-rating.pdf"


def jt_header(version: str) -> bytes:
    """A synthetic JT header for detector tests: the 80-character version string, then padding."""
    return f"Version {version} JT".ljust(80).encode() + b"\x00" * 64


def pdf(*pages: str) -> bytes:
    """A PDF whose pages are "text" (the first Riverside page) or "blank" (no text layer)."""
    writer = PdfWriter()
    for page in pages:
        if page == "text":
            writer.add_page(PdfReader(RIVERSIDE).pages[0])
        else:
            writer.add_blank_page(612, 792)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def xlsx() -> bytes:
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return out.getvalue()


def detect(tmp_path: Path, name: str, content: bytes):
    path = tmp_path / name
    path.write_bytes(content)
    return ContentDetector().detect(path, content[:512])


def test_the_content_decides_the_type_and_the_version(tmp_path):
    assert (detect(tmp_path, "calc.pdf", b"%PDF-1.7\n...").format_version) == "1.7"
    unnamed = detect(tmp_path, "calc", b"%PDF-2.0\n...")
    assert (unnamed.file_type, unnamed.format_version, unnamed.status) == ("pdf", "2.0", None)
    assert detect(tmp_path, "schedule.xlsx", xlsx()).file_type == "excel"
    for version in ("8.1", "9.5", "10.0"):
        signature = detect(tmp_path, "part.jt", jt_header(version))
        assert (signature.file_type, signature.format_version, signature.status) == (JT, version, None)


def test_an_extension_that_the_content_contradicts_is_a_mismatch(tmp_path):
    assert detect(tmp_path, "part.jt", b"%PDF-1.4\n...").status == FORMAT_MISMATCH
    assert detect(tmp_path, "part.jt", b"just some text").status == FORMAT_MISMATCH
    assert detect(tmp_path, "calc.pdf", xlsx()).status == FORMAT_MISMATCH
    assert detect(tmp_path, "schedule.xlsx", b"a,b\n1,2\n").status == FORMAT_MISMATCH
    # The header starts like the type but is broken or truncated.
    assert detect(tmp_path, "part.jt", b"Version x JT").status == INVALID_HEADER
    assert detect(tmp_path, "calc.pdf", b"%PDF").status == INVALID_HEADER
    assert detect(tmp_path, "schedule.xlsx", b"PK\x03\x04truncated").status == INVALID_HEADER


class JtReader:
    """A stand-in JT reader that is tested with JT 9.x only. It never reads real JT content."""
    def __init__(self, dependencies=()):
        self.manifest = ReaderManifest("jt-metadata-fake", "0", (JT,), Capabilities(metadata=True),
                                       format_versions=("9.",), dependencies=dependencies)

    def read(self, file_id, version, raw):
        return Extraction(())


def statuses(tmp_path, registry, files):
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    inventory = Indexer(tmp_path, registry=registry).scan()
    return {file_id: f.status for file_id, f in inventory.files.items()}


def test_the_registry_tells_no_reader_from_unsupported_version_from_a_missing_package(tmp_path):
    files = {"a.jt": jt_header("9.5"), "b.jt": jt_header("10.0")}
    assert statuses(tmp_path, ReaderRegistry([]), files) == {"a.jt": NO_READER, "b.jt": NO_READER}
    assert statuses(tmp_path, ReaderRegistry([JtReader()]), files) == {"a.jt": CLASSIFIED, "b.jt": UNSUPPORTED_VERSION}
    missing = ReaderRegistry([JtReader(dependencies=("no_such_module_for_jt",))])
    assert statuses(tmp_path, missing, files) == {"a.jt": DEPENDENCY_MISSING, "b.jt": UNSUPPORTED_VERSION}


def test_the_first_installed_reader_for_a_type_is_chosen(tmp_path):
    class Preferred(MarkdownReader):
        manifest = ReaderManifest("markdown-preferred", "2", ("markdown",), Capabilities(text=True),
                                  dependencies=("no_such_module_for_markdown",))

    (tmp_path / "a.md").write_text("# A\n\nText.\n")
    chosen = Indexer(tmp_path, registry=ReaderRegistry([Preferred(), MarkdownReader()])).scan().files["a.md"]
    assert chosen.reader == "markdown-text@2"  # The preferred reader is not installed.


def test_pdf_pages_without_text_are_reported_not_hidden(tmp_path):
    (tmp_path / "scanned.pdf").write_bytes(pdf("blank", "blank"))
    (tmp_path / "mixed.pdf").write_bytes(pdf("text", "blank"))
    (tmp_path / "full.pdf").write_bytes(pdf("text"))
    writer = PdfWriter(clone_from=BytesIO(pdf("text")))
    writer.encrypt("secret")
    writer.write(tmp_path / "locked.pdf")
    plan = Indexer(tmp_path).plan({})
    files = plan.inventory.files
    assert files["scanned.pdf"].status == NO_TEXT_LAYER and files["scanned.pdf"].warnings == ("no text on any of 2 pages",)
    assert files["mixed.pdf"].status == INDEXED_PARTIAL and files["mixed.pdf"].warnings == ("no text layer on pages 2",)
    assert files["full.pdf"].status == INDEXED_FULL
    assert files["locked.pdf"].status == ENCRYPTED
    # A scanned PDF is in the index with no passages, so it is not read again on each refresh.
    assert {d.file_id: len(d.passages) for d in plan.upserts}["scanned.pdf"] == 0


def test_the_coverage_report_gives_each_gap_a_distinct_status_and_a_hint(tmp_path):
    (tmp_path / "cad").mkdir()
    files = {"notes.md": b"# Notes\n\nText.\n", "scanned.pdf": pdf("blank"), "mixed.pdf": pdf("text", "blank"),
             "cad/assembly.jt": jt_header("10.0"), "cad/renamed.jt": b"%PDF-1.4\n"}
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    indexer = Indexer(tmp_path)
    report = coverage_report(indexer.plan({}).inventory, indexer.registry)
    gaps = {g["file_id"]: g for g in report["gaps"]}
    assert {f: g["status"] for f, g in gaps.items()} == {
        "cad/assembly.jt": NO_READER, "cad/renamed.jt": FORMAT_MISMATCH,
        "mixed.pdf": INDEXED_PARTIAL, "scanned.pdf": NO_TEXT_LAYER}
    assert gaps["cad/assembly.jt"]["format_version"] == "10.0"
    assert gaps["cad/assembly.jt"]["capabilities"] == {"text": "unsupported", "tables": "unsupported",
                                                       "metadata": "header_only", "geometry": "unsupported"}
    assert "OCR" in gaps["scanned.pdf"]["hint"]
    assert (report["fully_indexed"], report["partially_indexed"], report["no_content"], report["not_supported"]) == (1, 1, 1, 2)
    assert {(r["file_type"], r["format_version"]): r["files"] for r in report["by_format"]}[("jt", "10.0")] == 1
    assert report["by_folder"][0] == {"folder": "(top level)", "files": 3,
                                      "statuses": {INDEXED_FULL: 1, INDEXED_PARTIAL: 1, NO_TEXT_LAYER: 1}}


def test_statuses_survive_a_restart_and_the_report_is_for_the_index_team_only(tmp_path):
    root = tmp_path / "documents"
    root.mkdir()
    (root / "scanned.pdf").write_bytes(pdf("blank"))
    (root / "notes.md").write_text("# Notes\n\nText.\n")
    index_path = tmp_path / "index.sqlite3"

    def start():
        return SearchService(root, SQLiteSearchIndex(index_path), SQLiteAuditStore(tmp_path / "audit.sqlite3"),
                             MockPermissionStore())

    first = start()
    first.reindex()
    restarted = start()  # A new process on the same index file, before any refresh.
    assert {g["file_id"]: g["status"] for g in restarted.coverage()["gaps"]} == {"scanned.pdf": NO_TEXT_LAYER}
    assert restarted.reindex()["read_files"] == 0  # Known statuses: nothing is read again.

    app = create_app(root=root, index=SQLiteSearchIndex(index_path), audit=SQLiteAuditStore(tmp_path / "audit.sqlite3"))
    with TestClient(app) as client:
        client.post("/auth/login", json={"user_id": "kamal"})
        assert client.get("/index/coverage").status_code == 403
        client.post("/auth/login", json={"user_id": "maya"})
        assert client.get("/index/coverage").json()["by_status"] == {INDEXED_FULL: 1, NO_TEXT_LAYER: 1}
