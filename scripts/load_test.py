"""Send N simultaneous requests to the web app and check the time budget.

Every request must either be answered within the budget, or be refused at once
with 503 and Retry-After. The requests are a mix of the scored questions and the
S355 SQL query, for JP, Kamal and Maya, sent through the real ASGI app (with its
middleware and worker threads), in one event loop.

    uv run --frozen python -m scripts.load_test --requests 100 --requests 1000
    uv run --frozen python -m scripts.load_test --requests 1000 --budget 8
"""
import argparse
import asyncio
import json
from pathlib import Path
import statistics
import tempfile
from time import perf_counter

import httpx

from engineering_search.adapters import Admission, SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.jobs import SQLiteJobQueue

ROOT = Path(__file__).resolve().parents[1]
SQL = ("SELECT subject, file_id, table_no, row_no, line FROM components "
       "WHERE material_grade LIKE 'S355%' AND allowable_load_kn_m2 < 5")


def questions() -> list[str]:
    data = json.loads((ROOT / "evaluation/questions.json").read_text())
    return [q["question"] for q in (data["questions"] if isinstance(data, dict) else data)]


async def run(client_for, count: int, texts: list[str]) -> list[tuple[int, float]]:
    async def one(i):
        client = client_for[("jp", "kamal", "maya")[i % 3]]
        start = perf_counter()
        if i % 4 == 3:
            response = await client.post("/sql", json={"sql": SQL})
        else:
            response = await client.post("/search", json={"query": texts[i % len(texts)]})
        return response.status_code, perf_counter() - start
    return await asyncio.gather(*(one(i) for i in range(count)))


def report(count: int, results: list[tuple[int, float]], wall: float, budget: float) -> bool:
    served = sorted(t for status, t in results if status == 200)
    busy = sorted(t for status, t in results if status == 503)
    other = [status for status, _ in results if status not in (200, 503)]
    line = f"{count:5} at once: {len(served):4} answered"
    if served:
        line += f" (p50 {statistics.median(served):5.2f} s, max {served[-1]:5.2f} s)"
    line += f", {len(busy):4} refused as busy"
    if busy:
        line += f" (slowest refusal {busy[-1]:5.2f} s)"
    line += f", {len(other)} other errors, {len(served) / wall:4.1f} answers/s"
    ok = not other and (not served or served[-1] <= budget)
    print(line + ("" if ok else "   <-- OVER BUDGET OR ERRORS"))
    return ok


async def main(counts: list[int], budget: float) -> int:
    state = Path(tempfile.mkdtemp())
    app = create_app(root=ROOT / "test-repository", audit=SQLiteAuditStore(state / "audit.sqlite3"),
                     queue=SQLiteJobQueue(state / "queue.sqlite3"), worker_count=0,
                     admission=Admission(budget_seconds=budget))
    texts = questions()
    ok = True
    async with app.router.lifespan_context(app):
        clients = {}
        for user in ("jp", "kamal", "maya"):
            clients[user] = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                              timeout=600)
            await clients[user].post("/auth/login", json={"user_id": user})
        await clients["maya"].post("/index")
        print(f"Budget {budget} s. Each request is answered within it, or refused at once.")
        for count in counts:
            learnt = app.state.service.admission.snapshot()
            print(f"      learnt service time {learnt['service_seconds']:.3f} s, spread {learnt['spread_seconds']:.3f} s")
            start = perf_counter()
            results = await run(clients, count, texts)
            ok &= report(count, results, perf_counter() - start, budget)
        for client in clients.values():
            await client.aclose()
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--requests", type=int, action="append", help="Simultaneous requests (repeatable)")
    parser.add_argument("--budget", type=float, default=8.0, help="Seconds (default 8, as SEARCH_BUDGET_SECONDS)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.requests or [1, 10, 100, 1000], args.budget)))
