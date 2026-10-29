"""The decision records and the brief's item pages must not drift apart.

docs/constraints/ splits the brief into items (B, C, U, T, S), clarifications (K) and
gaps (G, O); docs/adr/ cites them. These pages are written by hand, so these tests check:
  - every relative link in the repository's documents resolves, anchor included;
  - in docs/adr and docs/constraints, every item ID is a link, to its own definition;
  - each item page's summary table lists exactly the items the page defines;
  - the ADR index lists every decision once, with its title, status and items.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "docs/constraints"
ADR = ROOT / "docs/adr"
PAGES = {"B": "background.md", "C": "constraints.md", "U": "use-case.md", "T": "task.md", "S": "scope.md",
         "K": "clarifications.md", "G": "gaps.md", "O": "gaps.md"}
ITEM = r"[BCUTSKGO]\d{1,2}"
BARE = re.compile(r"(?<![\[\w/#-])(" + ITEM + r")(?![\w\]])")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
ITEM_LINK = re.compile(r"\[(" + ITEM + r")\]\(([^)\s]+)\)")
SPEC = sorted(ADR.glob("*.md")) + sorted(CONSTRAINTS.glob("*.md"))


def documents() -> list[Path]:
    found = [p for p in ROOT.rglob("*.md")
             if not {".venv", "test-repository", ".git", "node_modules"} & set(p.relative_to(ROOT).parts)]
    return sorted(found)


def anchors(page: Path) -> set[str]:
    text = page.read_text()
    explicit = set(re.findall(r'<a id="([^"]+)"', text))
    headings = {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
                for h in re.findall(r"^#+ (.*)$", text, re.M)}
    return explicit | headings


def prose(text: str):
    """The lines that may cite items: not headings, quotes of the brief or anchors; without code spans."""
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.startswith(("#", ">", "<a id=")):
            yield number, re.sub(r"`[^`]*`", "", line)


@pytest.mark.parametrize("page", documents(), ids=lambda p: str(p.relative_to(ROOT)))
def test_every_relative_link_resolves(page):
    broken = []
    for _, target in LINK.findall(re.sub(r"`[^`\n]*`", "", page.read_text())):  # a code span is an example, not a link
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        destination = (page.parent / path).resolve() if path else page
        if not destination.exists():
            broken.append(target)
        elif anchor and destination.suffix == ".md" and anchor not in anchors(destination):
            broken.append(target)
    assert broken == [], f"broken links in {page.relative_to(ROOT)}: {broken}"


@pytest.mark.parametrize("page", SPEC, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_item_id_is_a_link_to_its_own_definition(page):
    text = page.read_text()
    bare, wrong = [], []
    for number, line in prose(text):
        without_links = LINK.sub("", line)
        bare += [f"line {number}: {m}" for m in BARE.findall(without_links)]
        for item, target in ITEM_LINK.findall(line):
            path, _, anchor = target.partition("#")
            destination = (page.parent / path).resolve() if path else page.resolve()
            expected = (CONSTRAINTS / PAGES[item[0]]).resolve()
            if destination != expected or anchor != item.lower():
                wrong.append(f"line {number}: [{item}]({target})")
    assert bare == [], f"item IDs that are not links in {page.name}: {bare}"
    assert wrong == [], f"item links to the wrong place in {page.name}: {wrong}"


@pytest.mark.parametrize("name", sorted(set(PAGES.values())))
def test_each_item_page_table_lists_exactly_the_items_it_defines(name):
    text = (CONSTRAINTS / name).read_text()
    defined = set(re.findall(r'<a id="([a-z]\d{1,2})"', text))
    listed = {a for a in re.findall(r"^\| \[[A-Z]\d{1,2}\]\(#([a-z]\d{1,2})\)", text, re.M)}
    assert defined, f"{name} defines no items"
    assert listed == defined, f"{name}: in the table but not defined {listed - defined}; defined but not in the table {defined - listed}"


def expand(cell: str) -> set[str]:
    """The item IDs in a cell, with ranges such as U2–U6 expanded."""
    ids = set(re.findall(r"\[(" + ITEM + r")\]", cell))
    for first, last in re.findall(r"\[(" + ITEM + r")\]\([^)]*\)–\[(" + ITEM + r")\]", cell):
        if first[0] == last[0]:
            ids |= {f"{first[0]}{n}" for n in range(int(first[1:]), int(last[1:]) + 1)}
    return ids


def records() -> dict[str, Path]:
    return {p.name[:4]: p for p in ADR.glob("[0-9][0-9][0-9][0-9]-*.md")}


def test_the_adr_index_lists_every_decision_with_its_title_status_and_items():
    rows = re.findall(r"^\| \[(\d{4})\]\(([^)]+)\) \| ([^|]+) \| ([^|]+) \|$", (ADR / "README.md").read_text(), re.M)
    assert sorted(r[0] for r in rows) == sorted(records()), "the index and the decision files differ"
    for number, target, title, serves in rows:
        record = records()[number]
        assert target == record.name, f"ADR {number} links to {target}"
        text = record.read_text()
        heading = re.match(r"# \d+\. (.*)", text).group(1)
        proposed = re.search(r"^\*\*Status:\*\* proposed", text, re.M) is not None
        assert title.strip().startswith("*Proposed:*") == proposed, f"ADR {number}: index and record disagree on status"
        assert title.strip().removeprefix("*Proposed:* ").lower() == heading.lower(), f"ADR {number}: title differs"
        serves_line = re.search(r"^\*\*Serves:\*\* (.*)$", text, re.M)
        assert serves_line, f"ADR {number} has no Serves line"
        missing = expand(serves) - expand(serves_line.group(1))
        assert expand(serves) and not missing, f"ADR {number}: the index cites {missing}, which the record does not"


@pytest.mark.parametrize("record", sorted(records().values()), ids=lambda p: p.name[:4])
def test_every_decision_has_a_status_and_serves_at_least_one_item(record):
    text = record.read_text()
    assert re.search(r"^\*\*Status:\*\* (accepted|proposed|superseded)", text, re.M), f"{record.name}: no status"
    serves = re.search(r"^\*\*Serves:\*\* (.*)$", text, re.M)
    assert serves and expand(serves.group(1)), f"{record.name}: serves no item of the brief"
