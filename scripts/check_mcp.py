"""Check that the MCP server works, before you connect a chat client.

The script starts the MCP server the same way a chat client does (a local
process over stdio), lists its tools, asks three text questions, and runs the
structured question "S355 components under 5 kN/m²" as SQL, with citations.

    uv run --frozen python -m scripts.check_mcp
    uv run --frozen python -m scripts.check_mcp --user kamal
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
S355_UNDER_5 = ("SELECT subject, project, material_grade, allowable_load_kn_m2, compliance_status, "
                "file_id, table_no, row_no, line FROM components "
                "WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5 ORDER BY allowable_load_kn_m2")
QUESTIONS = (
    "What is the roof load limit at Northgate?",
    "Has building control approved the Northgate warehouse?",
    "Which documents have a roof load greater than 5 kN/m²?",
)


async def check(user: str) -> int:
    server = StdioServerParameters(
        command=sys.executable, cwd=str(ROOT),
        args=["-m", "engineering_search.mcp_server", "--user", user])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [tool.name for tool in (await session.list_tools()).tools]
            print(f"Connected as {user}. Tools: {', '.join(tools)}\n")
            for question in QUESTIONS:
                reply = await session.call_tool("search_evidence", {"question": question})
                answer = json.loads(reply.content[0].text)["answer"]
                print(f"Q: {question}")
                if answer["status"] == "not_found":
                    print("A: not found in documents this user can read\n")
                elif answer["status"] == "partial":
                    print(f"A: no full match. Closest text lacks: {', '.join(answer['missing_words'])}\n")
                elif answer["status"] == "unverified":
                    print(f"A (unverified, does not name {', '.join(answer['unbound_words'])}): {answer['text']}\n")
                elif answer["type"] == "list":
                    first = answer["documents"][0]
                    print(f"A: {answer['count']} documents, for example {first['file_id']}: {first['text']}\n")
                else:
                    page = f", page {answer['page']}" if answer["page"] else ""
                    print(f"A: {answer['text']}\n   Source: {answer['file_id']}{page}, "
                          f"lines {answer['start_line']}-{answer['end_line']}\n")
            print("SQL: S355 components with an allowable load under 5 kN/m²")
            result = json.loads((await session.call_tool("query_sql", {"sql": S355_UNDER_5})).content[0].text)
            if "error" in result:
                print(f"   refused: {result['error']}")
                return 1
            for subject, project, grade, load, status, file_id, table_no, row_no, line in result["rows"]:
                print(f"   {subject:6} {project or '-':10} {grade:9} {load:4} kN/m²  {status or '-':9} "
                      f"{file_id}, line {line}")
            if result["rows"]:
                first = result["rows"][0]
                reply = await session.call_tool("get_document_evidence",
                                                {"file_id": first[5], "table_no": first[6], "row_no": first[7]})
                evidence = json.loads(reply.content[0].text)
                print(f"   Evidence for {first[0]}: \"{evidence['passage']['text']}\" "
                      f"({evidence['file_id']}, line {evidence['line']}, SHA-256 {evidence['source_version'][:12]}…)\n")
    print("The MCP server works.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user", default="jp", choices=["jp", "kamal", "maya"])
    raise SystemExit(asyncio.run(check(parser.parse_args().user)))


if __name__ == "__main__":
    main()
