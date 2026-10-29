"""The design records database is the source of truth for the ADR and constraint pages.

The first two tests are the check that keeps the generated files, the code and the brief in
step with the database. The history tests change a copy of the database through its views,
as a person would in the sqlite3 shell, and show that each change adds a version, that past
versions cannot be edited, and that a change to an item flags the decisions made under it.
The rest break a copy on purpose and show that each check fails, that the viewer needs no
network, and that the MCP server returns what is in the database and cannot activate."""
import asyncio
import json
import re
import shutil
import sqlite3

import pytest

from design_records import records
from design_records.mcp_server import create_server


@pytest.fixture
def path(tmp_path):
    copy = tmp_path / "design.sqlite"
    shutil.copy(records.DATABASE, copy)
    return copy


@pytest.fixture
def copy(path):
    con = records.connect(path, readonly=False)
    yield con
    con.close()


def test_the_generated_files_match_the_database():
    con = records.connect()
    differ = [str(p) for p, text in records.render(con).items() if not p.exists() or p.read_text() != text]
    assert differ == []


def test_the_records_are_consistent():
    assert records.check(records.connect()) == []


# --- History -------------------------------------------------------------------------------

def test_a_change_adds_a_version_and_keeps_the_old_one(copy):
    copy.execute("UPDATE constraint_current SET statement = 'Answers within 9 seconds.', "
                 "change_reason = 'Tighter budget' WHERE id = 'U3'")
    versions = copy.execute("SELECT version, lifecycle, statement FROM constraint_versions WHERE constraint_id = 'U3' "
                            "ORDER BY version").fetchall()
    assert [(v[0], v[1]) for v in versions] == [(1, "displaced"), (2, "active")]
    assert versions[0][2] == "The answer comes in under 10 seconds."
    page = records.render(copy)[records.CONSTRAINT_DIR / "use-case.md"]
    assert "> Answers within 9 seconds." in page
    assert "It read: “The answer comes in under 10 seconds.”" in page  # The history keeps the old wording.


def test_active_and_past_versions_cannot_be_edited_or_deleted(copy):
    with pytest.raises(sqlite3.DatabaseError, match="cannot be edited"):
        copy.execute("UPDATE constraint_versions SET statement = 'Quietly changed.' WHERE constraint_id = 'U3'")
    with pytest.raises(sqlite3.DatabaseError, match="are kept"):
        copy.execute("DELETE FROM decision_versions WHERE number = 1")
    with pytest.raises(sqlite3.DatabaseError, match="change a draft only"):
        copy.execute("UPDATE decision_sections SET body = 'Quietly changed.' WHERE number = 18")


def test_a_change_needs_a_reason(copy):
    with pytest.raises(sqlite3.DatabaseError, match="change_reason"):
        copy.execute("UPDATE constraint_current SET statement = 'No reason given.' WHERE id = 'U3'")


def test_a_new_wording_flags_the_decisions_made_under_the_old_one(copy):
    copy.execute("UPDATE constraint_current SET statement = 'Answers within 9 seconds.', change_reason = 'x' WHERE id = 'U3'")
    flagged = {r[0] for r in copy.execute("SELECT number FROM needs_review WHERE constraint_id = 'U3'")}
    assert 18 in flagged  # ADR 0018 (the time budget) serves U3.
    page = records.render(copy)[records.ADR_DIR / "0018-admission-control-and-the-time-budget.md"]
    assert "**Needs review:** [U3](../constraints/use-case.md#u3) was changed after this decision (made under version 1, now version 2)." in page


def test_a_new_assessment_does_not_flag_decisions(copy):
    copy.execute("UPDATE constraint_current SET mvp = 'Measured again.', standing = 'met', change_reason = 'x' WHERE id = 'U3'")
    assert copy.execute("SELECT count(*) FROM needs_review").fetchone()[0] == 0


