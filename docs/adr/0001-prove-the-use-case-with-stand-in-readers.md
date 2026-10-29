# 1. Prove the use case with sample stand-in readers, not real connectors

The brief says connectors that extract metadata, text and properties already exist ([C3](../constraints/constraints.md#c3)), so we build small sample readers (Markdown, text-layer PDF, CSV, XLSX, and the notes and title block of a DXF drawing) and fixed fact rules only to prove the use case end to end. They are labelled as stand-ins for the connectors' output and are not grown into products.

**Status:** accepted.

**Serves:** [C3](../constraints/constraints.md#c3), [K7](../constraints/clarifications.md#k7); on the way to [U2](../constraints/use-case.md#u2) and [U6](../constraints/use-case.md#u6). Leaves [G8](../constraints/gaps.md#g8) open.

**Considered options:** integrate a real connector (none is available to the MVP); read only Markdown (does not show that a PDF or a CAD drawing can be answered without opening it); read many formats fully (builds what already exists).

**Consequences:** every reader declares what it reads in a manifest and is chosen by one registry, so a real connector can replace it behind the same interface. Files no reader takes are reported in the coverage report with a reason, never dropped silently. A table row (a workbook row, a DXF title-block attribute) is quoted as its cells joined with " | ", each cell copied exactly, and cites the lines that hold them.

**Implemented by:** [`engineering_search/indexing/readers/`](../../engineering_search/indexing/readers/), [`facts.py`](../../engineering_search/indexing/facts.py), [`detect.py`](../../engineering_search/indexing/detect.py). **Tested by:** [`tests/test_indexer.py`](../../tests/test_indexer.py), [`tests/test_dxf.py`](../../tests/test_dxf.py), [`tests/test_facts.py`](../../tests/test_facts.py), [`tests/test_coverage.py`](../../tests/test_coverage.py).
