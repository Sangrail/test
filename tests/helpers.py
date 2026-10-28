"""Shared test helpers."""
from pathlib import Path

TEST_REPOSITORY = Path(__file__).resolve().parents[1] / "test-repository"
CEDAR_FOLDER = "project-cedar"


def seed_permission_demo(root: Path):
    """Copy the Project Cedar files from test-repository/ into a test folder.

    Project Cedar has a rule for each file, so these tests can check
    permissions on a small set of files.
    """
    destination = root / CEDAR_FOLDER
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted((TEST_REPOSITORY / CEDAR_FOLDER).glob("*.md")):
        target = destination / source.name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
