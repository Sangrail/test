from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
from time import monotonic, perf_counter, sleep

from fastapi.testclient import TestClient

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.indexing import Indexer
from engineering_search.store import SQLiteSearchIndex
from engineering_search.jobs import SQLiteJobQueue


def setup(tmp_path, workers=0, index=None):
    root = tmp_path / "documents"
    root.mkdir(exist_ok=True)
    queue = SQLiteJobQueue(tmp_path / "jobs.sqlite3")
    app = create_app(root=root, index=index, audit=SQLiteAuditStore(tmp_path / "audit.sqlite3"),
                     queue=queue, worker_count=workers)
    return root, queue, app


def upload(client, filename="roof.md", content=b"# Roof\n\nLoad limit 42 kN.\n"):
    created = client.post("/uploads", json={"filename": filename})
    assert created.status_code == 201
    job = created.json()
    assert job["status"] == "uploading"
    response = client.put(f"/uploads/{job['id']}/content", content=content)
    return job, response


def wait_ready(client, job_id):
    deadline = monotonic()+5
    while monotonic() < deadline:
        job = client.get(f"/uploads/{job_id}").json()
        if job["status"] == "ready":
            return job
        assert job["status"] != "failed", job
        sleep(.02)
    raise AssertionError("Worker did not finish within five seconds")


def test_upload_is_queued_then_searchable_only_after_worker_commit(tmp_path):
    root, queue, app = setup(tmp_path)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        client.post("/scan")
        client.post("/index")
        job, response = upload(client)
        assert response.status_code == 202 and response.json()["status"] == "queued"
        assert client.get("/uploads").json()["counts"]["queued"] == 1
        assert client.get("/index/status").json()["source_files"] == 1
        assert not client.post("/search", json={"query": "42"}).json()["evidence"]
        # Bulk reindex must not make a queued file searchable prematurely.
        client.post("/index")
        assert not client.post("/search", json={"query": "42"}).json()["evidence"]
        claimed = queue.claim("test-worker")
        app.state.worker_pool.process(claimed, perf_counter())
        ready = client.get(f"/uploads/{job['id']}").json()
        assert ready["status"] == "ready" and ready["attempts"] == 1
        evidence = client.post("/search", json={"query": "42"}).json()["evidence"]
        assert len(evidence) == 1 and evidence[0]["source_version"] == ready["source_version"]
        assert (root / ready["file_id"]).read_bytes().startswith(b"# Roof")
        assert client.get("/index/status").json()["searchable_passages"] == 1


def test_two_workers_extract_concurrently_and_publish_independent_files(tmp_path, monkeypatch):
    root, queue, app = setup(tmp_path, workers=2)
    release, both_entered = Event(), Event()
    guard = Lock()
    entered = []
    original = Indexer.extract

    def blocked_extract(self, path):
        with guard:
            entered.append(path)
            if len(entered) == 2:
                both_entered.set()
        assert release.wait(5)
        return original(self, path)

    monkeypatch.setattr(Indexer, "extract", blocked_extract)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        first, _ = upload(client, "one.md", b"# One\n\nUnique firstbeam.\n")
        second, _ = upload(client, "two.md", b"# Two\n\nUnique secondbeam.\n")
        try:
            assert both_entered.wait(3)
            assert client.get("/uploads").json()["counts"]["indexing"] == 2
            assert client.post("/search", json={"query": "unique"}).status_code == 409
        finally:
            release.set()
        a, b = wait_ready(client, first["id"]), wait_ready(client, second["id"])
        assert a["worker_id"] != b["worker_id"]
        assert len(client.post("/search", json={"query": "unique"}).json()["evidence"]) == 2


def test_validation_duplicate_names_and_content_cannot_be_overwritten(tmp_path):
    root, queue, app = setup(tmp_path)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        for name in ("../escape.md", "nested/file.md", "file.pdf", ".hidden.md"):
            assert client.post("/uploads", json={"filename": name}).status_code == 422
        one, response = upload(client, "same.md")
        two, _ = upload(client, "same.md")
        assert one["file_id"] != two["file_id"]
        assert client.put(f"/uploads/{one['id']}/content", content=b"replacement").status_code == 409
        bad, response = upload(client, "invalid.md", b"\xff")
        assert response.status_code == 422
        assert client.get(f"/uploads/{bad['id']}").json()["status"] == "failed"
        assert client.post(f"/uploads/{bad['id']}/retry").status_code == 409
        empty, response = upload(client, "empty.md", b"")
        assert response.status_code == 422
        large, response = upload(client, "huge.md", b"a"*(10*1024*1024+1))
        assert response.status_code == 413


def test_failed_index_can_be_retried_without_duplicate_passages(tmp_path):
    class OnceBrokenIndex(SQLiteSearchIndex):
        fail = True

        def upsert(self, document):
            if self.fail:
                self.fail = False
                raise OSError("Injected write failure")
            return super().upsert(document)

    root, queue, app = setup(tmp_path, index=OnceBrokenIndex())
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        job, _ = upload(client)
        claimed = queue.claim("test-worker")
        try:
            app.state.worker_pool.process(claimed, perf_counter())
        except OSError:
            queue.fail(job["id"], "Injected test failure")
        assert client.post(f"/uploads/{job['id']}/retry").status_code == 202
        claimed = queue.claim("test-worker")
        app.state.worker_pool.process(claimed, perf_counter())
        app.state.worker_pool.process(claimed, perf_counter())  # replay is idempotent
        assert len(client.post("/search", json={"query": "load"}).json()["evidence"]) == 1
        assert queue.get(job["id"])["attempts"] == 2


def test_atomic_claims_and_restart_recovery(tmp_path):
    queue = SQLiteJobQueue(tmp_path / "queue.sqlite3")
    jobs = [queue.create(f"file{i}.md") for i in range(30)]
    for job in jobs:
        queue.enqueue(job["id"], 10, "version")
    with ThreadPoolExecutor(max_workers=8) as pool:
        claimed = list(pool.map(lambda i: queue.claim(f"worker-{i}"), range(40)))
    ids = [job["id"] for job in claimed if job]
    assert len(ids) == len(set(ids)) == 30
    queue.complete(ids[0], 1, 1)
    interrupted = queue.create("interrupted.md")
    queue.recover()
    counts = queue.snapshot()["counts"]
    assert counts["queued"] == 30 and counts["indexing"] == 0
    assert counts["ready"] == 0 and queue.get(interrupted["id"])["status"] == "failed"


def test_ready_jobs_replayed_into_fresh_index_on_restart(tmp_path):
    root, queue, app = setup(tmp_path, workers=1)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        job, _ = upload(client)
        wait_ready(client, job["id"])
    _, _, new_app = setup(tmp_path, workers=1)
    with TestClient(new_app) as client:
        assert client.post("/auth/login", json={"user_id": "maya"}).status_code == 200
        wait_ready(client, job["id"])
        evidence = client.post("/search", json={"query": "42"}).json()["evidence"]
        assert len(evidence) == 1


def test_single_document_update_removes_old_tokens(tmp_path):
    path = tmp_path / "source.md"
    path.write_text("# Beam\n\nOldparameter 17.\n")
    index = SQLiteSearchIndex()
    index.upsert(Indexer(tmp_path).extract(path)[0])
    path.write_text("# Beam\n\nNewparameter 29.\n")
    index.upsert(Indexer(tmp_path).extract(path)[0])
    assert index.search("oldparameter", 10) == ([], 0)
    assert index.search("newparameter", 10)[1] == 1
    assert index.passage_count() == 1
