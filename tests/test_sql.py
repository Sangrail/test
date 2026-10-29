"""Constrained SQL over the structured data, through the HTTP API, against test-repository/.

The expected rows are written out by hand from the fixtures that
scripts/make_structured_fixtures.py writes, so a wrong extraction rule or a
leak through the projection fails here."""
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from helpers import TEST_REPOSITORY

SCHEDULE = "project-harbour/harbour-component-schedule.csv"
ROOF = "project-harbour/harbour-roof-schedule.xlsx"
BASIS = "project-harbour/harbour-design-basis.md"
REGISTER = "registers/component-register.csv"
S355_UNDER_5 = ("SELECT subject, file_id, line, allowable_load_kn_m2 FROM components "
                "WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5 ORDER BY file_id, line")
# Every S355 row with an allowable load under 5 kN/m², by hand from the fixtures. Not here:
# B-105 (6.0), R-311 (5.2), CB-14 (5.6), R-312 (S460), F-021 (an imposed load, a demand),
# R-313 (a formula with no cached value), and the floor design load in prose.
EXPECTED = {("M-401", BASIS, 13, 4.2), ("B-104", SCHEDULE, 3, 4.5), ("B-106", SCHEDULE, 5, 3.5),
            ("R-310", ROOF, 2, 3.8), ("B-104", REGISTER, 2, 4.5), ("CB-12", REGISTER, 3, 4.8),
            ("RG-02", REGISTER, 5, 3.9)}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    app = create_app(root=TEST_REPOSITORY, audit=SQLiteAuditStore(state / "audit.sqlite3"))
    with TestClient(app) as client:
        client.post("/auth/login", json={"user_id": "maya"})
        assert client.post("/index").status_code == 200
        client.audit_path = state / "audit.sqlite3"
        yield client


def sql(client, user, statement, limit=100):
    client.post("/auth/login", json={"user_id": user})
    return client.post("/sql", json={"sql": statement, "limit": limit})


def rows(client, user, statement):
    response = sql(client, user, statement)
    assert response.status_code == 200, response.text
    return response.json()["rows"]


def last_audit(client):
    with sqlite3.connect(client.audit_path) as db:
        return json.loads(db.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()[0])


def test_s355_components_under_5_kn_per_m2_with_citations(client):
    assert {tuple(r) for r in rows(client, "jp", S355_UNDER_5)} == EXPECTED


def test_a_user_gets_only_rows_from_files_they_may_read(client):
    # Kamal may not read the roof schedule: R-310 is not returned, and not counted.
    assert {tuple(r) for r in rows(client, "kamal", S355_UNDER_5)} == EXPECTED - {("R-310", ROOF, 2, 3.8)}
    assert rows(client, "kamal", f"SELECT count(*) FROM facts WHERE file_id = '{ROOF}'") == [[0]]
    assert rows(client, "kamal", "SELECT count(*) FROM table_rows WHERE json_extract(cells_json, '$[0]') = 'R-310'") == [[0]]
    assert rows(client, "jp", f"SELECT count(*) FROM facts WHERE file_id = '{ROOF}'") == [[15]]


def test_capacity_and_demand_stay_apart(client):
    slab = rows(client, "jp", "SELECT allowable_load_kn_m2, imposed_load_kn_m2 FROM components WHERE subject = 'F-021'")
    assert slab == [[None, 3.2]]
    roles = rows(client, "jp", "SELECT DISTINCT role FROM facts WHERE parameter = 'allowable_distributed_load'")
    assert roles == [["capacity"]]


def test_a_project_column_sets_the_project_of_each_register_row(client):
    projects = rows(client, "jp", f"SELECT subject, project, project_source FROM facts "
                                  f"WHERE file_id = '{REGISTER}' AND parameter = 'material_grade' ORDER BY line")
    assert projects == [["B-104", "Harbour", "row"], ["CB-12", "Cedar", "row"], ["CB-14", "Cedar", "row"],
                        ["RG-02", "Riverside", "row"]]
    assert rows(client, "jp", f"SELECT DISTINCT project, project_source FROM facts WHERE file_id = '{SCHEDULE}'") == [
        ["Harbour", "folder"]]


