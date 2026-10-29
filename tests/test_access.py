import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from engineering_search.access import ACCESS_RULES, MockPermissionStore
from helpers import TEST_REPOSITORY, seed_permission_demo
from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app

CEDAR = sorted(f"project-cedar/{p.name}" for p in (TEST_REPOSITORY / "project-cedar").glob("*.md"))
READERS = {file_id: MockPermissionStore().readers(file_id) for file_id in CEDAR}


def setup(tmp_path, permissions=None, audit=None):
    root = tmp_path / "documents"
    seed_permission_demo(root)
    db = tmp_path / "audit.sqlite3"
    app = create_app(root=root, audit=audit or SQLiteAuditStore(db), permissions=permissions)
    client = TestClient(app)
    sign_in(client,"maya")
    assert client.post("/index").status_code == 200
    return root, db, client


def sign_in(client, user):
    response = client.post("/auth/login",json={"user_id":user})
    assert response.status_code == 200
    return response


def audit_events(db):
    with sqlite3.connect(db) as connection:
        return [json.loads(r[0]) for r in connection.execute("SELECT payload FROM events ORDER BY id")]


@pytest.mark.parametrize("user,expected", [("jp",10),("kamal",6),("maya",5)])
def test_demo_permissions_are_enforced_in_search_and_metadata(tmp_path,user,expected):
    _, db, client = setup(tmp_path)
    sign_in(client,user)
    response = client.post("/search",json={"query":"load","limit":20})
    assert response.status_code == 200
    body = response.json()
    allowed = {file_id for file_id in CEDAR if user in READERS[file_id]}
    assert len(allowed) == expected
    assert {p["file_id"] for p in body["evidence"]} == allowed
    assert body["matched_passages"] == expected
    assert body["user"]["id"] == user
    assert "excluded" not in body and "candidate_count" not in body
    for file_id in CEDAR:
        if user not in READERS[file_id]:
            assert file_id not in response.text
    listed = client.get("/demo/documents").json()["documents"]
    assert {d["file_id"] for d in listed} == allowed
    event = next(e for e in audit_events(db) if e["event"] == "search_evidence_prepared")
    assert event["actor_subject"] == body["user"]["subject"]
    assert event["permission_version"] == "path-rules-v1"
    assert len(event["decisions"]) == 10
    excluded = [d for d in event["decisions"] if d["decision"] == "search_match_excluded_by_policy"]
    assert len(excluded) == 10-expected
    assert {p["file_id"] for p in event["evidence"]} == allowed


@pytest.mark.parametrize("reader", ["jp", "kamal"])
def test_backend_route_and_api_boundary(tmp_path, reader):
    _, _, client = setup(tmp_path)
    assert client.get("/admin").status_code == 200
    assert len(client.get("/admin/access").json()["rules"]) == len(ACCESS_RULES)
    sign_in(client,reader)
    page = client.get("/admin",follow_redirects=False)
    assert page.status_code == 303 and page.headers["location"].startswith("/search")
    for method,path in [("GET","/index/status"),("POST","/index"),("POST","/scan"),
                        ("GET","/telemetry"),
                        ("GET","/admin/access"),("GET","/openapi.json")]:
        assert client.request(method,path).status_code == 403, path
    assert client.get("/static/index.html").status_code == 404
    assert client.get("/search").status_code == 200
    assert client.get("/auth/me").json()["user"]["id"] == reader


def test_search_page_load_is_not_counted_as_a_query(tmp_path):
    _,_,client = setup(tmp_path)
    client.get("/search")
    assert client.get("/telemetry").json()["query_ms"]["count"] == 0
    client.post("/search",json={"query":"load"})
    assert client.get("/telemetry").json()["query_ms"]["count"] == 1


