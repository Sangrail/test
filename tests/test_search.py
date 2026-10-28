import hashlib
import json
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.store import SQLiteSearchIndex
from engineering_search.jobs import SQLiteJobQueue


def make_client(tmp_path, audit=None):
    root = tmp_path / "docs"
    root.mkdir()
    db = tmp_path / "audit.sqlite3"
    client = TestClient(create_app(root=root, index=SQLiteSearchIndex(),
                                  audit=audit or SQLiteAuditStore(db),
                                  queue=SQLiteJobQueue(tmp_path / "queue.sqlite3")))
    assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
    return root, db, client


def events(path):
    with sqlite3.connect(path) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM events ORDER BY id")]


def test_table_evidence_matches_source_and_durable_audit(tmp_path):
    root, db, client = make_client(tmp_path)
    source = "# Roof load\n\n| Limit | Conditions |\n| --- | --- |\n| 5 kN/m² | Static only |\n"
    (root / "roof.md").write_text(source)
    assert client.post("/index").status_code == 200
    response = client.post("/search", json={"query": "roof load"})
    assert response.status_code == 200
    body = response.json()
    passage = body["evidence"][0]
    assert passage["text"] == "\n".join(source.splitlines()[passage["start_line"]-1:passage["end_line"]])
    assert "Conditions" in passage["text"] and "Static only" in passage["text"]
    assert passage["source_version"] == hashlib.sha256(source.encode()).hexdigest()
    logged = events(db)
    assert logged[0]["evidence"][0]["source_version"] == passage["source_version"]
    assert logged[0]["request_id"] == body["request_id"] == logged[1]["request_id"]
    assert logged[0]["actor_subject"] == "demo-user-003"
    assert logged[0]["authorisation"] == "enforced_demo_policy"
    assert "text" not in logged[0]["evidence"][0] and "query" not in logged[0]
    assert logged[1]["event"] == "search_response_send_completed"


def test_add_edit_delete_and_unreadable_file_is_skipped(tmp_path):
    root, _, client = make_client(tmp_path)
    file = root / "roof.md"
    file.write_text("# Roof\n\nLoad limit 5 kN.\n")
    assert client.post("/index").json()["added"] == 1
    file.write_text("# Roof\n\nLoad limit 7 kN.\n")
    assert client.post("/index").json()["edited"] == 1
    assert client.post("/search", json={"query": "5"}).json()["evidence"] == []
    assert len(client.post("/search", json={"query": "7"}).json()["evidence"]) == 1
    (root / "bad.md").write_bytes(b"\xff")
    result = client.post("/index").json()
    assert result["failed_files"] == [{"file_id": "bad.md", "error": "UnicodeDecodeError"}]
    assert len(client.post("/search", json={"query": "7"}).json()["evidence"]) == 1
    (root / "bad.md").unlink()
    file.unlink()
    assert client.post("/index").json()["deleted"] == 1
    assert client.post("/search", json={"query": "roof"}).json()["evidence"] == []


def test_audit_failure_withholds_evidence(tmp_path):
    class BrokenAudit:
        def append(self, event):
            raise OSError("Disk unavailable")

    root, _, client = make_client(tmp_path, BrokenAudit())
    (root / "secret.md").write_text("# Secret\n\nClassified limit 42 kN.\n")
    client.post("/index")
    response = client.post("/search", json={"query": "limit"})
    assert response.status_code == 503
    # Check words, not "42": the error carries a random request ID that may contain "42".
    assert "Classified" not in response.text and "secret.md" not in response.text
    counters = client.get("/telemetry").json()["counters"]
    assert counters["audit_failures_total"] == 1
    assert counters["query_errors_total"] == 1


def test_completion_audit_failure_is_visible(tmp_path):
    class CompletionFailure:
        def __init__(self):
            self.events = []

        def append(self, event):
            if event["event"] != "search_evidence_prepared":
                raise OSError("Disk unavailable after release")
            self.events.append(event)

    audit = CompletionFailure()
    root, _, client = make_client(tmp_path, audit)
    (root / "a.md").write_text("# A\n\nRoof load 5 kN.\n")
    client.post("/index")
    assert client.post("/search", json={"query": "roof"}).status_code == 200
    assert len(audit.events) == 1
    assert client.get("/telemetry").json()["counters"]["response_completion_audit_failures_total"] == 1


