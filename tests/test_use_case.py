"""Acceptance tests for the use case in the brief.

An engineering lead must find a critical engineering parameter (a load limit,
a material specification or a compliance approval status) across 100+
project documents in under 10 seconds, with 100% confidence in the source,
without opening a design file or a PDF viewer.

These tests ask questions through the HTTP API, against test-repository/,
and check that:
  - the repository has more than 100 documents;
  - each answer states the expected value, from the expected file and page;
  - the answer text is in the source file at the cited lines, and the cited
    version is the SHA-256 of the file (checked here without the service code);
  - each request takes less than 10 seconds;
  - list questions return the right documents, and comparisons hold;
  - a question with no answer in the documents gets no answer;
  - a user never gets an answer from a file that they cannot read.
"""
import hashlib
import logging
from pathlib import Path
import re
from time import perf_counter

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.jobs import SQLiteJobQueue

REPOSITORY = Path(__file__).resolve().parents[1] / "test-repository"
NORTHGATE = "project-northgate/northgate-warehouse-structural-calculations.pdf"
RIVERSIDE = "project-riverside/riverside-footbridge-load-rating.pdf"
TIME_LIMIT_SECONDS = 10


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    app = create_app(root=REPOSITORY, audit=SQLiteAuditStore(state / "audit.sqlite3"),
                     queue=SQLiteJobQueue(state / "queue.sqlite3"), worker_count=0)
    with TestClient(app) as client:
        client.post("/auth/login", json={"user_id": "maya"})
        assert client.post("/index").json()["failed_files"] == []
        yield client


def ask(client, user, question, **options):
    client.post("/auth/login", json={"user_id": user})
    started = perf_counter()
    response = client.post("/search", json={"query": question, **options})
    elapsed = perf_counter() - started
    assert response.status_code == 200, response.text
    assert elapsed < TIME_LIMIT_SECONDS, f"{question!r} took {elapsed:.1f} s"
    return response.json()["answer"]


def flat(text):
    return " ".join(text.split())


def assert_from_source(source):
    """Check the cited text against the file itself, without the service's extraction code."""
    raw = (REPOSITORY / source["file_id"]).read_bytes()
    assert source["source_version"] == hashlib.sha256(raw).hexdigest()
    if source["page"]:
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        from io import BytesIO
        lines = PdfReader(BytesIO(raw)).pages[source["page"] - 1].extract_text().splitlines()
    else:
        lines = raw.decode("utf-8").splitlines()
    cited = flat(" ".join(lines[source["start_line"] - 1:source["end_line"]]))
    assert flat(source["text"]) in cited
    assert source["value"] and source["value"] in source["text"]


def test_repository_has_more_than_100_documents(client):
    status = client.get("/index/status").json()
    assert status["indexed_files"] > 100


@pytest.mark.parametrize("question,file_id,page,value", [
    # Load limits
    ("What is the roof load limit at Northgate?", NORTHGATE, 2, "0.6 kN/m²"),
    ("What is the pedestrian load limit on the Riverside footbridge?", RIVERSIDE, 2, "5.0 kN/m²"),
    ("What is the roof load limit for Project Cedar?", "project-cedar/03-roof-load.md", None, "5 kN/m²"),
    ("What is the roof load of synthetic project 042?", "generated-projects/project-042.md", None, "7 kN/m²"),
    # Material specifications
    ("What steel is used for the Northgate purlins?", NORTHGATE, 3, "S390GD"),
    ("What steel grade are the Riverside girders?", RIVERSIDE, 1, "S355J2+N"),
    # Compliance approval status
    ("Has building control approved the Northgate warehouse?", NORTHGATE, 4, "PENDING"),
    ("What is the approval status of the Riverside footbridge?", RIVERSIDE, 3, "APPROVED"),
    # The value and its status are in two sentences; the answer must hold both.
    ("Is the proposed 7 kN/m² roof load approved?", "specifications/roof-load-draft.md", None, "not approved"),
])
def test_one_value_is_answered_from_its_exact_source(client, question, file_id, page, value):
    answer = ask(client, "jp", question)
    assert answer["type"] == "answer" and answer["status"] == "found"
    assert (answer["file_id"], answer["page"]) == (file_id, page)
    assert value in answer["text"]
    assert_from_source(answer)
    for other in answer["also_stated_in"]:
        assert_from_source(other)


