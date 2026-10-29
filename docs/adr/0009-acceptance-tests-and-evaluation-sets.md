# 9. Enforce the use case with acceptance tests and evaluation sets

The MVP is done when the use case holds ([T5](../constraints/task.md#t5)), so acceptance tests ask the use-case questions through the HTTP API over a test repository of 100+ documents across several projects, and check every answer against the files themselves: the right value, from the right file and line, for the right user, in under 10 seconds. Evaluation sets score retrieval and agent-written SQL.

**Status:** accepted.

**Serves:** [T5](../constraints/task.md#t5), [U2](../constraints/use-case.md#u2), [U3](../constraints/use-case.md#u3), [U4](../constraints/use-case.md#u4), [U5](../constraints/use-case.md#u5), [U6](../constraints/use-case.md#u6), [K10](../constraints/clarifications.md#k10), [K13](../constraints/clarifications.md#k13). On the way to [G4](../constraints/gaps.md#g4).

**Considered options:** unit tests only (each part works, the use case may not); a manual demo (not repeatable).

**Consequences:** the tests read the source files without the service's code, so a wrong citation fails. The test documents are synthetic or public and written by the same team, so the scores do not predict real performance ([G4](../constraints/gaps.md#g4)).

**Implemented by:** [`test-repository/`](../../test-repository/TEST-DATA.txt), [`evaluation/`](../../evaluation/README.md), [`scripts/evaluate.py`](../../scripts/evaluate.py). **Tested by:** [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_no_leaks.py`](../../tests/test_no_leaks.py), [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py).
