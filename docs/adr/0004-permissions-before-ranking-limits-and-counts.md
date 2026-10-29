# 4. Apply permissions before ranking, limits and counts; folder rules stand in for the repository's controls

A user gets no information from a document they may not read ([K13](../constraints/clarifications.md#k13)), so permissions decide the visible files before the index ranks, limits, counts, joins or aggregates anything, on the text path and the SQL path. The MVP's rules are paths (the whole repository, a project folder or a file) with their readers; they stand in for the repository's own access controls ([G1](../constraints/gaps.md#g1)).

**Status:** accepted.

**Serves:** [U1](../constraints/use-case.md#u1), [K5](../constraints/clarifications.md#k5), [K13](../constraints/clarifications.md#k13), [K15](../constraints/clarifications.md#k15). Leaves [G1](../constraints/gaps.md#g1) open.

**Considered options:** filter results after ranking (a forbidden file can push permitted passages out of the top results, and counts leak); one index per user (does not scale and duplicates the documents).

**Consequences:** the text path ranks with statistics (how common a word is, how long passages are) from the permitted passages that match the question, not from the whole index, so a forbidden file cannot change the order of a user's results; this costs time in proportion to the permitted matches. The SQL path runs each statement against a projection built from the permitted files only. The leak tests attack this from many sides; they cannot show that the rules match the real repository.

**Implemented by:** [`access.py`](../../engineering_search/access.py), [`service.py`](../../engineering_search/service.py), `SQLiteSearchIndex.candidates` in [`store.py`](../../engineering_search/store.py), [`sql.py`](../../engineering_search/sql.py). **Tested by:** [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py), [`tests/test_access.py`](../../tests/test_access.py), [`tests/test_sql.py`](../../tests/test_sql.py).
