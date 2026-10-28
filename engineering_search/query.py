"""Turn a plain-language question into an index query.

Steps:
  1. Split the question into words (same rule as core.tokens, kept in order).
  2. Drop common English words ("what", "is", "the") that carry no meaning.
  3. Add a few engineering synonyms ("limit" also finds "maximum").
  4. Words that contain a digit become prefix searches, so "S355" also finds
     "S355J2". Other words are stemmed by the index ("loads" finds "load").

The index matches any word (OR) and then ranks passages that contain more of
the words first. The plan is echoed back so the user sees what was searched.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

STOP_WORDS = frozenset("""
a about above after all also am an and any are as at be been being below between both but by
can could did do does doing done during each else for from had has have having he her here hers
how i if in into is it its just may me might more most must my no nor not of off on once only or
other our out over please same she should show so some such tell than that the their them then
there these they this those through to too under until up us very was we were what when where
which while who whom why will with would you your give find list document documents
file files those these mention mentions mentioned specify specifies specified contain contains
state states stated include includes say says use used uses using
""".split())

# Small, hand-made dictionary. Each group is a set of words treated as equal.
# Stemming already covers word forms (approve, approved, approval).
SYNONYM_GROUPS = (
    {"limit", "maximum", "max", "allowable", "permitted", "permissible", "capacity"},
    {"prohibited", "restricted", "banned", "forbidden"},
    {"specification", "spec", "grade"},
    {"footbridge", "pedestrian"},
    {"rejected", "refused", "declined"},
)
SYNONYMS = {word: sorted(group - {word}) for group in SYNONYM_GROUPS for word in group}


@dataclass(frozen=True)
class Term:
    word: str
    alternatives: tuple[str, ...]
    prefix: bool

    def fts(self) -> str:
        """FTS5 syntax for this term, e.g. ("limit" OR "maximum") or "s355"*."""
        if self.prefix:
            return f'"{self.word}"*'
        options = [f'"{w}"' for w in (self.word, *self.alternatives)]
        return options[0] if len(options) == 1 else "(" + " OR ".join(options) + ")"

    def label(self) -> str:
        if self.prefix:
            return f"{self.word}*"
        if self.alternatives:
            return f"{self.word} (or {', '.join(self.alternatives)})"
        return self.word


@dataclass(frozen=True)
class QueryPlan:
    terms: tuple[Term, ...]
    ignored: tuple[str, ...]

    def fts(self) -> str:
        return " OR ".join(term.fts() for term in self.terms)

    def searched_for(self) -> str:
        return " · ".join(term.label() for term in self.terms)


def plan(question: str) -> QueryPlan:
    words = list(dict.fromkeys(w for w in re.findall(r"\w+", question.casefold()) if w.strip("_")))
    kept = [w for w in words if w not in STOP_WORDS]
    if not kept:  # A question made only of common words: search for them anyway.
        kept = words
    ignored = tuple(w for w in words if w not in kept)
    terms = tuple(Term(word, () if any(c.isdigit() for c in word) else tuple(SYNONYMS.get(word, ())),
                       prefix=any(c.isdigit() for c in word))
                  for word in kept)
    return QueryPlan(terms, ignored)
