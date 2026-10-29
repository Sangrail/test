# 8. Hold 10 seconds end to end with a time budget and admission control

The use case asks for an answer in under 10 seconds, end to end, for 95% of queries ([U4](../constraints/use-case.md#u4), [K6](../constraints/clarifications.md#k6)). The service gives each search, read and SQL query a budget of 8 seconds (2 s left for the network and the shell) and refuses at once, with a retry time, a request that cannot be answered within it; every stage is timed.

**Status:** accepted.

**Serves:** [U4](../constraints/use-case.md#u4), [K6](../constraints/clarifications.md#k6). Leaves [G5](../constraints/gaps.md#g5) open.

**Considered options:** queue every request (answers arrive late, which fails the use case without saying so); time out after starting the work (wastes the work and still fails late).

**Consequences:** under load some users are told to retry rather than kept waiting. One process holds the target on the test data; many users need more ([G5](../constraints/gaps.md#g5)). Slow queries are not stored for analysis ([O2](../constraints/gaps.md#o2)).

**Implemented by:** `Admission` and `Telemetry` in [`adapters.py`](../../engineering_search/adapters.py), `Admitted` in [`service.py`](../../engineering_search/service.py) (times every search, SQL query and evidence read, over HTTP and MCP), `AdmissionMiddleware` in [`app.py`](../../engineering_search/app.py). **Tested by:** [`tests/test_admission.py`](../../tests/test_admission.py), [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_search.py`](../../tests/test_search.py) (telemetry); measured by [`scripts/load_test.py`](../../scripts/load_test.py).
