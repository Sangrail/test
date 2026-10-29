"""Score search quality against evaluation/questions.json.

The script builds the index over test-repository/, asks each question as the
named user through POST /search, and checks the returned passages.

A passage is relevant when it comes from an expected file and contains the
expected text (case is ignored). An expected file can be a pattern such as
"generated-projects/*". Metrics (top 10 results):
  Success@1   the first result is relevant
  Success@5   a relevant result is in the first five
  MRR@10      mean of 1 / rank of the first relevant result (0 if none)
  Recall@10   share of expected (file, text) pairs found
  Answer      the answer (one sentence or table row) comes from an expected
              file and contains the expected text
  Zero        share of questions that returned no results
  Leaks       results or answers from a file the user must not see (must be 0)

    uv run python -m scripts.evaluate
    uv run python -m scripts.evaluate --save evaluation/results/baseline.json
"""
import argparse
from fnmatch import fnmatch
import json
from pathlib import Path
from statistics import median
import tempfile
from time import perf_counter

from fastapi.testclient import TestClient

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app

ROOT = Path(__file__).resolve().parents[1]
K = 10


def relevant(passage: dict, expected: list[dict]) -> set[int]:
    """Return the indexes of the expected items this passage satisfies."""
    text = " ".join(passage["text"].split()).casefold()
    return {i for i, item in enumerate(expected)
            if fnmatch(passage["file_id"], item["file"]) and item["contains"].casefold() in text}


def score(question: dict, results: list[dict]) -> dict:
    expected = question["expected"]
    forbidden = set(question.get("forbidden", []))
    first, found = None, set()
    for rank, passage in enumerate(results[:K], start=1):
        hits = relevant(passage, expected)
        if hits and first is None:
            first = rank
        found |= hits
    return {"id": question["id"], "user": question["user"], "question": question["question"],
            "scored": bool(expected), "results": len(results), "first_relevant_rank": first,
            "recall": len(found) / len(expected) if expected else None,
            "leaks": sorted({p["file_id"] for p in results} & forbidden),
            "top": [f'{p["file_id"]}:{p["start_line"]}' for p in results[:3]]}


def run(documents: Path, questions: list[dict]) -> list[dict]:
    with tempfile.TemporaryDirectory() as state:
        state = Path(state)
        app = create_app(root=documents, audit=SQLiteAuditStore(state / "audit.sqlite3"))
        with TestClient(app) as client:
            client.post("/auth/login", json={"user_id": "maya"}).raise_for_status()
            client.post("/index").raise_for_status()
            rows = []
            for question in questions:
                client.post("/auth/login", json={"user_id": question["user"]}).raise_for_status()
                started = perf_counter()
                response = client.post("/search", json={"query": question["question"], "limit": K})
                elapsed = (perf_counter() - started) * 1000
                response.raise_for_status()
                body = response.json()
                row = score(question, body["evidence"])
                answer = body.get("answer", {})
                sources = ([answer] if "file_id" in answer else []) + answer.get("also_stated_in", []) \
                    + answer.get("documents", [])
                row["leaks"] = sorted(set(row["leaks"]) | ({s["file_id"] for s in sources}
                                                           & set(question.get("forbidden", []))))
                row["answer_correct"] = bool("file_id" in answer and relevant(answer, question["expected"]))
                row["answer"] = f'{answer["file_id"]}:{answer["start_line"]} {answer["text"][:80]}' \
                    if "file_id" in answer else answer.get("status")
                row["latency_ms"] = round(elapsed, 1)
                row["searched_for"] = body.get("searched_for")
                rows.append(row)
            return rows


def summary(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["scored"]]
    ranks = [r["first_relevant_rank"] for r in scored]
    latencies = sorted(r["latency_ms"] for r in rows)
    return {"questions": len(rows), "scored_questions": len(scored),
            "success_at_1": sum(r == 1 for r in ranks) / len(scored),
            "success_at_5": sum(r is not None and r <= 5 for r in ranks) / len(scored),
            "mrr_at_10": sum(1 / r for r in ranks if r) / len(scored),
            "recall_at_10": sum(r["recall"] for r in scored) / len(scored),
            "answer_correct": sum(r.get("answer_correct", False) for r in scored) / len(scored),
            "zero_result_rate": sum(r["results"] == 0 for r in rows) / len(rows),
            "permission_leaks": sum(len(r["leaks"]) for r in rows),
            "latency_p50_ms": round(median(latencies), 1),
            "latency_p95_ms": latencies[min(len(latencies) - 1, round(0.95 * (len(latencies) - 1)))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--documents", type=Path, default=ROOT / "test-repository")
    parser.add_argument("--questions", type=Path, default=ROOT / "evaluation" / "questions.json")
    parser.add_argument("--save", type=Path, help="Write the full results to this JSON file")
    args = parser.parse_args()
    rows = run(args.documents.resolve(), json.loads(args.questions.read_text())["questions"])
    totals = summary(rows)

    for r in rows:
        rank = "-" if not r["scored"] else (r["first_relevant_rank"] or "miss")
        recall = "" if r["recall"] is None else f'{r["recall"]:.0%}'
        leak = f'  LEAK {r["leaks"]}' if r["leaks"] else ""
        answered = "" if not r["scored"] else ("answer=ok  " if r.get("answer_correct") else "answer=NO  ")
        print(f'{r["id"]} {r["user"]:<5} rank={rank!s:<4} recall={recall:<4} n={r["results"]:<3} '
              f'{answered}{r["question"][:55]}{leak}')
    print()
    for name, value in totals.items():
        print(f"{name:<18} {value:.2f}" if isinstance(value, float) and value <= 1 else f"{name:<18} {value}")
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps({"summary": totals, "questions": rows}, indent=2) + "\n")
        print(f"\nSaved {args.save}")


if __name__ == "__main__":
    main()
