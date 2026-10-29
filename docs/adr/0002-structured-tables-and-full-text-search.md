# 2. Store structured tables and a lexical full-text index; leave semantic search out

The brief allows "structured and/or semantic stores" ([C4](../constraints/constraints.md#c4)). We store tables and typed facts (structured) and a SQLite FTS5 full-text index over passages (lexical), in one local file. Semantic search with embeddings is out of scope ([O1](../constraints/gaps.md#o1)).

**Status:** accepted.

**Serves:** [C4](../constraints/constraints.md#c4), [K8](../constraints/clarifications.md#k8); [U2](../constraints/use-case.md#u2), [U5](../constraints/use-case.md#u5) (a lexical match shows exactly which words matched, so the quoted source can be checked).

**Considered options:** embeddings with a vector store (cannot explain why a passage matched, and adds a model to govern, [G3](../constraints/gaps.md#g3)); a search server such as Elasticsearch (more to run for an MVP); tables only (most parameters are stated in prose).

**Consequences:** paraphrases and synonyms that are not in the synonym list are missed; that is measured on real questions ([G4](../constraints/gaps.md#g4)). Units are normalised in facts; status words are not ([G6](../constraints/gaps.md#g6)).

**Implemented by:** [`store.py`](../../engineering_search/store.py), [`query.py`](../../engineering_search/query.py), [`facts.py`](../../engineering_search/indexing/facts.py). **Tested by:** [`tests/test_index.py`](../../tests/test_index.py), [`tests/test_search.py`](../../tests/test_search.py), [`tests/test_facts.py`](../../tests/test_facts.py).
