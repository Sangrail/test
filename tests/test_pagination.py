import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from engineering_search.access import MockPermissionStore
from helpers import TEST_REPOSITORY, seed_permission_demo
from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app

CEDAR = sorted(f"project-cedar/{p.name}" for p in (TEST_REPOSITORY / "project-cedar").glob("*.md"))
READERS = {file_id: MockPermissionStore().readers(file_id) for file_id in CEDAR}
from engineering_search.jobs import SQLiteJobQueue


def setup(tmp_path, permissions=None, audit=None):
    root = tmp_path / "documents"
    seed_permission_demo(root)
    db = tmp_path / "audit.sqlite3"
    app = create_app(root=root, permissions=permissions,
                     audit=audit or SQLiteAuditStore(db), worker_count=0,
                     queue=SQLiteJobQueue(tmp_path / "queue.sqlite3"))
    client = TestClient(app)
    client.post("/auth/login", json={"user_id": "maya"})
    assert client.post("/index").status_code == 200
    client.post("/auth/login", json={"user_id": "jp"})
    return root, db, client


@pytest.mark.parametrize("user,count", [("jp", 10), ("kamal", 6), ("maya", 5)])
def test_pages_contain_only_permitted_hits_and_totals(tmp_path, user, count):
    _, db, client = setup(tmp_path)
    client.post("/auth/login", json={"user_id": user})
    allowed = sorted(file_id for file_id in CEDAR if user in READERS[file_id])
    received = []
    pages = (count + 1) // 2
    for page in range(1, pages + 1):
        response = client.post("/search", json={"query": "load", "limit": 2, "page": page})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == page and data["limit"] == 2
        assert data["matched_passages"] == count and data["total_pages"] == pages
        assert data["has_next"] == (page < pages)
        assert data["has_previous"] == (page > 1)
        hits = [p["file_id"] for p in data["evidence"]]
        assert len(hits) == min(2, count - (page-1)*2)
        received.append(hits)
        for file_id in CEDAR:
            if user not in READERS[file_id]:
                assert file_id not in response.text
    # Pages are ranked, so check that together they hold each permitted file once.
    assert sorted(sum(received, [])) == allowed
    with sqlite3.connect(db) as connection:
        events = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM events ORDER BY id")]
    manifests = [e for e in events if e["event"] == "search_evidence_prepared"]
    assert [e["page"] for e in manifests] == list(range(1, pages+1))
    for event in manifests:
        assert event["limit"] == 2
        assert [p["file_id"] for p in event["evidence"]] == received[event["page"]-1]


def test_defaults_bounds_empty_and_out_of_range_pages(tmp_path):
    _, _, client = setup(tmp_path)
    default = client.post("/search", json={"query": "load", "limit": 2}).json()
    assert default["page"] == 1 and len(default["evidence"]) == 2
    for page in (0, -1, 1_000_001):
        assert client.post("/search", json={"query": "load", "page": page}).status_code == 422
    empty = client.post("/search", json={"query": "absentword", "page": 2}).json()
    assert empty["matched_passages"] == empty["total_pages"] == 0
    assert not empty["has_next"] and not empty["has_previous"]
    beyond = client.post("/search", json={"query": "load", "limit": 2, "page": 6}).json()
    assert beyond["evidence"] == [] and beyond["total_pages"] == 5
    assert not beyond["has_next"] and beyond["has_previous"]


def test_each_page_rechecks_permissions_and_current_session(tmp_path):
    permissions = MockPermissionStore()
    _, _, client = setup(tmp_path, permissions=permissions)
    client.post("/auth/login", json={"user_id": "maya"})
    first = client.post("/search", json={"query": "load", "limit": 2}).json()
    assert first["matched_passages"] == 5
    revoked = "project-cedar/06-material-certificate.md"
    permissions.rules[revoked] = set()
    second = client.post("/search", json={"query": "load", "limit": 2, "page": 2})
    assert second.json()["matched_passages"] == 4
    assert revoked not in second.text
    assert len(second.json()["evidence"]) == 2
    client.post("/auth/login", json={"user_id": "kamal"})
    switched = client.post("/search", json={"query": "load", "limit": 2, "page": 2}).json()
    assert switched["user"]["id"] == "kamal" and switched["matched_passages"] == 6
    assert {p["file_id"] for p in switched["evidence"]} <= {f for f in CEDAR if "kamal" in READERS[f]}
    client.post("/auth/logout")
    assert client.post("/search", json={"query": "load", "page": 2}).status_code == 401


def test_later_pages_remain_subject_to_the_audit_gate(tmp_path):
    class SwitchableAudit:
        fail = False

        def append(self, event):
            if self.fail:
                raise OSError("Audit unavailable")

    audit = SwitchableAudit()
    _, _, client = setup(tmp_path, audit=audit)
    assert client.post("/search", json={"query": "load", "limit": 2}).status_code == 200
    audit.fail = True
    response = client.post("/search", json={"query": "load", "limit": 2, "page": 2})
    assert response.status_code == 503
    assert "evidence" not in response.json()
    assert "project-cedar/" not in response.text


def test_hundreds_of_permitted_hits_are_reachable_without_duplicates(tmp_path):
    root, _, client = setup(tmp_path)
    for number in range(205):
        (root / f"project-{number:03d}.md").write_text("# Project\n\nBulkpagination load evidence.\n")
    client.post("/auth/login", json={"user_id": "maya"})
    assert client.post("/index").status_code == 200
    client.post("/auth/login", json={"user_id": "jp"})
    received = []
    for page in range(1, 6):
        result = client.post("/search", json={"query": "Bulkpagination", "limit": 50, "page": page}).json()
        assert result["matched_passages"] == 205 and result["total_pages"] == 5
        assert len(result["evidence"]) == (50 if page < 5 else 5)
        received.extend(passage["file_id"] for passage in result["evidence"])
    assert len(received) == len(set(received)) == 205
    assert client.get("/audit/events").status_code == 403
