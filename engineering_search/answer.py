"""Answer a question from the indexed passages, with exact sources.

Two kinds of answer:
  answer  one value, for example "What is the roof load limit at Northgate?"
  list    every matching document, for example "Which documents specify S355?"
          or "Which documents have a roof load greater than 5 kN/m²?"

For one value:

The answer is one sentence or one table row, copied exactly from a passage.
The service does not write or change any text. Thus the answer always has a
certain source: a file, a page (PDF), a line range and a file version.

The steps:
  1. Split each of the best passages into sentences and table rows.
  2. Keep the parts that state a value: a number with a unit, a material
     grade or an approval status.
  3. Score each part by how many question words it contains. Words in the
     passage heading and the file name also count. A part whose sentence,
     heading and file name together contain every question word comes first.
  4. The best part is the answer. Other parts from other files that also
     state a value are returned as "also stated in", so a user sees conflicts.

A question word is *bound* to the answer when it is in the sentence, the
passage heading, the file path or the document title. Words elsewhere in
the document do not describe the value: "Roof load is not specified. Floor
load limit is 5 kN/m²." does not answer a roof load question.

  found       every question word is bound to the answer
  unverified  some question words are in the document, but not bound to the
              answer (`unbound_words`); the value may be about something else
  partial     some question words are not in the document (`missing_words`)
  not_found   no part states a value and matches enough question words
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import re
from typing import Callable

from .core import Passage
from .query import QueryPlan
from .units import QUANTITY, SIGNED, number, to_si

PASSAGES_TO_READ = 8
MIN_COVERAGE = 0.5
MAX_ALSO_STATED = 5

UNIT = r"(?:kN/m²|kN/m2|kN/m|kNm|kN|kPa|MPa|GPa|ksi|psi|psf|lb/ft|kip|t|tonnes?|mm|cm|m|ft|in|%)"
VALUE = re.compile(
    rf"(?:{SIGNED})\s?{UNIT}(?![\w/])"                            # 5 kN/m², -2 kN/m², 3.5 t
    r"|\b[SC]\d{2,3}(?:/\d{2})?[A-Z0-9+]*\b"                      # S355J2+N, C30/37
    r"|\bB500[A-C]\b|\bGrade\s+(?:HPS\s+)?\d+W?\b|\bHL-93\b"      # B500B, Grade 50W, HL-93
    r"|\b(?:not approved|approved|pending|rejected|draft|prohibited|restricted)\b",
    re.IGNORECASE)
TABLE_ROW = re.compile(r"^\s*\||\S {2,}\S")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
SUFFIXES = ("ations", "ation", "ings", "ing", "ions", "ion", "als", "al", "ed", "es", "s")


def stem(word: str) -> str:
    """A rough stem, close enough to compare question words with text."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


def stems(text: str) -> set[str]:
    return {stem(w) for w in re.findall(r"\w+", text.casefold())}


@dataclass(frozen=True)
class Part:
    text: str
    start_line: int
    end_line: int


def parts(passage: Passage) -> list[Part]:
    """Sentences and table rows of a passage, with their line numbers in the source."""
    found: list[Part] = []
    prose: list[tuple[int, str]] = []

    def flush_prose() -> None:
        if not prose:
            return
        starts, pieces, offset = [], [], 0
        for _, line in prose:
            starts.append(offset)
            pieces.append(line.strip())
            offset += len(line.strip()) + 1
        joined = " ".join(pieces)
        position = 0
        for sentence in SENTENCE_END.split(joined):
            begin = joined.index(sentence, position)
            position = begin + len(sentence)
            first = prose[bisect_right(starts, begin) - 1][0]
            last = prose[bisect_right(starts, position - 1) - 1][0]
            found.append(Part(sentence, first, last))
        prose.clear()

    for number, line in enumerate(passage.text.splitlines(), start=passage.start_line):
        if not line.strip():
            flush_prose()
        elif TABLE_ROW.search(line):
            flush_prose()
            found.append(Part(" ".join(line.split()), number, number))
        else:
            prose.append((number, line))
    flush_prose()
    return found