def test_login_logout_and_forged_identity(tmp_path):
    _,_,client = setup(tmp_path)
    old_cookie = client.cookies.get("engineering_demo_session")
    sign_in(client,"maya")
    client.cookies.clear()
    client.cookies.set("engineering_demo_session",old_cookie)
    assert client.post("/search",json={"query":"load"}).status_code == 401
    client.cookies.clear()
    assert client.post("/auth/login",json={"user_id":"invented-admin"}).status_code == 400
    assert client.post("/search",json={"query":"load","user_id":"jp"},headers={"X-User":"jp"}).status_code == 401
    login = sign_in(client,"kamal")
    assert "HttpOnly" in login.headers["set-cookie"] and "SameSite=strict" in login.headers["set-cookie"]
    result = client.post("/search",json={"query":"incident","user_id":"jp"},headers={"X-User":"jp"})
    assert result.json()["evidence"] == [] and result.json()["matched_passages"] == 0
    assert result.json()["user"]["id"] == "kamal"
    client.post("/auth/logout")
    assert client.get("/auth/me").json()["user"] is None
    assert client.get("/index/status").status_code == 401


def test_permissions_applied_before_result_limit(tmp_path):
    root, _, client = setup(tmp_path)
    for name in ("03-roof-load.md","06-material-certificate.md"):
        path = root / "project-cedar" / name
        path.write_text(path.read_text()+"\n\nUniqueprobe matching evidence.\n")
    client.post("/index")
    sign_in(client,"maya")
    result = client.post("/search",json={"query":"Uniqueprobe","limit":1}).json()
    assert result["matched_passages"] == 1 and not result["truncated"]
    assert result["evidence"][0]["file_id"] == "project-cedar/06-material-certificate.md"


def test_unavailable_permissions_fail_closed_and_are_audited(tmp_path):
    class FailedPermissions:
        def evaluate(self,*args):
            raise OSError("Permissions database unavailable")

    _, db, client = setup(tmp_path,permissions=FailedPermissions())
    sign_in(client,"kamal")
    response = client.post("/search",json={"query":"load"})
    assert response.status_code == 503
    assert "roof" not in response.text and "evidence\":" not in response.text
    assert audit_events(db)[0]["event"] == "authorisation_unavailable"
    assert client.get("/demo/documents").status_code == 503


def test_folder_rules_cover_files_below_them(tmp_path):
    root,_,client = setup(tmp_path)
    (root / "open.md").write_text("# Open\n\nFolderprobe 1.\n")
    (root / "project-northgate" / "calcs").mkdir(parents=True)
    (root / "project-northgate" / "calcs" / "deep.md").write_text("# Deep\n\nFolderprobe 2.\n")
    client.post("/index")
    def found():
        return {p["file_id"] for p in client.post("/search",json={"query":"Folderprobe"}).json()["evidence"]}
    assert found() == {"open.md", "project-northgate/calcs/deep.md"}
    sign_in(client,"kamal")  # Not a reader of project-northgate/, so not of the file two levels down.
    assert found() == {"open.md"}


def test_forbidden_files_do_not_change_the_order_of_permitted_results(tmp_path):
    # Two permitted passages, each with one of the two query words. Ranked on the whole
    # index, twenty forbidden passages full of "alpha" would make "alpha" a common word
    # and move the "beta" passage first: the order would tell Kamal about files he cannot read.
    root, _, client = setup(tmp_path)
    (root / "a.md").write_text("# Notes\n\nAlpha gamma delta.\n")
    (root / "b.md").write_text("# Notes\n\nBeta gamma delta.\n")
    sign_in(client, "kamal")

    def order():
        client.post("/auth/login", json={"user_id": "maya"})
        client.post("/index")
        sign_in(client, "kamal")
        return [p["file_id"] for p in client.post("/search", json={"query": "alpha beta"}).json()["evidence"]]

    before = order()
    (root / "project-northgate").mkdir()
    for n in range(20):
        (root / "project-northgate" / f"f{n}.md").write_text(f"# Alpha {n}\n\nAlpha alpha alpha {n}.\n")
    assert before == ["a.md", "b.md"]
    assert order() == before
