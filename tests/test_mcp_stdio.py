"""The MCP server over stdio, started the way Claude Code, Codex and Pi start it.

A real MCP client session: initialise, list tools, call query_sql and
get_document_evidence. Expected rows are from the fixtures, as in test_sql.py."""
import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from helpers import TEST_REPOSITORY

ROOT = Path(__file__).resolve().parents[1]
S355_UNDER_5 = ("SELECT subject, file_id, table_no, row_no FROM components "
                "WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5 ORDER BY file_id, line")


async def session_as(user: str, state: Path, calls):
    server = StdioServerParameters(command=sys.executable, cwd=str(ROOT),
                                   args=["-m", "engineering_search.mcp_server", "--user", user,
                                         "--documents", str(TEST_REPOSITORY), "--state-dir", str(state)])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            results = [json.loads((await session.call_tool(name, args)).content[0].text) for name, args in calls]
            return tools, results


def test_a_stdio_client_answers_the_structured_question_with_citations(tmp_path):
    tools, (result, evidence) = asyncio.run(session_as("kamal", tmp_path, [
        ("query_sql", {"sql": S355_UNDER_5}),
        ("get_document_evidence", {"file_id": "project-harbour/harbour-component-schedule.csv",
                                   "table_no": 1, "row_no": 2}),
    ]))
    assert {"search_evidence", "read_evidence", "describe_schema", "list_tables", "describe_table",
            "query_sql", "get_document_evidence"} <= tools
    assert "get_index_coverage" not in tools  # Kamal is not on the index team.
    subjects = [row[0] for row in result["rows"]]
    assert sorted(subjects) == ["B-104", "B-104", "B-106", "CB-12", "M-401", "RG-02"]  # No R-310 for Kamal.
    assert evidence["passage"]["text"] == "B-104,Beam,Level 2 grid C,S355J2,4.5,,Approved"


def test_the_index_team_gets_the_coverage_tool(tmp_path):
    tools, (report,) = asyncio.run(session_as("maya", tmp_path, [("get_index_coverage", {"gaps_limit": 10})]))
    assert "get_index_coverage" in tools
    gaps = {gap["file_id"]: gap["status"] for gap in report["gaps"]}
    assert gaps["project-harbour/cad/hangar-frame.jt"] == "NO_READER"
    assert gaps["project-harbour/scans/site-survey-scan.pdf"] == "NO_TEXT_LAYER"
