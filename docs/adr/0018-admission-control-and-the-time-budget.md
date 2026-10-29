---
status: accepted (MVP; the scaling work is open)
date: 2026-10-29
---
# Answer within the time budget or refuse at once, and record what does not scale

**Serves:** [U3](../constraints/use-case.md#u3) (under 10 seconds), [U4](../constraints/use-case.md#u4) (trust), [C5](../constraints/environment.md#c5) (a chat-agent shell calls the service), [S1](../constraints/scope.md#s1) (MVP only). **Not met:** [P1](../constraints/production.md#p1) (any number of users, each answered within 10 seconds).

## Context

The use case asks for an answer in under 10 seconds ([U3](../constraints/use-case.md#u3)). The MVP was measured with one user at a time. With many users, it fails:

- **One process serves one request at a time.** `SearchService.lock` is held from the file match to the audit write, and the index has one SQLite connection. Throughput is about 10 requests a second on the 148 test files, whatever the load.
- **The constrained SQL path copies data for each request.** [ADR 0016](0016-structured-facts-and-client-written-sql.md) builds an in-memory projection of every permitted fact, then runs the statement. That costs about 2 µs a fact to build and 1 µs a fact to query the `components` view: 0.6 s at 200,000 facts, 3 s at 1,000,000. The build is under the service lock.
- **The SQL step budget does not grow with the data.** At 200,000 facts, the 2,000,000-step budget stops even the standard S355 query, because `components` is a view that groups every fact.

Measured on 29 October 2026 (`scripts/load_test.py` on a macOS laptop, one process, mixed text questions and the S355 SQL query, JP, Kamal and Maya):

| Requests at once | Before: slowest answer | Before: median |
| --- | --- | --- |
| 1 | 0.12 s | 0.12 s |
| 100 | 10.3 s | 5.6 s |
| 1,000 | 102 s | 51 s |

A user who waits 100 s and then gets an answer, or a timeout, loses trust. A user who is told at once "busy, try again in 5 s" can act.

Note that over local stdio ([ADR 0012](0012-mcp-server-for-the-chat-agent.md)) each chat client starts its own server process, so MCP users do not queue behind each other in one process; they share the machine and the SQLite files. The queue matters for the web service and for any shared remote server.

## Decision

- **Admission control.** Before a search, read or SQL query runs, predict its time and refuse it at once if it cannot finish within the budget. With n = requests in flight + 1, the prediction is n × mean + 2 × √n × spread, from moving averages of the measured service time (smoothing 0.05; first guess 0.2 s, deliberately cautious). A request's own service time runs from the later of its arrival and the previous departure, so waiting is not counted as work.
- **The budget is 8 s** (`SEARCH_BUDGET_SECONDS`), leaving 2 s of the 10 s target for the network, the chat client and the language model.
- **Admit where the request arrives.** The HTTP middleware admits before the route waits for a worker thread, so time in the thread queue counts. Each MCP tool admits before it calls the service. Index operations and uploads are not admission-controlled.
- **Tell the caller.** HTTP: 503 with a `Retry-After` header and `{"busy": true, "retry_after_seconds": n, "message": ...}`, and no evidence. MCP: the same object as the tool error; the server instructions tell the agent to report it and not to retry in a loop. The web page shows the message. `/index/status` shows the learnt service time, spread, requests in flight, refusals and capacity to the index team.
- **Do not hide the limit.** Document the throughput, the SQL cost and the step-budget limit here, in [ARCHITECTURE.md](../../ARCHITECTURE.md) and in [TODO.md](../../TODO.md), until the scaling work below is done.

## Consequences

Measured after the change, budget 8 s:

| Requests at once | Answered | Slowest answer | Refused as busy | Slowest refusal |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0.12 s | 0 | — |
| 10 | 10 | 0.73 s | 0 | — |
| 100 | about 50 | 5.7 s | about 50 | 0.02 s |
| 1,000 | about 47 | 5.5 s | about 953 | 0.24 s |

- Every answered request finished within the budget, and every refusal came back in under 0.25 s, with a retry time.
- **The guarantee is bounded latency, not capacity.** Throughput is unchanged at about 10 a second per process. With 1,000 simultaneous requests, most users are told to retry.
- The prediction is conservative: it admits about 50 per burst where about 75 would fit. That trades capacity for the guarantee. The 2 × √n × spread margin and the smoothing are tunable after measurement on real load.
- A burst of slow requests (large SQL projections) raises the estimate, and the service refuses more until it falls again.
- Admission is per process. Several processes behind a load balancer each admit on their own queue.

### What must change to serve the company

In order of value; each is a milestone in [TODO.md](../../TODO.md):

1. **Concurrent reads in one process.** One read connection per thread, each request in one read transaction (a WAL snapshot), and no global lock for searches. The index lock stays for writers. Python's GIL still limits the answer rules, so:
2. **Several worker processes** (or machines) reading the same index, behind a load balancer. Sessions and the upload queue move out of process memory. Rough sizing at the test-data cost of 0.1 s a request: 1,000 users asking one question a minute is about 17 requests a second, so 3 to 4 workers at 60% load. The real repository must be measured.
3. **SQL without a copy per request.** Cache projections by (permission-set fingerprint, index version), or enforce permissions inside a server database (row-level security, or views over a permitted-file table) so nothing is copied. Make `components` an indexed table, not a grouping view, and scale the step budget with the data.
4. **A server search engine** (or a server database with full-text search) when one SQLite file is no longer enough.
5. **Load tests in CI** at the expected size and concurrency, with the 10 s target as a gate.

## Implementation

Done for admission control. `Admission` and `Busy` in [`adapters.py`](../../engineering_search/adapters.py); `SearchService.admit()` in [`service.py`](../../engineering_search/service.py); `AdmissionMiddleware` in [`app.py`](../../engineering_search/app.py); `service.admit()` around each MCP tool in [`mcp_server.py`](../../engineering_search/mcp_server.py); `SEARCH_BUDGET_SECONDS` in [`runtime.py`](../../engineering_search/runtime.py). Tests: [`tests/test_admission.py`](../../tests/test_admission.py) (the prediction, worked by hand on a fake clock; 503 with Retry-After and no evidence). Load test: `uv run --frozen python -m scripts.load_test`. The scaling work above is not started.
