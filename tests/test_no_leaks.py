"""A user must never get information from a file that they cannot read.

This is a hard requirement. These tests attack it from many sides, for each
user, through the HTTP API and the SearchService that the MCP server calls:
  - every question in the evaluation set, in each mode (auto, answer, list);
  - questions made from the text of each forbidden file, so that the
    forbidden file is the best match;
  - follow-up questions whose "within" list names forbidden files;
  - all result pages;
  - reading a forbidden file directly.

Each response is checked in two ways:
  - positive: each file named in the response is one the user can read, and
    each quoted text is in that file (read here without the service code);
  - negative: no forbidden file name, and no line of text that only a
    forbidden file contains, appears anywhere in the response.
"""
from io import BytesIO
import json
import logging
from pathlib import Path
import re

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pypdf import PdfReader
import pytest

from engineering_search.access import USERS
from engineering_search.adapters import SQLiteAuditStore
from engineering_search.app import create_app
from engineering_search.service import ServiceError

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT / "test-repository"
NORTHGATE = "project-northgate/northgate-warehouse-structural-calculations.pdf"
ROOF_SCHEDULE = "project-harbour/harbour-roof-schedule.xlsx"

# Written out by hand from the access rules, so that a wrong rule fails the test.
CANNOT_READ = {
    "jp": set(),
    "kamal": {"specifications/bridge.md", "specifications/roof-load.md", "specifications/roof-load-draft.md",
              NORTHGATE, "project-cedar/06-material-certificate.md", "project-cedar/07-compliance-approval.md",
              "project-cedar/08-environmental-review.md", "project-cedar/10-restricted-incident.md",
              ROOF_SCHEDULE},
    "maya": {"project-cedar/03-roof-load.md", "project-cedar/04-beam-capacity.md", "project-cedar/05-foundation.md",
             "project-cedar/09-bridge-load.md", "project-cedar/10-restricted-incident.md"},
}
MODES = ("auto", "answer", "list")


def flat(text: str) -> str:
    return " ".join(re.sub(r"[|#*`]", " ", text).lower().split())


def file_text(file_id: str) -> str:
    raw = (REPOSITORY / file_id).read_bytes()
    if file_id.endswith(".xlsx"):
        book = load_workbook(BytesIO(raw), data_only=True)
        return "\n".join(" | ".join("" if c is None else str(c) for c in row)
                         for sheet in book.worksheets for row in sheet.iter_rows(values_only=True))
    if file_id.endswith(".pdf"):
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        return "\n".join(page.extract_text() for page in PdfReader(BytesIO(raw)).pages)
    return raw.decode("utf-8")


# Every file that has a reader, so every file that can be in a response.
ALL_FILES = sorted(str(p.relative_to(REPOSITORY)) for p in REPOSITORY.rglob("*")
                   if p.suffix in (".md", ".pdf", ".csv", ".xlsx", ".dxf"))
TEXT = {file_id: file_text(file_id) for file_id in ALL_FILES}
FLAT = {file_id: flat(text) for file_id, text in TEXT.items()}


def secret_lines(user: str) -> list[str]:
    """Lines that only forbidden files contain: these must never reach the user."""
    readable = " \n ".join(FLAT[f] for f in ALL_FILES if f not in CANNOT_READ[user])
    lines = {flat(line) for f in CANNOT_READ[user] for line in TEXT[f].splitlines()}
    return sorted(line for line in lines if len(line) >= 20 and line not in readable)


def attack_questions(user: str) -> list[str]:
    """Questions made from the forbidden files, so that a forbidden file is the best match."""
    questions = []
    for file_id in sorted(CANNOT_READ[user]):
        questions.append(" ".join(re.findall(r"[a-z]+", Path(file_id).stem)))
        lines = [line for line in TEXT[file_id].splitlines() if len(re.findall(r"[A-Za-z]{2,}", line)) >= 4]
        questions += [" ".join(line.split()[:8]) for line in lines[:5]]
    return questions


EVALUATION = [q["question"] for q in json.loads((ROOT / "evaluation/questions.json").read_text())["questions"]]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    app = create_app(root=REPOSITORY, audit=SQLiteAuditStore(state / "audit.sqlite3"))
    with TestClient(app) as client:
        client.post("/auth/login", json={"user_id": "maya"})
        assert client.post("/index").json()["failed_files"] == []
        yield client


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def sources(value):
    """Every object in the response that names a file."""
    if isinstance(value, dict):
        if "file_id" in value:
            yield value
        for item in value.values():
            yield from sources(item)
    elif isinstance(value, list):
        for item in value:
            yield from sources(item)


