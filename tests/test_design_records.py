"""The design records database is the source of the ADR and constraint pages.

The first two tests are the check that keeps the pages, the files and the brief in step with
the database. The others break a copy of the database on purpose and show that each check
fails, and that the MCP server returns links that are in the database."""
import asyncio
import json
import shutil

import pytest

from design_records import records
from design_records.mcp_server import create_server


@pytest.fixture
def copy(tmp_path):
    path = tmp_path / "records.sqlite"
    shutil.copy(records.DATABASE, path)
    con = records.connect(path, readonly=False)
    yield con
    con.close()


def test_the_generated_pages_match_the_database():
    con = records.connect()
    differ = [str(path) for path, text in records.render(con).items() if not path.exists() or path.read_text() != text]
    assert differ == []


def test_the_records_are_consistent():
    assert records.check(records.connect()) == []


def test_a_changed_statement_changes_its_constraint_page(copy):
    copy.execute("UPDATE constraints SET statement = 'Answers within 9 seconds.' WHERE id = 'U3'")
    page = records.render(copy)[records.CONSTRAINT_DIR / "use-case.md"]
    assert "> Answers within 9 seconds." in page
    assert "> The answer comes in under 10 seconds." not in page


def test_a_missing_file_is_a_problem(copy):
    copy.execute("INSERT INTO decision_files VALUES (18, 'engineering_search/no_such_file.py', 'implements')")
    assert "decision_files names engineering_search/no_such_file.py, which does not exist" in records.problems(copy)


def test_a_mention_without_a_link_is_a_problem(copy):
    copy.execute("UPDATE decision_sections SET body = body || ' This also bears on P5.' "
                 "WHERE number = 4 AND heading = 'Consequences'")
    assert "ADR 0004 mentions P5 but has no decision_constraints row for it" in records.problems(copy)


def test_a_code_path_without_a_link_is_a_problem(copy):
    copy.execute("UPDATE decision_sections SET body = body || ' See `engineering_search/units.py`.' "
                 "WHERE number = 4 AND heading = 'Consequences'")
    assert "ADR 0004 names engineering_search/units.py but has no decision_files row for it" in records.problems(copy)


def test_a_changed_brief_is_a_problem(copy):
    copy.execute("UPDATE brief_sections SET text = 'Something else.' WHERE heading = 'Scope'")
    assert "brief_sections differ from docs/Starting_document.md" in records.problems(copy)


def test_ids_are_linked_but_not_inside_part_numbers_or_code(copy):
    text = records.link_ids(copy, "S355 and R-310 and C30/37, `U3`, and U3.", "../constraints/")
    assert text == "S355 and R-310 and C30/37, `U3`, and [U3](../constraints/use-case.md#u3)."


def call(name, args):
    result = asyncio.run(create_server().call_tool(name, args))
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def test_the_mcp_server_finds_the_records_that_govern_a_file():
    result = call("governing_records", {"path": "engineering_search/sql.py"})
    assert [d["number"] for d in result["decisions"]] == [16]  # ADR 0016 names sql.py as its projection and safety.
    assert result["decisions"][0]["serves"][:2] == ["U1", "U2"]
    # sql.py stands in for the stores (C4); the whole engineering_search/ folder delivers the prototype (T3).
    assert {c["constraint_id"] for c in result["constraints"]} == {"C4", "T3"}


def test_a_stand_in_file_leads_to_the_decisions_on_its_constraint():
    result = call("governing_records", {"path": "engineering_search/indexing/readers/pdf.py"})
    assert result["decisions"] == []  # No record names pdf.py itself.
    assert ("C3", "stand-in") in {(c["constraint_id"], c["role"]) for c in result["constraints"]}
    through = {d["number"]: d["via"] for d in result["decisions_through_constraints"]}
    assert "C3" in through[20] and "C3" in through[3]  # ADR 0020 and ADR 0003 serve C3.


def test_the_mcp_server_returns_a_constraint_with_its_stand_ins():
    c3 = call("get_constraint", {"constraint_id": "c3"})
    assert c3["standing"] == "assumed"
    assert {"path": "engineering_search/indexing/readers", "role": "stand-in"} in c3["files"]
    assert 20 in {d["number"] for d in c3["decisions"]}


def test_the_mcp_server_refuses_to_write():
    result = call("query_records", {"sql": "DELETE FROM decisions"})
    assert "error" in result
    assert records.connect().execute("SELECT count(*) FROM decisions").fetchone()[0] >= 21
