"""CLI entrypoint for the Performance Monitor pipeline.

Usage:
    python scripts/run_monitor.py --dry-run
    python scripts/run_monitor.py --all-accounts
    python scripts/run_monitor.py --account-id <uuid>
    python scripts/run_monitor.py --account-id <uuid> --date-from 2026-04-01
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date


def _dry_run_check() -> None:
    errors: list[str] = []

    try:
        import colorforge_agents.monitor.performance_monitor  # noqa: F401
        import colorforge_agents.monitor.scorer  # noqa: F401
        import colorforge_agents.monitor.analyzer  # noqa: F401
        import colorforge_agents.monitor.policy_proposer  # noqa: F401
        import colorforge_agents.monitor.snapshot_writer  # noqa: F401
    except ImportError as exc:
        errors.append(f"Import error: {exc}")

    for var in ["DATABASE_URL", "ANTHROPIC_API_KEY"]:
        if not os.getenv(var):
            errors.append(f"Missing env var: {var}")

    if errors:
        for e in errors:
            print(f"[dry-run] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("[dry-run] All imports OK. Exiting 0.")
    sys.exit(0)


async def _run(account_ids: list[str], date_from: date | None) -> None:
    from pathlib import Path

    import anthropic
    from prisma import Prisma

    from colorforge_agents.monitor.performance_monitor import PerformanceMonitor

    prisma = Prisma()
    await prisma.connect()

    try:
        if not account_ids:
            accounts = await prisma.account.find_many()
            account_ids = [a.id for a in accounts]

        claude_client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        assets_base = Path(os.getenv("ASSETS_BASE", "/var/colorforge/assets"))

        monitor = PerformanceMonitor(prisma, claude_client, assets_base)
        result = await monitor.run(account_ids)

        print(
            f"Monitor complete: accounts={result.accounts_scraped} "
            f"books={result.books_scored} "
            f"policies={result.policies_proposed} "
            f"alerts={result.alerts_written}"
        )
    finally:
        await prisma.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="ColorForge Performance Monitor")
    parser.add_argument("--dry-run", action="store_true", help="Validate imports and config, then exit")
    parser.add_argument("--account-id", metavar="UUID", help="Run for a single account")
    parser.add_argument("--all-accounts", action="store_true", help="Run for all accounts in DB")
    parser.add_argument("--date-from", metavar="YYYY-MM-DD", help="Override date range start")
    args = parser.parse_args()

    if args.dry_run:
        _dry_run_check()

    if not args.account_id and not args.all_accounts:
        parser.error("Provide --account-id UUID, --all-accounts, or --dry-run")

    account_ids = [args.account_id] if args.account_id else []

    date_from: date | None = None
    if args.date_from:
        date_from = date.fromisoformat(args.date_from)

    asyncio.run(_run(account_ids, date_from))


if __name__ == "__main__":
    main()
