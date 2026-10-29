"""Run a self-contained instance on this machine; no external services required."""
import argparse
import os
from pathlib import Path

import uvicorn

from .runtime import build_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path,
                        default=Path(os.environ.get("DOCUMENT_ROOT", "test-repository")),
                        help="The existing repository to index, searched recursively")
    parser.add_argument("--state-dir", type=Path,
                        default=Path(os.environ.get("STATE_DIR", ".runtime")),
                        help="Writable folder for the index and audit databases")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-startup-index", action="store_true",
                        help="Build manually from the backend dashboard instead")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    root = args.documents.expanduser().resolve()
    if not root.is_dir():
        parser.error("Document directory does not exist; supply --documents")
    state = args.state_dir.expanduser().resolve()
    app = build_app(root, state, index_on_start=not args.no_startup_index)
    print(f"Documents: {root}\nRuntime data: {state}", flush=True)
    print(f"Search: http://127.0.0.1:{args.port}/search", flush=True)
    print("Pretend login: use an SSH tunnel for remote access. One API process.", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
