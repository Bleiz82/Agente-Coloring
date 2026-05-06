"""CLI entrypoint for the Publisher pipeline.

Usage:
    python scripts/run_publish.py --dry-run
    python scripts/run_publish.py --book-id <uuid>
"""

from __future__ import annotations

import argparse
import os
import sys


def _dry_run_check() -> None:
    """Validate imports, env vars, and config — then exit 0."""
    errors: list[str] = []

    try:
        import colorforge_agents.seo.listing_agent  # noqa: F401
        import colorforge_agents.gates.listing_gate  # noqa: F401
        import colorforge_agents.publisher.publisher_agent  # noqa: F401
    except ImportError as exc:
        errors.append(f"Import error: {exc}")

    for var in ["DATABASE_URL", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
        if not os.getenv(var):
            errors.append(f"Missing env var: {var}")

    assets_base = os.getenv("ASSETS_BASE", "/var/colorforge/assets")
    print(f"[dry-run] Assets base: {assets_base}")

    if errors:
        for e in errors:
            print(f"[dry-run] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("[dry-run] All imports OK. Exiting 0.")
    sys.exit(0)


async def _run(book_id: str) -> None:
    """Run the full Publisher pipeline for an existing book in DB."""
    raise NotImplementedError(
        f"DB-backed book publishing not yet implemented (book_id={book_id}). "
        "Use --dry-run to validate imports."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ColorForge Publisher pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Validate imports and config, then exit")
    parser.add_argument("--book-id", metavar="UUID", help="Book ID to publish")
    args = parser.parse_args()

    if args.dry_run:
        _dry_run_check()

    if not args.book_id:
        parser.error("Provide --book-id UUID or --dry-run")

    import asyncio
    asyncio.run(_run(args.book_id))


if __name__ == "__main__":
    main()
