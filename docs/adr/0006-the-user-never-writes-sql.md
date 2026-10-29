# 6. The user never writes SQL; the chat agent may write constrained SQL

Users will not learn query languages ([B4](../constraints/background.md#b4)), so a question that is a SQL statement is refused with a request for plain language. For filters, joins and counts over tables, the chat agent (not the service, not the user) writes one SELECT, which runs against a read-only projection of the files the user may read, with an allowlist of tables and functions, a step budget and a row limit.

**Status:** accepted.

**Serves:** [B3](../constraints/background.md#b3), [B4](../constraints/background.md#b4), [K9](../constraints/clarifications.md#k9), [C4](../constraints/constraints.md#c4), [C5](../constraints/constraints.md#c5). Leaves [G7](../constraints/gaps.md#g7) open.

**Considered options:** the service translates questions into SQL with its own model (a model inside the service, [G3](../constraints/gaps.md#g3), and errors hidden from the user); no SQL path (counts and comparisons across schedules cannot be answered from passages); let the user type SQL (against [B4](../constraints/background.md#b4)).

**Consequences:** each SQL row carries its file and line, so it can be cited and shown with `get_document_evidence`. SQLite itself decides whether a question typed into the search is SQL: the text is compiled, never run, against the tables `query_sql` offers. Typed SQL that names those tables is refused; typed SQL that names some other table is searched as ordinary words (and finds nothing), because plain English such as "select the beams from the roof" has the same shape. The service cannot tell whether a statement came from the user through the agent ([G7](../constraints/gaps.md#g7)); the MCP instructions forbid it.

**Implemented by:** [`sql.py`](../../engineering_search/sql.py) (`Projection`, `is_sql_statement`), [`service.py`](../../engineering_search/service.py), [`mcp_server.py`](../../engineering_search/mcp_server.py). **Tested by:** [`tests/test_sql.py`](../../tests/test_sql.py), [`tests/test_sql_questions.py`](../../tests/test_sql_questions.py), [`tests/test_source_on_disc.py`](../../tests/test_source_on_disc.py).
