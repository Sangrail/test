# 7. The source is the file on disc; a content fingerprint detects change

The files live in an existing repository with no versioning system ([C2](../constraints/constraints.md#c2), [K3](../constraints/clarifications.md#k3)), so a source is the file as it is now. The indexer takes a SHA-256 of each file's bytes, re-reads only new and changed files, removes deleted ones, and runs on start and on request; the same fingerprint lets the service refuse a quote from a file that changed after indexing.

**Status:** accepted.

**Serves:** [C2](../constraints/constraints.md#c2), [U5](../constraints/use-case.md#u5), [K3](../constraints/clarifications.md#k3), [K12](../constraints/clarifications.md#k12), [K16](../constraints/clarifications.md#k16).

**Considered options:** track revisions and approval state (the repository has none; it would invent a document-management system); re-read every file on each refresh (slow, and no faster to notice a change); a timer or a file watcher (more to run; a changed file is already refused, [G5](../constraints/gaps.md#g5)).

**Consequences:** the system never claims a file is "current" or "approved"; it states what the file says. Between refreshes, an edited file's evidence is refused rather than quoted stale. There is no upload path.

**Implemented by:** [`indexer.py`](../../engineering_search/indexing/indexer.py) (`plan`), `SearchService.reindex` and `changed_on_disc` in [`service.py`](../../engineering_search/service.py). **Tested by:** [`tests/test_indexer.py`](../../tests/test_indexer.py), [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py), [`tests/test_startup.py`](../../tests/test_startup.py).