def test_the_example_queries_in_the_mcp_guide(client):
    # docs/MCP.md, "Example SQL". The expected rows are from the fixtures, by hand.
    open_items = ("SELECT subject, compliance_status, file_id, line FROM components "
                  "WHERE project = 'Harbour' AND compliance_status <> 'Approved' ORDER BY file_id, line")
    assert rows(client, "jp", open_items) == [["B-106", "Pending", SCHEDULE, 5], ["R-313", "Pending", ROOF, 5]]
    assert rows(client, "kamal", open_items) == [["B-106", "Pending", SCHEDULE, 5]]
    joined = rows(client, "jp", "SELECT c.subject, r.cells_json, c.line FROM components c JOIN table_rows r "
                                "ON r.file_id = c.file_id AND r.table_no = c.table_no AND r.row_no = c.row_no "
                                "WHERE c.subject = 'B-106'")
    assert [(s, json.loads(cells), line) for s, cells, line in joined] == [
        ("B-106", ["B-106", "Beam", "Mezzanine edge", "S355J2+N", "3.5", "", "Pending"], 5)]
    by_project = "SELECT project, count(DISTINCT file_id), count(*) FROM facts WHERE project = 'Harbour' GROUP BY project"
    assert rows(client, "jp", by_project) == [["Harbour", 5, 48]]  # 3 facts from the DXF title block
    assert rows(client, "kamal", by_project) == [["Harbour", 4, 33]]  # Without the roof schedule's 15 facts.
    demands = "SELECT subject FROM components WHERE imposed_load_kn_m2 IS NOT NULL ORDER BY subject"
    assert rows(client, "kamal", demands) == [["F-021"], ["F-022"]]
    # 5 N/m² is 0.005 kN/m²: units are normalised, intent is not.
    assert rows(client, "jp", "SELECT subject FROM components WHERE material_grade LIKE 'S355%' "
                              "AND allowable_load_kn_m2 < 0.005") == []


@pytest.mark.parametrize("statement", [
    "DELETE FROM facts",
    "SELECT 1; DELETE FROM facts",
    "PRAGMA table_info(facts)",
    "ATTACH DATABASE ':memory:' AS other",
    "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) SELECT count(*) FROM n",
    "SELECT randomblob(1000000)",
    "SELECT load_extension('evil')",
    "SELECT count(*) FROM facts a, facts b, facts c, facts d",  # runs past the step budget
])
def test_statements_that_write_escape_or_run_away_are_refused_and_audited(client, statement):
    response = sql(client, "jp", statement)
    assert response.status_code == 400, response.text
    event = last_audit(client)
    assert event["event"] == "sql_query_refused" and event["returned_rows"] == 0
    # The audit keeps a fixed category, not SQLite's message, which can quote the statement.
    assert event["error"] in {"not_select", "not_allowed", "too_slow", "invalid"}
    assert "evil" not in json.dumps(event) and "facts" not in json.dumps(event)
    assert rows(client, "jp", "SELECT count(*) FROM documents") == [[145]]  # Nothing was changed.


def test_the_row_limit_truncates(client):
    body = sql(client, "jp", "SELECT * FROM facts", limit=5).json()
    assert body["row_count"] == 5 and body["truncated"] is True


def test_the_audit_records_the_statement_hash_and_cited_files_not_the_rows(client):
    rows(client, "kamal", S355_UNDER_5)
    event = last_audit(client)
    assert event["event"] == "sql_query_executed" and event["returned_rows"] == 6
    assert event["result_files"] == sorted({BASIS, SCHEDULE, REGISTER})
    assert event["files_excluded_by_policy"] > 0 and event["sql_characters"] == len(S355_UNDER_5)
    assert "B-104" not in json.dumps(event) and "S355" not in json.dumps(event)


def test_a_cited_row_is_the_line_in_the_file(client):
    client.post("/auth/login", json={"user_id": "jp"})
    evidence = client.get(f"/evidence/{SCHEDULE}/tables/1/rows/2").json()
    raw_line = (TEST_REPOSITORY / SCHEDULE).read_text(encoding="utf-8").splitlines()[evidence["line"] - 1]
    assert evidence["passage"]["text"] == raw_line == "B-104,Beam,Level 2 grid C,S355J2,4.5,,Approved"
    assert dict(zip(evidence["columns"], evidence["cells"]))["Allowable UDL (kN/m²)"] == "4.5"
    client.post("/auth/login", json={"user_id": "kamal"})
    # A forbidden row gets the same answer as a missing one.
    assert client.get(f"/evidence/{ROOF}/tables/1/rows/1").status_code == 404
    assert client.get(f"/evidence/{SCHEDULE}/tables/1/rows/99").status_code == 404


def test_the_schema_holds_no_document_data(client):
    client.post("/auth/login", json={"user_id": "kamal"})
    schema = client.get("/sql/schema").json()
    assert set(schema["tables"]) == {"documents", "facts", "components", "table_rows", "source_tables"}
    assert "allowable_load_kn_m2" in client.get("/sql/schema?table=components").json()["columns"]
    assert client.get("/sql/schema?table=sqlite_master").status_code == 404
