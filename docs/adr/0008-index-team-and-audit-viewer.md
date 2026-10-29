---
status: accepted
date: 2026-10-28
version: 1
---

# Keep search users and the index team separate

**Serves:** [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [U1](../constraints/use-case.md#u1) (selected managers and leads search).

## Context

The use case is for engineering managers and leads who search ([U1](../constraints/use-case.md#u1)). Index operations, uploads, telemetry, the access rules and the audit log are a different job, with sensitive information: the audit log names files that some users cannot read. Permission to search must not give access to these operations ([R1](../constraints/requirements.md#r1)).

## Decision

- JP and Kamal can search only.
- Maya represents the index team. Maya can open index operations, uploads, telemetry, the access rules, the API documentation and the audit log.
- The index-team role does not change file permissions. When Maya searches, Maya gets only the files that Maya can read ([ADR 0010](0010-path-based-access-rules.md)).
- The server checks the role on every page and API request. Hidden navigation is not the protection.
- The audit viewer shows pages of events, newest first. A snapshot ID keeps the pages stable while new events arrive. It is a page boundary, not permission to read.

## Consequences

- A search user cannot see the access rules, the audit log or other users' searches.
- The index team can see file names in permission decisions. That is accepted for this role.
- Sign-in is pretend, so anyone can select Maya. Real identity is required before a shared service ([TODO.md](../../TODO.md#before-use-as-a-shared-service)).

## Implementation

Done. The `backend_boundary` middleware in [`app.py`](../../engineering_search/app.py) protects `/admin`, `/index`, `/scan`, `/uploads`, `/audit`, `/telemetry`, `/health` and the API pages. A denied request is recorded in the audit log. Pages: `static/admin.html` and `static/audit.html`. The demo users are `USERS` in [`access.py`](../../engineering_search/access.py). Tests: `tests/test_access.py`, `tests/test_audit.py`.

The earlier version of this record described per-file grants for ten demonstration files. [ADR 0010](0010-path-based-access-rules.md) replaced those grants with folder and file rules.

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-28 | now | Recorded when the decision was made. | sangrail |