def term_stems(query: QueryPlan) -> list[tuple[bool, set[str]]]:
    """For each query term: (is prefix, accepted stems or prefixes)."""
    return [(t.prefix, {t.word} if t.prefix else {stem(w) for w in (t.word, *t.alternatives)})
            for t in query.terms]


def matches(term: tuple[bool, set[str]], words: set[str]) -> bool:
    prefix, options = term
    if prefix:
        return any(w.startswith(o) for o in options for w in words)
    return bool(options & words)


@dataclass(frozen=True)
class Candidate:
    part: Part
    passage: Passage
    rank: int
    coverage: float
    line_hits: int
    value: str
    covered: int = 0  # question words found in the sentence, its heading or its file name


def candidates(query: QueryPlan, passages: list[Passage]) -> list[Candidate]:
    terms = term_stems(query)
    if not terms:
        return []
    found = []
    for rank, passage in enumerate(passages[:PASSAGES_TO_READ]):
        context = stems(passage.heading + " " + re.sub(r"[^\w]+", " ", passage.file_id))
        for part in parts(passage):
            value = VALUE.search(part.text)
            if not value:
                continue
            words = stems(part.text)
            in_line = sum(matches(t, words) for t in terms)
            in_context = sum(matches(t, context) and not matches(t, words) for t in terms)
            coverage = (in_line + 0.5 * in_context) / len(terms)
            if in_line and coverage >= MIN_COVERAGE:
                found.append(Candidate(part, passage, rank, coverage, in_line, value.group(0),
                                       in_line + in_context))
    # Best: a source that has every question word somewhere (sentence, heading or file
    # name), then the most words in the sentence itself, then search rank.
    found.sort(key=lambda c: (-c.covered, -c.coverage, -c.line_hits, c.rank, c.part.start_line))
    return found


def citation(candidate: Candidate) -> dict:
    p = candidate.passage
    return {"text": candidate.part.text, "value": candidate.value, "file_id": p.file_id,
            "page": p.page, "start_line": candidate.part.start_line, "end_line": candidate.part.end_line,
            "heading": p.heading, "source_version": p.source_version}


def widen(query: QueryPlan, best: Candidate) -> Candidate:
    """Add the next one or two sentences of the same passage if they hold a missing question word.

    "The proposed roof load is 7 kN/m². Approval status: DRAFT, not approved."
    answers "Is the proposed 7 kN/m² roof load approved?" only with both sentences.
    The result is still one continuous piece of the source text.
    """
    terms = term_stems(query)
    sentences = parts(best.passage)
    first = last = sentences.index(best.part)
    missing = [t for t in terms if not matches(t, stems(best.part.text))]
    for step in (1, 2):
        if not missing or first + step >= len(sentences):
            break
        nearby = stems(sentences[first + step].text)
        if any(matches(t, nearby) for t in missing):
            last = first + step
            missing = [t for t in missing if not matches(t, nearby)]
    if last == first:
        return best
    span = sentences[first:last + 1]
    part = Part(" ".join(p.text for p in span), span[0].start_line, span[-1].end_line)
    return Candidate(part, best.passage, best.rank, best.coverage, best.line_hits, best.value, best.covered)


def title(passages: list[Passage]) -> str:
    """The document title: the heading at the top of the document, if it has one.

    Readers drop a heading that has no text under it, so the first passage's heading
    is the title only when that passage starts on the first lines of the first page;
    otherwise it is a section heading ("Roof") and would bind words it does not
    describe. Interim: readers will return the title themselves (reader manifests)."""
    first = passages[0] if passages else None
    return first.heading if first and first.page in (None, 1) and first.start_line <= 3 else ""


