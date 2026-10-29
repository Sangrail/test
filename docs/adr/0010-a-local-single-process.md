# 10. A local single process that reads the repository in place

The scope is an MVP, not the platform ([S1](../constraints/scope.md#s1), [S2](../constraints/scope.md#s2)), so the service runs as one local process, bound to 127.0.0.1, that reads the repository where it is ([C2](../constraints/constraints.md#c2)) and keeps its index and audit log in a local state folder. The MCP server can share the same index file; a lock lets one process at a time publish changes.

**Status:** accepted.

**Serves:** [S1](../constraints/scope.md#s1), [S2](../constraints/scope.md#s2), [C2](../constraints/constraints.md#c2), [C1](../constraints/constraints.md#c1).

**Considered options:** a distributed deployment with a shared index service (the platform, [S2](../constraints/scope.md#s2)); copy the repository into the service (against [C2](../constraints/constraints.md#c2)).

**Consequences:** no external services are needed to run it. Scale, identity and durable audit are gaps ([G1](../constraints/gaps.md#g1), [G2](../constraints/gaps.md#g2), [G5](../constraints/gaps.md#g5)), recorded rather than built.

**Implemented by:** [`runtime.py`](../../engineering_search/runtime.py), [`__main__.py`](../../engineering_search/__main__.py), `FileLock` in [`adapters.py`](../../engineering_search/adapters.py). **Tested by:** [`tests/test_startup.py`](../../tests/test_startup.py), [`tests/test_mcp_stdio.py`](../../tests/test_mcp_stdio.py), [`tests/test_binding.py`](../../tests/test_binding.py) (a refresh waits for another process's lock).
