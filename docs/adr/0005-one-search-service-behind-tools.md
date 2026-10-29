# 5. One search service behind MCP tools and HTTP; the chat shell owns the conversation

The brief's chat-agent shell calls backend APIs or tools ([C5](../constraints/constraints.md#c5)). One `SearchService` holds the search, the SQL, the permissions and the audit; an MCP server and an HTTP app are thin front ends on it. The MVP does not build a chat interface: Claude Code, Codex or Pi is the shell, and the web search page is only a test harness.

**Status:** accepted.

**Serves:** [C5](../constraints/constraints.md#c5), [C1](../constraints/constraints.md#c1) (a narrow interface that an existing architecture can place), [B2](../constraints/background.md#b2).

**Considered options:** build a chat UI with its own model (builds what exists, and brings model governance into the MVP, [G3](../constraints/gaps.md#g3)); separate logic per front end (two places to keep the permissions right).

**Consequences:** both front ends get the same answers, permission checks and audit. The MCP user is taken from a flag and is not verified ([G1](../constraints/gaps.md#g1)).

**Implemented by:** [`service.py`](../../engineering_search/service.py), [`mcp_server.py`](../../engineering_search/mcp_server.py), [`app.py`](../../engineering_search/app.py). **Tested by:** [`tests/test_mcp_stdio.py`](../../tests/test_mcp_stdio.py), [`tests/test_use_case.py`](../../tests/test_use_case.py).
