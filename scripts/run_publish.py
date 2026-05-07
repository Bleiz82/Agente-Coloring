"""Manual single-book publish script for soft-launch operations.

Runs the full ColorForge publish pipeline for a single niche with human
review gate before submission to KDP.

Usage:
    # Validate environment only (no DB, no KDP):
    uv run python scripts/run_publish.py --dry-run

    # Soft-launch: generate + review + publish on secondary account:
    uv run python scripts/run_publish.py \\
        --account secondary \\
        --niche-id <uuid> \\
        --review

    # Non-interactive (CI/automation):
    uv run python scripts/run_publish.py \\
        --account primary \\
        --niche-id <uuid>

Environment variables required (set via Doppler or .env):
    DATABASE_URL          Postgres connection string
    GEMINI_API_KEY        Gemini image generation key
    ANTHROPIC_API_KEY     Claude critic/vision key
    ASSETS_BASE           Base directory for PDF assets (default /var/colorforge/assets)
    REDIS_URL             Redis URL for currency cache (optional)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: ensure colorforge_agents is importable when run from repo root
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "agents"))

_REQUIRED_ENV = ["DATABASE_URL", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
_ASSETS_BASE_DEFAULT = "/var/colorforge/assets"


# ---------------------------------------------------------------------------
# Dry-run validation
# ---------------------------------------------------------------------------


def _dry_run_check() -> None:
    """Validate imports, env vars, and config — exit 0 if all OK."""
    errors: list[str] = []

    modules = [
        "colorforge_agents.seo.listing_agent",
        "colorforge_agents.gates.listing_gate",
        "colorforge_agents.gates.content_gate",
        "colorforge_agents.publisher.publisher_agent",
        "colorforge_agents.generator.cover_compositor",
        "colorforge_agents.generator.front_matter",
        "colorforge_agents.utils.currency",
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"  [ok] import {mod}")
        except ImportError as exc:
            errors.append(f"Import error: {mod}: {exc}")
            print(f"  [FAIL] import {mod}: {exc}", file=sys.stderr)

    for var in _REQUIRED_ENV:
        if not os.getenv(var):
            errors.append(f"Missing env var: {var}")
            print(f"  [FAIL] {var} not set", file=sys.stderr)
        else:
            print(f"  [ok] {var} is set")

    assets_base = Path(os.getenv("ASSETS_BASE", _ASSETS_BASE_DEFAULT))
    print(f"  [info] ASSETS_BASE={assets_base}")

    if errors:
        print(f"\n{len(errors)} error(s) found — fix before launch.", file=sys.stderr)
        sys.exit(1)

    print("\nAll checks passed. Safe to publish.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Review gate
# ---------------------------------------------------------------------------


def _human_review_gate(niche_id: str, account: str) -> bool:
    """Prompt operator to approve the publish. Returns True if approved."""
    print("\n" + "=" * 60)
    print("  HUMAN REVIEW GATE")
    print(f"  niche_id : {niche_id}")
    print(f"  account  : {account}")
    print("=" * 60)
    print("\n  Checklist before approving:")
    print("  [ ] Cover image looks correct (no artifacts, no TM violations)")
    print("  [ ] Title/subtitle passes ListingGate (no blocked terms)")
    print("  [ ] Price in correct range ($7.99-$14.99)")
    print("  [ ] AI disclosure present on copyright page")
    print("  [ ] File sizes within KDP 650MB limit")
    print("  [ ] Weekly quota not exceeded for this account+format")
    print()
    answer = input("  Type 'yes' to publish, anything else to abort: ").strip().lower()
    return answer == "yes"


# ---------------------------------------------------------------------------
# Main publish pipeline
# ---------------------------------------------------------------------------


async def _run(niche_id: str, account_label: str, review: bool) -> int:
    """Run the full publish pipeline for a niche from DB."""
    print(f"\n[run_publish] niche_id={niche_id} account={account_label} review={review}")

    # 1. Validate environment
    missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
    if missing:
        print(f"ERROR: missing env vars: {missing}", file=sys.stderr)
        return 1

    # 2. Import runtime dependencies (deferred to avoid import cost in dry-run)
    try:
        from prisma import Prisma  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: prisma not installed. Run: uv add prisma", file=sys.stderr)
        return 1

    try:
        from colorforge_agents.gates.content_gate import ContentGate
        from colorforge_agents.gates.listing_gate import ListingGate
        from colorforge_agents.publisher.publisher_agent import PublisherAgent
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    assets_base = Path(os.getenv("ASSETS_BASE", _ASSETS_BASE_DEFAULT))

    # 3. Connect DB
    prisma = Prisma()
    await prisma.connect()

    try:
        # 4. Fetch account record
        account = await prisma.account.find_first(where={"label": account_label})
        if account is None:
            print(f"ERROR: no account with label={account_label!r}", file=sys.stderr)
            return 1

        # 5. Fetch niche brief
        niche = await prisma.nichebrief.find_unique(where={"id": niche_id})
        if niche is None:
            print(f"ERROR: no NicheBrief with id={niche_id!r}", file=sys.stderr)
            return 1

        # 6. Fetch latest LISTING-state book for this niche
        book = await prisma.book.find_first(
            where={"nicheBriefId": niche_id, "state": "LISTING"},
            order={"updatedAt": "desc"},
        )
        if book is None:
            print(
                f"ERROR: no book in LISTING state for niche_id={niche_id!r}. "
                "Run the generation pipeline first.",
                file=sys.stderr,
            )
            return 1

        print(f"  book_id={book.id} title={getattr(book, 'title', 'unknown')!r}")

        # 7. Human review gate
        if review and not _human_review_gate(niche_id, account_label):
            print("\nPublish aborted by operator.")
            return 0

        # 8. Load contracts from DB JSON fields
        from colorforge_agents.contracts.book_draft import BookDraft
        from colorforge_agents.contracts.book_plan import BookFormat
        from colorforge_agents.contracts.listing import ListingContract
        from colorforge_agents.contracts.validation_report import ValidationReport

        listing = ListingContract.model_validate(book.listingJson)  # type: ignore[attr-defined]
        draft = BookDraft.model_validate(book.draftJson)  # type: ignore[attr-defined]
        report = ValidationReport.model_validate(book.validationJson)  # type: ignore[attr-defined]

        # 9. Publish
        content_gate = ContentGate()
        listing_gate = ListingGate()
        agent = PublisherAgent(content_gate, listing_gate, prisma, assets_base)

        result = await agent.publish(
            listing,
            draft,
            account,
            report,
            book_format=BookFormat(getattr(book, "bookFormat", "PAPERBACK")),
        )

        print(f"\n[SUCCESS] book={result.book_id} asin={result.asin}")
        return 0

    finally:
        await prisma.disconnect()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ColorForge manual publish — soft-launch operator tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--dry-run", action="store_true", help="Validate imports and env, then exit")
    p.add_argument("--account", default="secondary", help="Account label (default: secondary)")
    p.add_argument("--niche-id", metavar="UUID", help="NicheBrief UUID to publish")
    p.add_argument(
        "--review",
        action="store_true",
        default=True,
        help="Pause for human review before KDP submission (default: on)",
    )
    p.add_argument("--no-review", dest="review", action="store_false", help="Skip review gate")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.dry_run:
        _dry_run_check()

    if not args.niche_id:
        print("ERROR: --niche-id UUID is required (or use --dry-run)", file=sys.stderr)
        sys.exit(1)

    sys.exit(asyncio.run(_run(args.niche_id, args.account, args.review)))


if __name__ == "__main__":
    main()
