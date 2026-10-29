---
status: accepted
date: 2026-10-28
---
# Run independent instances with local data

**Serves:** [S1](../constraints/scope.md#s1) (MVP only), [S3](../constraints/scope.md#s3) (published repository), [C2](../constraints/environment.md#c2) (files in an existing repository). **Not met:** [P1](../constraints/production.md#p1) (any number of users, each answered within 10 seconds).

## Context

The MVP must be easy for other people to download, run and test ([S1](../constraints/scope.md#s1)). The repository will be published ([S3](../constraints/scope.md#s3)), so it must not need a central account, a hosted service or private data. In production the files stay in the existing repository ([C2](../constraints/environment.md#c2)). For the MVP, a local folder stands in for it.

## Decision

- Each person runs an independent copy of the service on a computer that they control: indexing, search, telemetry and audit.
- The document folder and the writable state folder are separate from the code. Both can be set at start.
- Remote use is a copy on a remote machine, reached through an SSH tunnel to a loopback port.
- The source package contains the code and the synthetic and public test documents only. It never contains private documents, uploads or audit databases.

## Consequences

- No account, API key or cloud database is needed. The install needs network access, and search does not.
- Pretend sign-in is acceptable only for trusted testers. Anyone who can reach the service can select any user ([ADR 0008](0008-index-team-and-audit-viewer.md)).
- The documents are on the tester's computer, so the access rules are a demonstration, not a protection ([ADR 0012](0012-mcp-server-for-the-chat-agent.md)).
- One local instance is not a service for an organisation. Serving any number of users, each within 10 seconds, with no single point of failure ([P1](../constraints/production.md#p1)), is separate engineering work ([ADR 0018](0018-admission-control-and-the-time-budget.md), [docs/README.md](../README.md#making-it-available-to-an-organisation)).
- A future reader must declare its dependencies, platforms and licence. A vendor reader on the developer's computer does not mean that a tester can install it.

## Implementation

Done. `python -m engineering_search` starts the web service. [`runtime.py`](../../engineering_search/runtime.py) puts the index, queue and audit files in the state folder (default `.runtime/`). The index persists between runs ([ADR 0004](0004-persistent-evidence.md)). Telemetry resets on restart. `scripts/package_source.py` makes the source ZIP. See [RUNNING.md](../../RUNNING.md).
