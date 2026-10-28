"""Write 120 small synthetic project documents into test-repository/generated-projects/.

They make the test repository larger than 100 documents, as the use case
requires. Each one states a roof load, a material and an approval status, so
they also compete with the real answers in the other test documents.

    uv run --frozen python scripts/seed_demo.py
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("Approved", "Pending", "Draft")

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--output", type=Path, default=ROOT / "test-repository" / "generated-projects")
parser.add_argument("--count", type=int, default=120)
args = parser.parse_args()
if args.count < 1:
    parser.error("count must be positive")
args.output.mkdir(parents=True, exist_ok=True)
for i in range(args.count):
    (args.output / f"project-{i:03}.md").write_text(
        f"# Synthetic project {i:03}\n\n"
        "SYNTHETIC TEST DATA - not for engineering use.\n\n"
        "## Roof load\n\n"
        "| Parameter | Value | Conditions | Approval status |\n"
        "| --- | --- | --- | --- |\n"
        f"| Maximum roof load | {(i % 9) + 1} kN/m² | Static, dry | {STATUSES[i % 3]} |\n\n"
        "## Material specification\n\n"
        f"Support material: S{275 + 80 * (i % 2)} steel. Project identifier: DEMO{i:03}.\n",
        encoding="utf-8",
    )
print(f"Wrote {args.count} synthetic Markdown documents to {args.output}")