def test_120_documents_conflicts_and_telemetry(tmp_path):
    root, _, client = make_client(tmp_path)
    for i in range(120):
        (root / f"project-{i:03}.md").write_text(f"# Project {i}\n\nRoof load {i+1} kN. Draft.\n")
    indexed = client.post("/index").json()
    assert indexed["files"] == 120 and indexed["workers"] == 1
    assert indexed["ingestion_files_per_second"] > 0
    assert indexed["indexing_files_per_second"] > 0
    for _ in range(10):
        response = client.post("/search", json={"query": "roof load", "limit": 50})
        assert response.json()["matched_passages"] == 120
        assert len(response.json()["evidence"]) == 50
        assert response.json()["truncated"] is True
    metrics = client.get("/telemetry").json()
    assert metrics["query_ms"]["count"] == 10
    assert metrics["query_ms"]["min"] <= metrics["query_ms"]["median"] <= metrics["query_ms"]["max"]
    assert metrics["query_ms"]["min"] <= metrics["query_ms"]["average"] <= metrics["query_ms"]["max"]
    assert metrics["recent_search_stages"][0]["audit_ms"] > 0


def test_validation_readiness_openapi_and_symlink_boundary(tmp_path):
    root, _, client = make_client(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\nRestricted value.\n")
    (root / "link.md").symlink_to(outside)
    (root / "broken.pdf").write_text("Not a real PDF")
    assert client.post("/search", json={"query": "roof"}).status_code == 409
    assert client.post("/search", json={"query": "?!"}).status_code == 422
    assert client.post("/search", json={"query": "roof", "limit": 0}).status_code == 422
    indexed = client.post("/index").json()
    assert indexed["files"] == 0
    assert indexed["failed_files"] == [{"file_id": "broken.pdf", "error": "PdfStreamError"}]
    assert client.post("/search", json={"query": "restricted"}).json()["evidence"] == []
    assert client.get("/docs").status_code == 200
    assert "/search" in client.get("/openapi.json").json()["paths"]


def test_rescan_detects_changes_without_modifying_index(tmp_path):
    root, _, client = make_client(tmp_path)
    (root / "roof.md").write_text("# Roof\n\nLoad limit 5 kN.\n")
    (root / "remove.md").write_text("# Old\n\nObsolete entry.\n")
    before = client.get("/index/status").json()
    assert before["source_files"] is None
    scanned = client.post("/scan").json()
    assert scanned["source_files"] == 2
    assert scanned["indexed_files"] == 0 and scanned["status"] == "not_indexed"
    client.post("/index")
    assert client.get("/index/status").json()["status"] == "up_to_date"
    (root / "roof.md").write_text("# Roof\n\nLoad limit 9 kN.\n")
    (root / "remove.md").unlink()
    (root / "new.MD").write_text("# Added\n\nNew specification.\n")
    # Reading status does not silently rescan the filesystem.
    assert client.get("/index/status").json()["status"] == "up_to_date"
    changed = client.post("/scan").json()
    assert changed["status"] == "out_of_date"
    assert changed["source_files"] == 2 and changed["indexed_files"] == 2
    assert changed["pending_changes"] == {"added": 1, "edited": 1, "deleted": 1}
    assert {r["status"] for r in changed["documents"]} == {"added", "edited", "deleted"}
    assert client.post("/search", json={"query": "5"}).json()["evidence"]
    assert not client.post("/search", json={"query": "9"}).json()["evidence"]
    client.post("/index")
    final = client.get("/index/status").json()
    assert final["status"] == "up_to_date"
    assert final["pending_changes"] == {"added": 0, "edited": 0, "deleted": 0}
    assert client.post("/search", json={"query": "9"}).json()["evidence"]


def test_empty_folder_scan_failure_and_dashboard(tmp_path):
    root, _, client = make_client(tmp_path)
    assert client.get("/").status_code == 200
    assert client.get("/static/dashboard.js").status_code == 200
    assert client.post("/scan").json()["source_files"] == 0
    client.post("/index")
    assert client.get("/index/status").json()["status"] == "up_to_date"
    root.rmdir()
    assert client.post("/scan").status_code == 503
    state = client.get("/index/status").json()
    assert state["status"] == "error" and state["scan_error"]
    assert state["operation"] is None and state["ready"] is True


def test_scan_operation_is_visible_and_overlapping_build_rejected(tmp_path, monkeypatch):
    from threading import Event, Thread
    import engineering_search.service as service_module
    root, _, client = make_client(tmp_path)
    entered, finish = Event(), Event()
    original_scan = service_module.scan_files

    def slow_scan(root):
        entered.set()
        assert finish.wait(5)
        return original_scan(root)

    monkeypatch.setattr(service_module, "scan_files", slow_scan)
    responses = []
    thread = Thread(target=lambda: responses.append(client.post("/scan")))
    thread.start()
    try:
        assert entered.wait(3)
        assert client.get("/index/status").json()["status"] == "scanning"
        assert client.post("/index").status_code == 409
    finally:
        finish.set()
        thread.join(5)
    assert responses[0].status_code == 200