def assert_no_leak(user: str, response: dict, secrets: list[str], question: str = ""):
    readable = set(ALL_FILES) - CANNOT_READ[user]
    for source in sources(response):
        assert source["file_id"] in readable, f"{user} got {source['file_id']}"
        if source.get("text"):
            # A DXF attribute is quoted as "TAG | value": the tag and the value are on separate lines of the file.
            parts = source["text"].split(" | ") if source["file_id"].endswith(".dxf") else [source["text"]]
            assert all(flat(part) in FLAT[source["file_id"]] for part in parts), f"text not from {source['file_id']}"
    everything = flat(" \n ".join(strings(response)))
    for file_id in CANNOT_READ[user]:
        assert file_id.lower() not in everything, f"{user} saw the name {file_id}"
    # The response repeats the question ("searched for"). Text the user typed is not a leak.
    for line in (s for s in secrets if s not in flat(question)):
        assert line not in everything, f"{user} saw forbidden text: {line!r}"


def search_all_pages(client, body: dict) -> list[dict]:
    """The first five pages and the last page. Every page costs a full search, so
    the middle pages of long results are skipped to keep the suite fast."""
    def fetch(page):
        response = client.post("/search", json={**body, "limit": 50, "page": page})
        assert response.status_code == 200, response.text
        return response.json()
    pages = [fetch(1)]
    total = pages[0]["total_pages"] or 1
    pages += [fetch(page) for page in range(2, min(total, 5) + 1)]
    if total > 5:
        pages.append(fetch(total))
    return pages


def test_the_access_rules_give_each_user_the_expected_files(client):
    for user in CANNOT_READ:
        client.post("/auth/login", json={"user_id": user})
        listed = {d["file_id"] for d in client.get("/demo/documents").json()["documents"]}
        assert listed == set(ALL_FILES) - CANNOT_READ[user]


@pytest.mark.parametrize("user", ["kamal", "maya", "jp"])
def test_no_search_gives_information_from_a_forbidden_file(client, user):
    secrets = secret_lines(user)
    assert user == "jp" or secrets, "the test needs text that only forbidden files contain"
    client.post("/auth/login", json={"user_id": user})
    questions = EVALUATION + attack_questions(user)
    for question in questions:
        for mode in MODES:
            for response in search_all_pages(client, {"query": question, "mode": mode}):
                assert_no_leak(user, response, secrets, question)
    # A follow-up question cannot open a forbidden file by naming it.
    within = sorted(CANNOT_READ[user]) + ["project-cedar/01-project-brief.md"]
    for question in ("load", "compliance approval status", "steel grade", "incident"):
        for response in search_all_pages(client, {"query": question, "within": within}):
            assert_no_leak(user, response, secrets)


@pytest.mark.parametrize("user", ["kamal", "maya"])
def test_a_forbidden_file_cannot_be_read_directly(client, user):
    person = next(u for u in USERS if u["id"] == user)
    service = client.app.state.service
    for file_id in CANNOT_READ[user]:
        for page in (None, 1, 2):
            with pytest.raises(ServiceError) as refused:
                service.read(person, file_id, page)
            # The same answer as for a file that does not exist, so the name does not leak.
            assert refused.value.status == 404


@pytest.mark.parametrize("user", ["kamal", "maya"])
def test_the_document_overview_does_not_count_forbidden_files(client, user):
    client.post("/auth/login", json={"user_id": user})
    overview = client.get("/demo/documents").json()
    readable = set(ALL_FILES) - CANNOT_READ[user]
    assert sum(overview["by_type"].values()) == len(readable)
    assert sum(folder["readable"] for folder in overview["by_folder"]) == len(readable)
    assert all("files" not in folder for folder in overview["by_folder"])
    # Every readable type has a column, so each folder's types add up to its readable files.
    assert all(sum(folder["types"].values()) == folder["readable"] for folder in overview["by_folder"])


def test_a_sign_in_card_names_only_the_folders_its_user_may_read(client):
    cards = {card["id"]: card for card in client.get("/auth/users").json()["users"]}
    for user, card in cards.items():
        readable = set(ALL_FILES) - CANNOT_READ[user]
        folders = {f.split("/")[0] + "/" if "/" in f else "(top level)" for f in readable}
        assert {folder["folder"] for folder in card["folders"]} == folders, user
        assert sum(folder["readable"] for folder in card["folders"]) == len(readable)
        assert all(set(folder) == {"folder", "readable"} for folder in card["folders"])  # no totals
        forbidden_folders = {f.split("/")[0] for f in CANNOT_READ[user]} - {f.split("/")[0] for f in readable}
        assert not any(name in json.dumps(card) for name in forbidden_folders), user
