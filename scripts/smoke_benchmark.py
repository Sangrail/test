"""Reindex a local demo server and measure 100 sequential HTTP searches."""
import argparse
import json
from pathlib import Path
import statistics
from time import perf_counter

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()
with httpx.Client(base_url=args.url, timeout=10) as client:
    client.post("/auth/login", json={"user_id": "maya"}).raise_for_status()
    indexed = client.post("/index")
    indexed.raise_for_status()
    timings = []
    for i in range(100):
        query = "roof load" if i % 2 == 0 else f"DEMO{i:03}"
        start = perf_counter()
        response = client.post("/search", json={"query": query, "limit": 10})
        timings.append((perf_counter() - start) * 1000)
        response.raise_for_status()
        assert response.json()["evidence"], "Use the 120-file generated demo corpus"
    metrics = client.get("/telemetry").json()
    assert client.get("/docs").status_code == 200
    assert "SearchResponse" in client.get("/openapi.json").json()["components"]["schemas"]
result = {
    "workload": "120 tiny synthetic Markdown documents; one worker; 100 sequential HTTP searches",
    "index": indexed.json(), "telemetry": metrics,
    "client_query_ms": {"min": min(timings), "max": max(timings),
                        "median": statistics.median(timings), "average": statistics.mean(timings)},
}
Path(".runtime").mkdir(exist_ok=True)
Path(".runtime/smoke-benchmark.json").write_text(json.dumps(result, indent=2))
print(json.dumps({"files": result["index"]["files"],
                  "index_seconds": result["index"]["total_seconds"],
                  "server_query_ms": metrics["query_ms"],
                  "client_query_ms": result["client_query_ms"]}, indent=2))
