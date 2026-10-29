"""Design records: intent, constraints, scope and the architecture decision records of this
project, with every version of each, in one SQLite database (docs/records/design.sqlite).

The database is the source of truth. The ADR pages, the ADR index, the constraint pages, a
self-contained browser view and a SQL dump are build artefacts, generated from it at commit
time by .githooks/pre-commit:

    uv run --frozen python -m design_records generate   # write the generated files
    uv run --frozen python -m design_records check      # list differences, broken links, warnings
    uv run --frozen python -m design_records mcp        # the MCP server over stdio

    schema.sql     the tables, the append-only guards, and the views that take plain SQL changes
    records.py     rendering the generated files, and the consistency checks
    viewer.html    the template of the browser view
    mcp_server.py  tools to look up records and their history, and to propose drafts

tests/test_design_records.py runs the check in the suite. See docs/records/README.md.
"""
