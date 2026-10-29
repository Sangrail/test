---
status: accepted
date: 2026-10-28
version: 1
---
<!-- Generated from docs/records/design.sqlite. Do not edit: change the database, then run `uv run --frozen python -m design_records generate` (the pre-commit hook runs it). -->

# Measure from the start, and audit before evidence is released

**Serves:** [U3](../constraints/use-case.md#u3) (under 10 seconds), [U4](../constraints/use-case.md#u4) (100% confidence in the source), [R1](../constraints/requirements.md#r1) (no information from forbidden documents). **Not met:** [P4](../constraints/production.md#p4) (durable, protected audit).

## Context

The use case sets a time limit ([U3](../constraints/use-case.md#u3)), so the time of each stage must be measured from the first version. It also asks for 100% confidence in the source ([U4](../constraints/use-case.md#u4)) and strict permissions ([R1](../constraints/requirements.md#r1)). The company must be able to show, after the event, which evidence each user got and which matches were withheld. Telemetry (performance) and audit (security) have different purposes and must stay separate.

## Decision

- Measure indexing throughput, query times (median, p95 and others), failures and the time of each search stage: lookup, permissions and audit.
- Before the service returns evidence, write an audit event: the user, the permission version, the decision for each matched file, the source of the answer and of each returned passage. If the write fails, return no evidence.
- Do not record the question text, the passage text or credentials. Record the number of characters in the question only.
- Take the user from the session, never from the question.
- A later event records that the response was sent. It cannot prove that a person read it.

## Consequences

- The audit log shows that permitted evidence reached the user and that excluded matches did not.
- The audit log is a local SQLite file, with no protection against changes and no retention rules. A production audit must be durable and protected ([P4](../constraints/production.md#p4)).
- File names in the audit log are sensitive. Only the index team can read the log ([ADR 0008](0008-index-team-and-audit-viewer.md)).
- Fast searches alone do not prove a useful or complete index. Coverage ([ADR 0005](0005-coverage-and-reader-gaps.md)) and quality ([ADR 0015](0015-acceptance-tests-enforce-the-use-case.md)) are separate measures.

## Implementation

Done. `SearchService.commit_audit` in [`service.py`](../../engineering_search/service.py) writes to `audit.sqlite3` ([`adapters.py`](../../engineering_search/adapters.py)) and raises `ServiceError(503)` on failure. `Telemetry` keeps the last 10,000 queries and 100 index runs in memory, so it resets on restart. The audit log is durable but not protected against changes, and has no retention rules. Tests: `tests/test_audit.py`.

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-28 | now | Recorded when the decision was made. | sangrail |