def bound_context(text: str, passage: Passage, document_title: str) -> set[str]:
    """Words that describe a sentence: the sentence, its heading, the file path and the document title."""
    return stems(" ".join((text, passage.heading, re.sub(r"[^\w]+", " ", passage.file_id), document_title)))


def answer(query: QueryPlan, passages: list[Passage],
           document_passages: Callable[[str], list[Passage]] | None = None) -> dict:
    """Return the answer with its source.

    document_passages(file_id) gives all passages of a document, for its title
    and to tell unbound words (in the document) from missing words (not in it).
    The statuses are described at the top of this module.
    """
    ranked = candidates(query, passages)
    if not ranked:
        return {"type": "answer", "status": "not_found",
                "message": "No document you can read states this. The closest passages are below."}
    best = widen(query, ranked[0])
    others, seen = [], {best.passage.file_id}
    for candidate in ranked[1:]:
        if candidate.passage.file_id not in seen and len(others) < MAX_ALSO_STATED:
            seen.add(candidate.passage.file_id)
            others.append(citation(candidate))
    document = document_passages(best.passage.file_id) if document_passages else [best.passage]
    bound = bound_context(best.part.text, best.passage, title(document))
    everywhere = bound | stems(" ".join(f"{p.heading} {p.text}" for p in document))
    terms = list(zip(query.terms, term_stems(query)))
    missing = [t.word for t, stemmed in terms if not matches(stemmed, everywhere)]
    unbound = [t.word for t, stemmed in terms if matches(stemmed, everywhere) and not matches(stemmed, bound)]
    status = "partial" if missing else "unverified" if unbound else "found"
    result = {"type": "answer", "status": status, **citation(best), "also_stated_in": others}
    if missing:
        result["missing_words"] = missing
        result["message"] = ("No document you can read matches every word of the question. "
                             f"This closest match does not mention: {', '.join(missing)}.")
    elif unbound:
        result["unbound_words"] = unbound
        result["message"] = ("This sentence states a value, but it does not say that it is about: "
                             f"{', '.join(unbound)}. The document mentions those words elsewhere. "
                             "Check the source before you use the value.")
    return result


def manifest(result: dict) -> dict:
    """The answer for the audit log: where it came from, not its text."""
    keys = ("file_id", "page", "start_line", "end_line", "source_version")
    sources = [result] if "file_id" in result else []
    sources += result.get("also_stated_in", []) + result.get("documents", [])
    return {"type": result["type"], "status": result["status"],
            "sources": [{k: s[k] for k in keys} for s in sources]}



# List questions and number comparisons ------------------------------------

COMPARATORS = (
    (">=", r"at least|not less than|>="), ("<=", r"at most|not more than|no more than|<="),
    (">", r"greater than|more than|higher than|larger than|above|over|exceeding|exceeds|>"),
    ("<", r"less than|lower than|smaller than|below|under|<"),
    ("=", r"equal to|exactly|equals|of|=|is"),
)
COMPARISON = re.compile(
    r"(?:(" + "|".join(pattern for _, pattern in COMPARATORS) + r")\s*)?" + QUANTITY.pattern, re.IGNORECASE)
LIST_QUESTION = re.compile(
    r"^\s*(?:which|what)\s+(?:\w+\s+){0,2}(?:documents?|files?|projects?|reports?|drawings?)\b"
    r"|\b(?:all|any|every|list|show)\b.{0,40}\b(?:documents?|files?|projects?)\b"
    r"|^\s*(?:do|does|are|is)\s+(?:we|there)\b"
    r"|^\s*(?:which|what)\s+of\s+(?:those|these|them)\b|^\s*of\s+(?:those|these)\b"
    r"|\bdocuments?\s+(?:that|which|with|in|for|about|mentioning|containing)\b", re.IGNORECASE)
MAX_LISTED = 200  # documents on one page of a list answer


