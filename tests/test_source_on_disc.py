"""A source is the file on disc as it is now, and the user asks in plain language.

  - A quote must still be what the file holds. A cited file that changed (or was
    deleted) after it was indexed is refused, not quoted, until the index is refreshed.
  - A question that is a SQL statement is refused: the user never writes SQL (B4).
"""
import pytest
from fastapi.testclient import TestClient

from engineering_search.access import USERS
from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.service import ServiceError
from engineering_search.store import SQLiteSearchIndex

MAYA = next(u for u in USERS if u["id"] == "maya")
KAMAL = next(u for u in USERS if u["id"] == "kamal")
QUESTION = "What is the roof load limit?"


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "roof.md").write_text("# Roof\n\nThe roof load limit is 5 kN/m².\n")
    (root / "other.md").write_text("# Annex\n\nThe roof load limit is 4 kN/m² in the annex.\n")
    app = create_app(root=root, index=SQLiteSearchIndex(), audit=SQLiteAuditStore(tmp_path / "audit.sqlite3"))
    client = TestClient(app)
    client.post("/auth/login", json={"user_id": "maya"})
    assert client.post("/index").status_code == 200
    return root, client, app.state.service


def refusals(service):
    return [e["payload"] for e in service.audit.read_page(1, 100)["events"]
            if e["payload"]["event"] == "request_refused"]


def ask(client, question=QUESTION):
    response = client.post("/search", json={"query": question, "mode": "answer"})
    assert response.status_code == 200, response.text
    return response.json()


def test_an_unchanged_file_is_quoted(setup):
    root, client, _ = setup
    body = ask(client)
    assert body["changed_files"] == []
    assert body["answer"]["text"] in (root / body["answer"]["file_id"]).read_text()


def test_a_file_edited_after_indexing_is_refused_until_the_index_is_refreshed(setup):
    root, client, service = setup
    (root / "roof.md").write_text("# Roof\n\nThe roof load limit is 9 kN/m².\n")
    body = ask(client)
    assert body["changed_files"] == ["roof.md"]
    assert body["answer"]["file_id"] == "other.md"  # picked again, without the changed file
    assert all(p["file_id"] != "roof.md" for p in body["evidence"])
    assert "5 kN/m²" not in str(body)  # the old text is not quoted
    with pytest.raises(ServiceError) as refused:
        service.read(MAYA, "roof.md")
    assert refused.value.status == 409 and refused.value.detail["changed_files"] == ["roof.md"]
    (event,) = refusals(service)
    assert (event["operation"], event["reason"], event["changed_files"]) == ("read", "changed_on_disc", ["roof.md"])
    assert event["actor_subject"] == MAYA["subject"]

    assert client.post("/index").status_code == 200
    body = ask(client, "roof load limit 9 kN/m²")
    assert body["changed_files"] == [] and body["answer"]["file_id"] == "roof.md"
    assert "9 kN/m²" in body["answer"]["text"]
    assert service.read(MAYA, "roof.md")["evidence"]


def test_a_file_deleted_after_indexing_is_not_quoted(setup):
    root, client, _ = setup
    (root / "other.md").unlink()
    body = ask(client, "roof load limit annex")
    assert "other.md" in body["changed_files"]
    assert all(p["file_id"] != "other.md" for p in body["evidence"])
    assert body["answer"].get("file_id") != "other.md"


def test_a_table_edited_after_indexing_is_left_out_of_sql_and_its_rows_are_refused(setup):
    root, client, service = setup
    (root / "schedule.csv").write_text("Mark,Material grade,Allowable load (kN/m2)\nB-1,S355,4.5\n")
    (root / "other.csv").write_text("Mark,Material grade,Allowable load (kN/m2)\nB-2,S275,3.0\n")
    assert client.post("/index").status_code == 200
    query = "SELECT subject, file_id, table_no, row_no FROM components ORDER BY subject"
    assert [row[0] for row in service.query_sql(MAYA, query)["rows"]] == ["B-1", "B-2"]

    (root / "schedule.csv").write_text("Mark,Material grade,Allowable load (kN/m2)\nB-1,S275,9.0\n")
    result = service.query_sql(MAYA, query)
    assert result["changed_files"] == ["schedule.csv"]
    assert [row[0] for row in result["rows"]] == ["B-2"]
    no_file_id = service.query_sql(MAYA, "SELECT subject FROM components")  # no file_id column to check
    assert no_file_id["rows"] == [["B-2"]]
    with pytest.raises(ServiceError) as refused:
        service.table_row_evidence(MAYA, "schedule.csv", 1, 1)
    assert refused.value.status == 409 and refused.value.detail["changed_files"] == ["schedule.csv"]


@pytest.mark.parametrize("statement", [
    "SELECT * FROM facts",
    "select subject, material_grade from components",
    "SELECT subject FROM components WHERE project = 'Harbour'",
    "SELECT count(*) FROM documents",
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "DROP TABLE facts",
    "roof load; DELETE FROM facts",
    "roof load UNION SELECT file_id FROM documents",
    "SELECT subject FROM components",  # one plain column, no WHERE
    "SELECT subjekt FROM components",  # a misspelt column is still SQL
    "(SELECT subject FROM components);",
    "PRAGMA table_info(facts)",
    "DROP TABLE users",  # a table the projection does not have
])
def test_a_question_that_is_sql_is_refused(setup, statement):
    _, client, service = setup
    response = client.post("/search", json={"query": statement})
    assert response.status_code == 422 and "plain language" in response.json()["detail"]
    with pytest.raises(ServiceError) as refused:  # the MCP tool search_evidence calls this
        service.search(MAYA, statement)
    assert refused.value.status == 422
    events = refusals(service)  # both refusals are audited, by length and hash, never by text
    assert [(e["operation"], e["reason"], e["query_characters"]) for e in events] == [
        ("search", "sql_statement", len(statement))] * 2
    assert all(statement not in str(e) for e in events)


@pytest.mark.parametrize("question", [
    "Select the beams from the roof",
    "select the roof load from the annex where the limit is stated",
    "Update me on the roof load limit",
    "Which documents select S355 steel?",  # "select S355 steel" compiles, but not where a statement starts
    "Select 5 beams",  # compiles, but has no FROM
    "With S355, which beams are approved?",
    "Drop test results for the crane",
    "Create a list of approved drawings",
])
def test_a_plain_question_that_starts_like_sql_is_answered(setup, question):
    _, client, _ = setup
    assert client.post("/search", json={"query": question}).status_code == 200


def test_a_read_of_a_file_the_user_may_not_read_is_refused_and_audited(setup):
    root, client, service = setup
    (root / "project-northgate").mkdir()
    (root / "project-northgate" / "calc.md").write_text("# Calc\n\nThe roof load limit is 1 kN/m².\n")
    assert client.post("/index").status_code == 200
    with pytest.raises(ServiceError) as refused:
        service.read(KAMAL, "project-northgate/calc.md")
    assert refused.value.status == 404  # the same answer as for a missing file
    (event,) = refusals(service)
    assert (event["operation"], event["reason"]) == ("read", "not_found_or_not_permitted")
    assert event["actor_subject"] == KAMAL["subject"] and "evidence" not in event
