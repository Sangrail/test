"""Create a source ZIP containing only explicitly selected code and synthetic fixtures."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = ("README.md", "ARCHITECTURE.md", "RUNNING.md", "TODO.md", "GLOSSARY.md",
             "design/system-design.svg", "design/system-design.png", "design/make_diagram.py",
             "design/code-architecture.svg", "design/code-architecture.png", "design/make_architecture.py",
             "pyproject.toml", "uv.lock", ".gitignore")
PATTERNS = ("engineering_search/*.py", "engineering_search/indexing/*.py", "engineering_search/indexing/readers/*.py", "engineering_search/static/*.html",
            "engineering_search/static/*.css", "engineering_search/static/*.js",
            "test-repository/**/*.md", "test-repository/**/*.pdf", "test-repository/**/*.txt",
            "evaluation/*.json", "evaluation/*.md", "evaluation/results/*.json", "scripts/*.py", "tests/*.py",
            "design/*.md", "docs/*.md", "docs/adr/*.md")


def package(destination: Path) -> int:
    files = {ROOT / name for name in TOP_LEVEL}
    for pattern in PATTERNS:
        files.update(ROOT.glob(pattern))
    files = {path for path in files if "uploads" not in path.relative_to(ROOT).parts}
    # Fail rather than silently omit required source or follow external symlinks.
    for path in files:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Invalid source file: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, Path("engineering-search-mvp") / path.relative_to(ROOT))
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / ".runtime" / "engineering-search-mvp.zip")
    args = parser.parse_args()
    count = package(args.output)
    print(f"Packaged {count} source files: {args.output.resolve()}")


if __name__ == "__main__":
    main()
