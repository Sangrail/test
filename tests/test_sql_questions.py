"""The gold set for natural-language-to-SQL evaluation is itself correct.

evaluation/sql_questions.json holds plain-language questions with expected
rows written by hand from the fixtures. This test runs each question's
reference SQL as its user and compares the result with the hand-written rows.
It fails if the extraction changes (a fact rule, a reader, a permission) so
that the gold answers are no longer true, before a client is scored on them."""
import json
from pathlib import Path

import pytest

from engineering_search.access import USERS
from engineering_search.runtime import build_service
from helpers import TEST_REPOSITORY

GOLD = json.loads((Path(__file__).resolve().parents[1] / "evaluation/sql_questions.json").read_text())["questions"]


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    service = build_service(TEST_REPOSITORY, tmp_path_factory.mktemp("state"))
    service.reindex()
    return service


@pytest.mark.parametrize("question", GOLD, ids=[q["id"] for q in GOLD])
def test_the_reference_sql_gives_the_hand_written_answer(service, question):
    user = next(u for u in USERS if u["id"] == question["user"])
    result = service.query_sql(user, question["gold_sql"], 500)
    expected = question["expected"]
    if "value" in expected:
        assert result["rows"] == [[expected["value"]]]
    else:
        assert sorted(map(tuple, (row[:2] for row in result["rows"]))) == sorted(map(tuple, expected["rows"]))


def test_the_gold_set_covers_each_trap_and_both_users():
    traps = " ".join(q["trap"] for q in GOLD)
    for kind in ("grade", "permissions", "project", "capacity and demand", "units", "schema", "sign"):
        assert kind in traps, kind
    assert {q["user"] for q in GOLD} == {"jp", "kamal"}
    assert any(q["expected"].get("rows") == [] for q in GOLD)  # "No rows" is a right answer somewhere.
