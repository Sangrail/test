"""The coverage report: which files were read, how fully, and why the others were not.

Built from an inventory and the reader registry only, so it can run without the
search index. Coverage is reported by file type and format version, by status,
by top-level folder (project) and by capability (text, tables, ...), not as one
"files processed" number. It names files, so only the index team may see it.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .inventory import Inventory, SourceFile
from .readers import ReaderRegistry
from .status import (CLASSIFIED, FAILED, HINTS, INDEXED_FULL, INDEXED_PARTIAL, NO_EXTRACTABLE_CONTENT,
                     NO_TEXT_LAYER, NOT_SUPPORTED)

CAPABILITIES = ("text", "tables", "metadata", "geometry")


def capability_outcomes(source: SourceFile, capabilities: set[str]) -> dict[str, str]:
    """ok, partial, none, failed, not_checked or unsupported, for each capability."""
    outcome = {INDEXED_FULL: "ok", INDEXED_PARTIAL: "partial", NO_TEXT_LAYER: "none",
               NO_EXTRACTABLE_CONTENT: "none", CLASSIFIED: "not_checked"}.get(source.status, "failed")
    result = {name: outcome if name in capabilities else "unsupported" for name in CAPABILITIES}
    if source.format_version and "metadata" not in capabilities:
        result["metadata"] = "header_only"  # the detector read the format version, nothing more
    return result


def coverage_report(inventory: Inventory, registry: ReaderRegistry) -> dict:
    capabilities = {f"{r.manifest.reader_id}@{r.manifest.reader_version}": set(r.manifest.capabilities.names())
                    for r in registry.readers}
    formats: dict[tuple, dict] = {}
    folders: dict[str, Counter] = defaultdict(Counter)
    by_capability: dict[str, Counter] = {name: Counter() for name in CAPABILITIES}
    gaps = []
    for source in sorted(inventory.files.values(), key=lambda f: f.file_id):
        key = (source.file_type, source.format_version)
        row = formats.setdefault(key, {"file_type": source.file_type, "format_version": source.format_version,
                                       "files": 0, "bytes": 0, "statuses": Counter()})
        row["files"] += 1
        row["bytes"] += source.size
        row["statuses"][source.status] += 1
        folder = source.file_id.split("/")[0] + "/" if "/" in source.file_id else "(top level)"
        folders[folder]["files"] += 1
        folders[folder][source.status] += 1
        outcomes = capability_outcomes(source, capabilities.get(source.reader or "", set()))
        for name, outcome in outcomes.items():
            by_capability[name][outcome] += 1
        if source.status != INDEXED_FULL:
            gaps.append({"file_id": source.file_id, "file_type": source.file_type,
                         "format_version": source.format_version, "reader": source.reader,
                         "status": source.status, "capabilities": outcomes,
                         "observation": source.observation, "error": source.error,
                         "warnings": list(source.warnings), "hint": HINTS.get(source.status, "")})
    statuses = inventory.by_status()
    return {
        "files": len(inventory), "bytes": sum(f.size for f in inventory.files.values()),
        "fully_indexed": statuses.get(INDEXED_FULL, 0),
        "partially_indexed": statuses.get(INDEXED_PARTIAL, 0),
        "no_content": statuses.get(NO_TEXT_LAYER, 0) + statuses.get(NO_EXTRACTABLE_CONTENT, 0),
        "not_supported": sum(n for s, n in statuses.items() if s in NOT_SUPPORTED),
        "failed": sum(n for s, n in statuses.items() if s in FAILED),
        "not_checked": statuses.get(CLASSIFIED, 0),
        "by_status": statuses,
        "by_format": [{**row, "statuses": dict(sorted(row["statuses"].items()))}
                      for _, row in sorted(formats.items(), key=lambda item: (item[0][0], item[0][1] or ""))],
        "by_capability": {name: dict(sorted(c.items())) for name, c in by_capability.items()},
        "by_folder": [{"folder": folder, "files": c.pop("files"), "statuses": dict(sorted(c.items()))}
                      for folder, c in sorted(folders.items())],
        "readers": registry.manifests(),
        "gaps": gaps,
    }
