from fastapi.testclient import TestClient

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.jobs import SQLiteJobQueue


def configured(root, state):
    return create_app(root=root, audit=SQLiteAuditStore(state / "audit.sqlite3"),
                      queue=SQLiteJobQueue(state / "queue.sqlite3"),
                      worker_count=0, index_on_start=True)


def test_startup_build_and_restart_use_current_documents(tmp_path):
    root = tmp_path / "external documents"
    root.mkdir()
    document = root / "load.md"
    document.write_text("# Roof\n\nApproved load 5 kN.\n")
    state = tmp_path / "separate state"
    for value in ("5", "7"):
        document.write_text(f"# Roof\n\nApproved load {value} kN.\n")
        with TestClient(configured(root, state)) as client:
            client.post("/auth/login", json={"user_id": "maya"})
            status = client.get("/index/status").json()
            assert status["status"] == "up_to_date"
            assert status["indexed_files"] == 1
            result = client.post("/search", json={"query": "load"}).json()
            assert f"{value} kN" in result["evidence"][0]["text"]
            assert client.app.state.telemetry.snapshot()["index_runs"][-1]["files"] == 1


def test_unreadable_file_is_skipped_at_startup(tmp_path):
    root = tmp_path / "documents"
    root.mkdir()
    (root / "valid.md").write_text("# Valid\n\nLoad 5 kN.\n")
    (root / "invalid.md").write_bytes(b"\xff")
    app = configured(root, tmp_path / "state")
    with TestClient(app):
        assert set(app.state.index.versions()) == {"valid.md"}
        failed = app.state.telemetry.snapshot()["index_runs"][-1]["failed_files"]
        assert failed == [{"file_id": "invalid.md", "error": "MALFORMED"}]