def test_no_answer_is_given_when_no_document_states_it(client):
    answer = ask(client, "jp", "What is the fire resistance rating of the Northgate mezzanine?")
    assert answer["status"] == "not_found" and "text" not in answer


def test_list_documents_in_a_project_then_narrow_the_list(client):
    northgate = ask(client, "jp", "Do we have any documents in Northgate?")
    assert northgate["type"] == "list"
    listed = [d["file_id"] for d in northgate["documents"]]
    assert NORTHGATE in listed
    for document in northgate["documents"]:
        assert (REPOSITORY / document["file_id"]).read_bytes()  # every entry is a real file
    follow_up = ask(client, "jp", "Of those documents, which mention compliance?", within=listed)
    assert [d["file_id"] for d in follow_up["documents"]] == [NORTHGATE]
    assert "PENDING" in follow_up["documents"][0]["text"]


def test_list_documents_that_specify_a_material(client):
    answer = ask(client, "jp", "Which documents specify S355?")
    listed = {d["file_id"] for d in answer["documents"]}
    assert {"project-cedar/04-beam-capacity.md", "project-cedar/06-material-certificate.md",
            "specifications/roof-load.md", RIVERSIDE, NORTHGATE,
            "registers/material-approval-register.pdf"} <= listed
    for document in answer["documents"]:
        assert "S355" in document["text"]
        assert_from_source(document)


def test_list_documents_with_a_compliance_approval_status(client):
    answer = ask(client, "jp", "Which documents have a compliance approval status?")
    assert {d["file_id"] for d in answer["documents"]} == {
        "specifications/bridge.md", "project-cedar/07-compliance-approval.md", NORTHGATE}
    for document in answer["documents"]:
        assert_from_source(document)


def kn_per_m2(text):
    number, unit = re.search(r"(\d+(?:\.\d+)?)\s?(N/m²|kN/m²|kPa)", text).groups()
    return float(number) / (1000 if unit == "N/m²" else 1)


def test_list_documents_by_load_limit_value(client):
    above = ask(client, "jp", "Which documents have a roof load greater than 5 kN/m²?")
    listed = {d["file_id"] for d in above["documents"]}
    assert "specifications/roof-load-draft.md" in listed  # 7 kN/m², and the line says it is a draft
    assert not {"project-cedar/03-roof-load.md", NORTHGATE} & listed  # 5 and 0.6 kN/m²
    assert above["count"] > 40
    for document in above["documents"]:
        assert kn_per_m2(document["value"]) > 5
        assert_from_source(document)
    equal = ask(client, "jp", "Which documents have a roof load of 5000 N/m²?")
    listed = {d["file_id"] for d in equal["documents"]}
    assert {"project-cedar/03-roof-load.md", "specifications/roof-load.md"} <= listed
    assert all(kn_per_m2(d["value"]) == 5 for d in equal["documents"])


def test_answers_never_come_from_files_the_user_cannot_read(client):
    answer = ask(client, "kamal", "Has building control approved the Northgate warehouse?")
    assert answer.get("file_id") != NORTHGATE
    # Kamal cannot read the Northgate file. A roof load from another project is not
    # an answer about Northgate, so it must not be given as one.
    roof = ask(client, "kamal", "What is the roof load limit at Northgate?")
    assert roof["status"] != "found" and roof.get("file_id") != NORTHGATE
    if roof["status"] == "partial":
        assert "northgate" in roof["missing_words"]
    assert all(o["file_id"] != NORTHGATE for o in answer.get("also_stated_in", []))
    statuses = ask(client, "kamal", "Which documents have a compliance approval status?")
    assert statuses["status"] == "not_found" and statuses["documents"] == []
