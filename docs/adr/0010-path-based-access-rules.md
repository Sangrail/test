---
status: accepted
date: 2026-10-28
version: 2
---

# Index the whole repository, and control access with folder and file rules

**Serves:** [R1](../constraints/requirements.md#r1) (no information from forbidden documents), [C2](../constraints/environment.md#c2) (files in an existing repository), [U2](../constraints/use-case.md#u2) (100+ documents), [R7](../constraints/requirements.md#r7) (project folders on a file system), [R8](../constraints/requirements.md#r8) (no view inside unauthorised folders). **Not met:** [P3](../constraints/production.md#p3) (permissions from the repository).

## Context

The first prototype gave per-file grants to ten demonstration files, and gave all other files to two users only. That made most of the repository look out of scope, and it did not match how the existing repository ([C2](../constraints/environment.md#c2)) controls access. File shares and document systems set permissions on folders, and files inherit them, as in Windows. The search must cover all 100+ documents ([U2](../constraints/use-case.md#u2)) and still never give a user information from a document that the user cannot read ([R1](../constraints/requirements.md#r1)).

## Decision

- Index every supported file. Permissions decide what a user sees, not what is indexed.
- A rule applies to the whole repository, to a folder or to one file. The most specific rule wins and replaces the inherited one.
- Rules list users directly. There are no groups and no "deny" entries.
- Check the rules on each request, before answers, counts and pages ([ADR 0006](0006-permissions-before-results.md)).

The full list of assumptions is at the top of [`access.py`](../../engineering_search/access.py).

## Consequences

- The rules are simpler than Windows (NTFS) permissions, which merge inherited and explicit entries and have "deny" entries. A production service must get the effective permissions from the repository through its connector, not copy them into a Python file ([P3](../constraints/production.md#p3)).
- The rules are small and easy to read for a demonstration. The sign-in screen and the README show which folders each user can read.

## Implementation

Done. `ACCESS_RULES`, `governing_rule` and `MockPermissionStore` in [`access.py`](../../engineering_search/access.py). JP reads 138 of 138 files, Kamal 130 and Maya 133. Tests: `tests/test_access.py`, `tests/test_pagination.py`, `tests/test_no_leaks.py` (which also checks each user's file list against a list written by hand).

## History

| Version | Active from | Until | Change | By |
| --- | --- | --- | --- | --- |
| 2 | 2026-10-29 | now | Link [R7](../constraints/requirements.md#r7) (project folders) and [R8](../constraints/requirements.md#r8) (folder authorisation), which this decision serves. | sangrail (via Claude Code) |
| 1 | 2026-10-28 | 2026-10-29 (Displaced by version 2) | Recorded when the decision was made. | sangrail |
