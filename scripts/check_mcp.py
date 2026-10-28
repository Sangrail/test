"""Check that the MCP server works, before you connect a chat client.

The script starts the MCP server the same way a chat client does (a local
process over stdio), lists its tools, and asks three questions.

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
                elif answer["type"] == "list":
                    first = answer["documents"][0]
                    print(f"A: {answer['count']} documents, for example {first['file_id']}: {first['text']}\n")
                else:
                    page = f", page {answer['page']}" if answer["page"] else ""
                    print(f"A: {answer['text']}\n   Source: {answer['file_id']}{page}, "
                          f"lines {answer['start_line']}-{answer['end_line']}\n")
    print("The MCP server works.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user", default="jp", choices=["jp", "kamal", "maya"])
    raise SystemExit(asyncio.run(check(parser.parse_args().user)))


if __name__ == "__main__":
    main()