def test_a_review_clears_the_flag_and_survives_a_new_version_of_the_decision(copy):
    copy.execute("UPDATE constraint_current SET statement = 'Answers within 9 seconds.', change_reason = 'x' WHERE id = 'U3'")
    copy.execute("INSERT INTO reviews (number, constraint_id, note) VALUES (18, 'U3', 'The budget still fits.')")
    assert 18 not in {r[0] for r in copy.execute("SELECT number FROM needs_review")}
    copy.execute("UPDATE decision_current SET summary = 'Reworded.', change_reason = 'Typo' WHERE number = 18")
    assert 18 not in {r[0] for r in copy.execute("SELECT number FROM needs_review")}


def test_a_decision_without_sections_or_links_cannot_be_activated(copy):
    copy.execute("INSERT INTO decision_current (number, slug, title, summary, change_reason) "
                 "VALUES (99, 'empty', 'Empty', 'Empty', 'Test')")
    with pytest.raises(sqlite3.DatabaseError, match="four sections"):
        copy.execute("UPDATE decision_versions SET lifecycle = 'active' WHERE number = 99")
    copy.execute("UPDATE decision_sections SET body = 'Written.' WHERE number = 99")
    with pytest.raises(sqlite3.DatabaseError, match="serve at least one"):
        copy.execute("UPDATE decision_versions SET lifecycle = 'active' WHERE number = 99")


def test_a_withdrawn_item_keeps_its_anchor_and_flags_its_decisions(copy):
    copy.execute("DELETE FROM constraint_current WHERE id = 'R6'")
    page = records.render(copy)[records.CONSTRAINT_DIR / "requirements.md"]
    withdrawn = page.split("## Withdrawn", 1)[1]
    assert '<a id="r6"></a>' in withdrawn
    assert (18, "withdrawn") in {(r[0], r[1]) for r in copy.execute("SELECT number, change FROM needs_review")}


# --- Checks --------------------------------------------------------------------------------

def test_a_missing_file_is_a_problem(copy):
    copy.execute("INSERT INTO drafts (kind, id, change_reason) VALUES ('decision', '18', 'Test')")
    copy.execute("INSERT INTO decision_files SELECT 18, version, 'engineering_search/no_such_file.py', 'implements' "
                 "FROM decision_versions WHERE number = 18 AND lifecycle = 'proposed'")
    copy.execute("UPDATE decision_versions SET lifecycle = 'active' WHERE number = 18 AND lifecycle = 'proposed'")
    assert "decision_file_current names engineering_search/no_such_file.py, which does not exist" in records.problems(copy)


def add_to_consequences(con, number, text):
    con.execute("UPDATE decision_section_current SET body = body || ?, change_reason = 'Test' "
                "WHERE number = ? AND heading = 'Consequences'", (text, number))


def test_a_mention_without_a_link_is_a_problem(copy):
    add_to_consequences(copy, 4, " This also bears on P5.")
    assert "ADR 0004 mentions P5 but has no decision_constraints row for it" in records.problems(copy)


def test_a_code_path_without_a_link_is_a_problem(copy):
    add_to_consequences(copy, 4, " See `engineering_search/units.py`.")
    assert "ADR 0004 names engineering_search/units.py but has no decision_files row for it" in records.problems(copy)


def test_a_changed_brief_is_a_problem(copy):
    copy.execute("UPDATE brief_sections SET text = 'Something else.' WHERE heading = 'Scope'")
    assert "brief_sections differ from docs/Starting_document.md" in records.problems(copy)


def test_a_changed_schema_is_a_problem(copy):
    copy.execute("DROP TRIGGER constraint_version_update")
    assert "the database schema differs from design_records/schema.sql" in records.problems(copy)


def test_ids_are_linked_but_not_inside_part_numbers_or_code(copy):
    text = records.link_ids(copy, "S355 and R-310 and C30/37, `U3`, and U3.", "../constraints/")
    assert text == "S355 and R-310 and C30/37, `U3`, and [U3](../constraints/use-case.md#u3)."


