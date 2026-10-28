from pathlib import Path

from engineering_search.core import extract, source_files
from engineering_search.query import plan
from engineering_search.store import SQLiteSearchIndex

TEST_REPOSITORY = Path(__file__).resolve().parents[1] / "test-repository"
NORTHGATE = TEST_REPOSITORY / "project-northgate" / "northgate-warehouse-structural-calculations.pdf"


def test_plan_drops_common_words_adds_synonyms_and_prefixes_codes():
    query = plan("What is the roof load limit for S355?")
    assert [t.word for t in query.terms] == ["roof", "load", "limit", "s355"]
    assert "maximum" in query.terms[2].alternatives
    assert query.terms[3].prefix and query.fts().endswith('"s355"*')
    assert set(query.ignored) == {"what", "is", "the", "for"}
    assert plan("what is it").terms  # Only common words: search for them anyway.


def test_pdf_passages_keep_page_numbers_and_numbered_headings():
    document, _ = extract(NORTHGATE, TEST_REPOSITORY)
    roof = next(p for p in document.passages if p.heading == "3.1 Roof load limit")
    assert roof.page == 2 and roof.start_line >= 1
    assert "0.6 kN/m²" in roof.text
    assert all(p.page for p in document.passages)


def test_index_matches_word_forms_and_ranks_full_matches_first(tmp_path):
    (tmp_path / "a.md").write_text("# Notes\n\nThe roof was inspected.\n")
    (tmp_path / "b.md").write_text("# Roof\n\nMaximum roof loads: 5 kN/m².\n")
    index = SQLiteSearchIndex()
    index.apply([extract(p, tmp_path)[0] for p in source_files(tmp_path)], [])
    results = index.candidates("roof load limit")
    assert [p.file_id for p in results] == ["b.md", "a.md"]  # "loads" and "maximum" both match.


def test_index_persists_and_applies_changes_atomically(tmp_path):
    (tmp_path / "a.md").write_text("# A\n\nAlpha value.\n")
    path = tmp_path / "state" / "index.sqlite3"
    index = SQLiteSearchIndex(path)
    index.apply([extract(tmp_path / "a.md", tmp_path)[0]], [])

    class Broken:
        file_id = "b.md"
        source_version = "x"
        passages = None  # Fails part-way through the insert.

    try:
        index.apply([extract(tmp_path / "a.md", tmp_path)[0], Broken()], ["a.md"])
    except TypeError:
        pass
    reopened = SQLiteSearchIndex(path)
    assert set(reopened.versions()) == {"a.md"}
    assert reopened.search("alpha", 10)[1] == 1
    assert reopened.indexed_at()