@dataclass(frozen=True)
class Comparison:
    operator: str
    number: float
    unit: str
    kind: str     # dimension, e.g. "pressure"
    base: float   # the value in the SI unit of that dimension

    def accepts(self, text: str) -> str | None:
        """Return the first quantity in text that meets the comparison, or None."""
        for match in QUANTITY.finditer(text):
            measured = to_si(number(match.group(1)), match.group(2))
            if not measured or measured[0] != self.kind:
                continue
            value = measured[1]
            if {">": value > self.base, ">=": value >= self.base, "<": value < self.base,
                    "<=": value <= self.base, "=": abs(value - self.base) < 1e-9}[self.operator]:
                return match.group(0)
        return None

    def describe(self) -> str:
        return f"{self.operator} {self.number:g} {self.unit}"


@dataclass(frozen=True)
class Intent:
    mode: str                       # "answer" (one value) or "list" (all matching documents)
    search_text: str                # the question without the comparison
    comparison: Comparison | None


def understand(question: str, mode: str = "auto") -> Intent:
    """Decide whether the question asks for one value or for a list of documents."""
    is_list = bool(LIST_QUESTION.search(question))
    comparison, search_text = None, question
    for match in COMPARISON.finditer(question):
        measured = to_si(number(match.group(2)), match.group(3))
        if measured is None:
            continue
        word = (match.group(1) or "").casefold()
        operator = next((op for op, pattern in COMPARATORS if word and re.fullmatch(pattern, word)), None)
        if operator is None and not is_list:
            continue  # "Is the 7 kN/m² roof load approved?" names a value; it does not filter by it.
        comparison = Comparison(operator or "=", number(match.group(2)), match.group(3), *measured)
        search_text = (question[:match.start()] + " " + question[match.end():]).strip()
        break
    if mode == "auto":
        mode = "list" if is_list or (comparison and comparison.operator != "=") else "answer"
    if mode == "answer":
        return Intent("answer", question, None)
    return Intent(mode, search_text, comparison)


def list_documents(query: QueryPlan, comparison: Comparison | None,
                   documents: dict[str, list[Passage]]) -> dict:
    """One entry per document: the part that best shows why the document matches.

    `documents` holds only documents the user may read that contain every query word.
    With a comparison, the qualifying line must state the quantity and have every
    question word bound to it (line, heading, file path or title), so a floor load
    does not qualify a document for a roof load filter. All entries are returned;
    the caller pages them (MAX_LISTED per page).
    """
    terms = term_stems(query)
    entries = []
    for file_id, passages in documents.items():
        best, best_key = None, None
        document_title = title(passages)
        for passage in passages:
            context = stems(passage.heading + " " + re.sub(r"[^\w]+", " ", passage.file_id))
            for part in parts(passage):
                words = stems(part.text)
                in_line = sum(matches(t, words) for t in terms)
                in_context = sum(matches(t, context) and not matches(t, words) for t in terms)
                compared = comparison.accepts(part.text) if comparison else None
                if comparison:
                    bound = bound_context(part.text, passage, document_title)
                    if not compared or not in_line or not all(matches(t, bound) for t in terms):
                        continue
                value = compared or (VALUE.search(part.text) or [None])[0]
                key = (in_line + 0.5 * in_context, value is not None, in_line, -part.start_line)
                if best_key is None or key > best_key:
                    best_key, best = key, Candidate(part, passage, 0, key[0] / max(len(terms), 1),
                                                    in_line, value or "")
        if best is not None:
            entries.append(best)
    entries.sort(key=lambda c: (-c.coverage, c.passage.file_id))
    return {"type": "list", "status": "found" if entries else "not_found",
            "count": len(entries),
            "criteria": {"all_words": [t.label() for t in query.terms],
                         "comparison": comparison.describe() if comparison else None},
            "documents": [citation(c) for c in entries],
            **({} if entries else {"message": "No document you can read matches all of these words"
                                              + (" and the value condition." if comparison else ".")})}
