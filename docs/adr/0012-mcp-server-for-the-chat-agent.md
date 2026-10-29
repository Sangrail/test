---
status: superseded in part by 0016 (the tools) and 0018 (admission); stdio and the identity hole stand
date: 2026-10-28
---
# Give the chat agent an MCP server over stdio, and accept an unverified user for the MVP only

> **Superseded in part** by [ADR 0016](0016-structured-facts-and-client-written-sql.md) (five structured tools and a coverage tool for the index team) and [ADR 0018](0018-admission-control-and-the-time-budget.md) (admission control). The stdio transport and the identity hole stand.

**Serves:** C5 (a chat-agent shell calls backend APIs and tools), U6 (no file formats, schema, query languages or jargon), S1 (MVP only), R1 (no information from forbidden documents).

## Context

The constraints include a chat-agent shell that can call backend APIs and tools (C5). The users do not want to learn file formats, schema, query languages or jargon (U6). A chat agent lets them ask in their own words, and lets the agent ask follow-up questions. The Model Context Protocol (MCP) is the standard way for chat clients (Claude Desktop, Claude Code and others) to call tools. The simplest MCP transport is stdio: the chat client starts the server as a local process. A stdio server has no sign-in. It knows the user only from its start command. R1 is an absolute requirement, so this is a security hole.

## Decision

- Provide an MCP server with two tools:
  - `search_evidence(question, mode, within, limit, page)`: the same search as the search bar.
  - `read_evidence(file_id, page)`: all indexed passages of one readable file.
- Use the stdio transport for the MVP (S1).
- Take the user from the `--user` flag (or `SEARCH_USER`). Nothing verifies it.
- Accept this hole for the MVP only, with public and synthetic test data only (S3). Record it in the module docstring, [docs/MCP.md](../MCP.md), the README and the system design diagram.
- The tool results contain the same permitted evidence as the web page. The agent must quote the answer and its source, not write its own value (U4).

## Consequences

- A person who can change the chat client configuration can read as any user. Do not use the stdio server with real restricted files.
- The fix: run the MCP server remotely over Streamable HTTP, behind the company sign-in (OAuth). Take the user from the verified token on each request. The permissions and audit log then match the real person ([docs/MCP.md](../MCP.md#the-security-hole-the-mcp-user-is-not-verified)).
- Tool results go to the language-model provider of the chat client. The company must approve that provider for the documents.
- The agent can summarise or change the exact text. The tool gives exact text and sources, but the agent's reply is outside the control of this service.

## Implementation

Done for stdio, with the hole. [`mcp_server.py`](../../engineering_search/mcp_server.py), with `mcp==1.27.2` (FastMCP). [ADR 0016](0016-structured-facts-and-client-written-sql.md) adds the structured tools: `describe_schema`, `list_tables`, `describe_table`, `query_sql` and `get_document_evidence`. The index team also gets `get_index_coverage`. Verified on 29 October 2026 with Claude Code, Codex and Pi over local stdio; the project files `.mcp.json` and `.pi/mcp.json` start the server. Install and test steps: [docs/MCP.md](../MCP.md). Checks: `uv run --frozen python -m scripts.check_mcp` and `tests/test_mcp_stdio.py`, which run the server as a chat client does. The remote server with OAuth is in [TODO.md](../../TODO.md#before-use-as-a-shared-service).
