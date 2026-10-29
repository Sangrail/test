# 3. Answer with a sentence copied from the source, and refuse rather than guess

An answer is one sentence or table row copied exactly from a document, with the file, the location and the quoted text; the service never writes answer text. When the question's words are not bound to the value (its sentence, heading or file), or the cited file has changed since it was indexed, the service says so or refuses instead of answering.

**Status:** accepted.

**Serves:** [U5](../constraints/use-case.md#u5), [U6](../constraints/use-case.md#u6), [K3](../constraints/clarifications.md#k3), [K4](../constraints/clarifications.md#k4), [K14](../constraints/clarifications.md#k14).

**Considered options:** a language model writes the answer from retrieved passages (fluent, but the words are not in the source); return the best passages and let the user judge (not an answer, [K14](../constraints/clarifications.md#k14)).

**Consequences:** an answer has a status: found, unverified (some question words are not bound), partial (some are missing) or not found. A search or SQL query lists files that changed on disc in `changed_files` and answers without them; a read of a changed file is refused. Some answerable questions are refused; a wrong answer is worse.

**Implemented by:** [`answer.py`](../../engineering_search/answer.py), `SearchService.search` and `changed_on_disc` in [`service.py`](../../engineering_search/service.py). **Tested by:** [`tests/test_binding.py`](../../tests/test_binding.py), [`tests/test_use_case.py`](../../tests/test_use_case.py), [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py).
