"""Phase A regressions: an answer must be about what the question asks, permissions
apply before the candidate limit, long lists page, and two processes that share one
index cannot publish at the same time.

Each test builds a small document folder, so the expected result is visible here."""
from pathlib import Path
import threading
import time

import pytest

from engineering_search.access import USERS, MockPermissionStore
from engineering_search.adapters import FileLock, SQLiteAuditStore
from engineering_search.answer import MAX_LISTED, understand
from engineering_search.jobs import SQLiteJobQueue
from engineering_search.service import SearchService
from engineering_search.store import CANDIDATE_LIMIT, SQLiteSearchIndex

JP, KAMAL = (next(u for u in USERS if u["id"] == name) for name in ("jp", "kamal"))


def service(tmp_path: Path, files: dict[str, str], rules=None, index=None, index_lock=None) -> SearchService:
    root = tmp_path / "documents"
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    built = SearchService(root, index or SQLiteSearchIndex(), SQLiteAuditStore(tmp_path / "audit.sqlite3"),
                          MockPermissionStore(rules), SQLiteJobQueue(tmp_path / "queue.sqlite3"),
                          index_lock=index_lock)
    built.reindex()
    return built


FLOOR_ONLY = """# Warehouse design basis

## Roof

The roof is a steel portal frame with profiled cladding.

## Floor loading

The design load is 7.5 kN/m² for the ground slab.
"""


def test_a_floor_load_is_not_the_roof_load_answer(tmp_path):
    search = service(tmp_path, {"warehouse.md": FLOOR_ONLY})
    answer = search.search(JP, "What is the roof design load?", mode="answer")["answer"]
    assert answer["text"] == "The design load is 7.5 kN/m² for the ground slab."
    assert answer["status"] == "unverified"
    assert answer["unbound_words"] == ["roof"]


def test_a_value_whose_heading_names_the_subject_is_found(tmp_path):
    search = service(tmp_path, {"warehouse.md": FLOOR_ONLY.replace("## Floor loading", "## Roof loading")})
    answer = search.search(JP, "What is the roof design load?", mode="answer")["answer"]
    assert answer["status"] == "found" and "unbound_words" not in answer


def test_a_floor_load_does_not_qualify_a_document_for_a_roof_load_filter(tmp_path):
    roof = "# Store\n\n## Roof loading\n\nThe roof load is 6 kN/m².\n"
    search = service(tmp_path, {"warehouse.md": FLOOR_ONLY, "store.md": roof})
    listed = search.search(JP, "Which documents have a roof load greater than 5 kN/m²?")["answer"]
    assert [d["file_id"] for d in listed["documents"]] == ["store.md"]


def test_signed_values_compare_with_their_sign():
    below = understand("Which documents have a settlement less than -10 mm?").comparison
    assert (below.operator, below.number, below.unit) == ("<", -10.0, "mm")
    assert below.accepts("Predicted settlement is −12 mm at the corner.")
    assert not below.accepts("Predicted settlement is 12 mm at the corner.")
    # A hyphen inside a code is not a minus sign.
    assert not below.accepts("Grid line A-12 mm offset")


def test_forbidden_passages_cannot_push_a_permitted_passage_past_the_candidate_limit(tmp_path):
    forbidden = "\n\n".join(f"## Note {n}\n\nUniqueprobe ranked first {n}." for n in range(CANDIDATE_LIMIT + 50))
    rules = {"": {"jp", "kamal", "maya"}, "secret/": {"jp"}}
    search = service(tmp_path, {"secret/notes.md": "# Notes\n\n" + forbidden,
                                "public.md": "# Public\n\nA long sentence that mentions uniqueprobe once."},
                     rules=rules)
    assert len(search.index.candidates("uniqueprobe")) == CANDIDATE_LIMIT  # The limit is reached unscoped.
    result = search.search(KAMAL, "uniqueprobe")
    assert [p["file_id"] for p in result["evidence"]] == ["public.md"]
    assert result["matched_passages"] == 1


def test_a_long_list_continues_on_the_next_page(tmp_path):
    count = MAX_LISTED + 3
    files = {f"beams/beam-{n:03}.md": f"# Beam {n}\n\nSteel grade S355 for beam {n}.\n" for n in range(count)}
    search = service(tmp_path, files)
    first = search.search(JP, "Which documents use steel grade S355?", page=1)["answer"]
    second = search.search(JP, "Which documents use steel grade S355?", page=2)["answer"]
    assert first["count"] == second["count"] == count
    assert len(first["documents"]) == MAX_LISTED and first["truncated"]
    assert len(second["documents"]) == 3 and not second["truncated"]
    listed = {d["file_id"] for d in first["documents"] + second["documents"]}
    assert listed == set(files)


def test_a_refresh_waits_while_another_process_holds_the_index_lock(tmp_path):
    lock_path = tmp_path / "index.lock"
    search = service(tmp_path, {"a.md": "# A\n\nAlpha.\n"}, index_lock=FileLock(lock_path))
    (search.root / "b.md").write_text("# B\n\nBravo.\n")
    other_process = FileLock(lock_path)  # Its own file descriptor, as another process would have.
    finished = threading.Event()
    with other_process:
        worker = threading.Thread(target=lambda: (search.reindex(), finished.set()))
        worker.start()
        time.sleep(0.3)
        assert not finished.is_set(), "the refresh published while another process held the lock"
    worker.join(timeout=10)
    assert finished.is_set() and set(search.index.versions()) == {"a.md", "b.md"}