def test_the_viewer_needs_no_network_and_carries_the_history():
    html = records.render(records.connect())[records.VIEWER]
    assert re.search(r"<script[^>]+src=|<link[^>]+href=|@import|fetch\(", html) is None
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    c1 = [(v["version"], v["lifecycle"]) for v in data["item_versions"] if v["constraint_id"] == "C1"]
    assert c1 == [(1, "displaced"), (2, "active")]


# --- The MCP server ------------------------------------------------------------------------

def call(name, args, database=records.DATABASE):
    result = asyncio.run(create_server(database).call_tool(name, args))
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def test_the_mcp_server_finds_the_records_that_govern_a_file():
    result = call("governing_records", {"path": "engineering_search/sql.py"})
    assert [d["number"] for d in result["decisions"]] == [16]  # ADR 0016 names sql.py as its projection and safety.
    assert result["decisions"][0]["serves"][:2] == ["U1", "U2"]
    assert result["decisions"][0]["exceeds_scope"] == ["S5"]  # It reads tables into facts, which connectors do.
    # sql.py stands in for the stores (C4); the whole engineering_search/ folder delivers the prototype (T3).
    assert {c["constraint_id"] for c in result["constraints"]} == {"C4", "T3"}


def test_a_stand_in_file_leads_to_the_decisions_on_its_constraint():
    result = call("governing_records", {"path": "engineering_search/indexing/readers/pdf.py"})
    assert result["decisions"] == []  # No record names pdf.py itself.
    assert ("C3", "stand-in") in {(c["constraint_id"], c["role"]) for c in result["constraints"]}
    through = {d["number"]: d["via"] for d in result["decisions_through_constraints"]}
    assert "C3" in through[20] and "C3" in through[3]  # ADR 0020 and ADR 0003 serve C3.


def test_the_mcp_server_returns_an_item_with_its_stand_ins_and_history():
    c3 = call("get_constraint", {"constraint_id": "c3"})
    assert c3["standing"] == "assumed"
    assert {"path": "engineering_search/indexing/readers", "role": "stand-in"} in c3["files"]
    assert 20 in {d["number"] for d in c3["decisions"]}
    assert [h["lifecycle"] for h in c3["history"]] == ["displaced", "active"]
    first = call("get_constraint", {"constraint_id": "C3", "version": 1})
    assert "stand-in" not in {f["role"] for f in first["files"]}  # The stand-ins were named by ADR 0020, in version 2.


def test_a_proposal_is_a_draft_and_changes_nothing_current(path):
    result = call("propose_change", {"kind": "constraint", "record": "R5", "change_reason": "Measured on 400 files",
                                     "changes": {"mvp": "Measured: 0.4 s on 400 files."}, "changed_by": "test"}, path)
    assert result["draft"]["version"] == 2
    con = records.connect(path)
    assert con.execute("SELECT lifecycle, mvp FROM constraint_versions WHERE constraint_id = 'R5' AND version = 2").fetchone()[:] \
        == ("proposed", "Measured: 0.4 s on 400 files.")
    assert con.execute("SELECT version FROM constraint_current WHERE id = 'R5'").fetchone()[0] == 1
    assert "draft: constraint R5 version 2 (Measured on 400 files)" in records.warnings(con)


def test_a_proposal_cannot_activate(path):
    result = call("propose_change", {"kind": "decision", "record": "18", "change_reason": "Try",
                                     "changes": {"lifecycle": "active"}}, path)
    assert "error" in result
    assert records.connect(path).execute("SELECT count(*) FROM drafts").fetchone()[0] == 0


def test_the_mcp_query_tool_refuses_to_write(path):
    result = call("query_records", {"sql": "DELETE FROM drafts"}, path)
    assert "error" in result
    result = call("query_records", {"sql": "INSERT INTO reviews (number, constraint_id, note) VALUES (18, 'U3', 'x')"}, path)
    assert "error" in result
    assert records.connect(path).execute("SELECT count(*) FROM decision_reviews").fetchone()[0] == \
        records.connect().execute("SELECT count(*) FROM decision_reviews").fetchone()[0]
