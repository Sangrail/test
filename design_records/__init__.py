"""Design records: the brief, the constraints and the architecture decision records of this
project, in one SQLite database (design/records/records.sqlite).

The database is the source. The ADR pages, the ADR index and the constraint pages are
generated from it, with a SQL dump for review:

    uv run --frozen python -m design_records generate   # write the pages and the dump
    uv run --frozen python -m design_records check      # list differences and broken links
    uv run --frozen python -m design_records mcp        # a read-only MCP server over stdio

    records.py     the schema, rendering the pages, and the consistency checks
    mcp_server.py  tools to look up constraints, decisions and the files they govern

tests/test_design_records.py runs the check in the suite. See design/records/README.md.
"""
