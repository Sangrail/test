---
status: accepted
date: 2026-10-28
---
<!-- Generated from design/records/records.sqlite. Edit the database, then run `uv run --frozen python -m design_records generate`. -->

# Put all search logic in one service, used by the web page and the chat agent

**Serves:** [C1](../constraints/environment.md#c1) (a broader architecture exists), [C5](../constraints/environment.md#c5) (a chat-agent shell calls backend APIs and tools), [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [U4](../constraints/use-case.md#u4) (100% confidence in the source).

## Context

The use case has two front ends: a search bar on a web page, and a chat-agent shell that calls backend APIs and tools ([C5](../constraints/environment.md#c5)). The broader architecture already exists ([C1](../constraints/environment.md#c1)), so this component must be a backend that other parts call, not a closed application. Before this decision, the search, permission and audit logic was in the HTTP routes of `app.py`. The MCP server had to call the web app over HTTP, or copy the logic. A copy can drift: one front end could check permissions ([R1](../constraints/requirements.md#r1)) or audit the sources ([U4](../constraints/use-case.md#u4)) differently from the other.

## Decision

- [`service.py`](../../engineering_search/service.py) holds all search logic in `SearchService`: search, read one file, permissions, audit, index operations and uploads.
- [`app.py`](../../engineering_search/app.py) is the HTTP layer only. It does sign-in, roles, request checks and the routes. Each route calls the service. The upload routes are an MVP shortcut: they call `service.queue` directly for the job steps.
- [`mcp_server.py`](../../engineering_search/mcp_server.py) calls the same service directly, with the same index, permissions and audit log. It does not start the web app.
- The service raises `ServiceError(status, detail)`. The web app changes it into an HTTP reply. The MCP server returns it as an error result.
- Every import points down: entry points (`__main__.py`, `mcp_server.py`) → [`runtime.py`](../../engineering_search/runtime.py) → `app.py` → `service.py` → the indexer (`indexing/`), domain logic (`answer.py`, `access.py`) and adapters (`store.py`, `adapters.py`, `jobs.py`) → `core.py` and `query.py`. `service.py` does not import `store.py`. `runtime.py` opens the stores and gives them to the service as objects. [design/code-architecture.png](../../design/code-architecture.png) shows each import.

## Consequences

- Both front ends give the same answer, check the same permissions and write the same audit events. One test of the service covers both.
- A new front end (for example a REST client in the existing architecture, [C1](../constraints/environment.md#c1)) needs only a thin layer.
- Each process has its own `SearchService`: the web app in one process, the MCP server in another. Both open the same SQLite files. SQLite allows this, but a shared service needs one backend that many clients call ([design/SCALING.md](../../design/SCALING.md)).
- `SearchService` is a large class. It is acceptable for the MVP. The MVP shortcuts are listed in [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Implementation

Done. Tests go through the web app (`tests/test_*.py`) and through the service directly (`tests/test_no_leaks.py` calls `service.read`). `scripts/check_mcp.py` starts the MCP server as a chat client does and calls its tools.
