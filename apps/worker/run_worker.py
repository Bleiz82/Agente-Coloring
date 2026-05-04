#!/usr/bin/env python3
"""Worker process entrypoint.

Usage:
  python run_worker.py          # start worker normally
  python run_worker.py --dry-run  # validate imports + Redis connection, then exit 0
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Make colorforge_worker importable from repo root
sys.path.insert(0, str(Path(__file__).parent))

# Make colorforge_kdp importable (workspace package)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "packages" / "kdp-client"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports and Redis connection then exit",
    )
    args = parser.parse_args()

    if args.dry_run:
        try:
            from colorforge_worker.worker import get_redis_conn, run_worker  # noqa: F401
            try:
                conn = get_redis_conn()
                conn.ping()
                print("dry-run: imports OK, Redis reachable")
            except Exception as exc:
                print(f"dry-run: imports OK, Redis not reachable ({exc}) -- run `uv sync` first")
        except ImportError as exc:
            print(f"dry-run: import failed ({exc}) -- run `uv sync` to install dependencies")
        sys.exit(0)

    # Start health server in background and run worker
    import threading

    from colorforge_worker.health import start_health_server
    from colorforge_worker.worker import run_worker

    def _run_health() -> None:
        asyncio.run(start_health_server())

    health_thread = threading.Thread(target=_run_health, daemon=True)
    health_thread.start()
    run_worker()


if __name__ == "__main__":
    main()
