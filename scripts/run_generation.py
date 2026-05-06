"""CLI entrypoint for the Generator pipeline.

Usage:
    python scripts/run_generation.py --dry-run
    python scripts/run_generation.py --book-plan-id <uuid>
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _dry_run_check() -> None:
    """Validate imports, env vars, and config — then exit 0."""
    errors: list[str] = []

    # Required imports
    try:
        import colorforge_agents.generator.generator  # noqa: F401
        import colorforge_agents.generator.image_gen  # noqa: F401
        import colorforge_agents.generator.pdf_assembler  # noqa: F401
        import colorforge_agents.generator.post_processor  # noqa: F401
        import colorforge_agents.critic.critic  # noqa: F401
        import colorforge_agents.critic.vision_checker  # noqa: F401
        import colorforge_agents.gates.content_gate  # noqa: F401
        import colorforge_agents.strategist.strategist  # noqa: F401
    except ImportError as exc:
        errors.append(f"Import error: {exc}")

    # Required env vars
    for var in ["DATABASE_URL", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
        if not os.getenv(var):
            errors.append(f"Missing env var: {var}")

    # Assets base directory
    assets_base = os.getenv("ASSETS_BASE", "/var/colorforge/assets")
    print(f"[dry-run] Assets base: {assets_base}")

    if errors:
        for e in errors:
            print(f"[dry-run] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("[dry-run] All imports OK. Exiting 0.")
    sys.exit(0)


async def _run(plan_id: str) -> None:
    """Run the full Generator pipeline for an existing BookPlan in DB."""
    import asyncio  # noqa: F401 — for type checker
    from colorforge_agents.generator.generator import GeneratorCore
    from colorforge_agents.generator.image_gen import GeminiImageClient
    from colorforge_agents.generator.pdf_assembler import PDFAssembler
    from colorforge_agents.generator.post_processor import ImagePostProcessor

    gemini_key = os.environ["GEMINI_API_KEY"]
    assets_base = Path(os.getenv("ASSETS_BASE", "/var/colorforge/assets"))
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-image-generation")

    image_client = GeminiImageClient(api_key=gemini_key, model=gemini_model)
    post_processor = ImagePostProcessor()
    pdf_assembler = PDFAssembler()

    # Prisma client (real connection)
    from prisma import Prisma  # type: ignore[import]

    prisma = Prisma()
    await prisma.connect()

    core = GeneratorCore(
        image_client=image_client,
        post_processor=post_processor,
        pdf_assembler=pdf_assembler,
        prisma=prisma,
        assets_base=assets_base,
    )

    # Load BookPlan from DB
    # (Full Prisma schema in M5 — placeholder for now)
    raise NotImplementedError(
        f"DB-backed BookPlan loading not yet implemented (plan_id={plan_id}). "
        "Use --dry-run to validate imports."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ColorForge Generator pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Validate imports and config, then exit")
    parser.add_argument("--book-plan-id", metavar="UUID", help="BookPlan ID to generate")
    args = parser.parse_args()

    if args.dry_run:
        _dry_run_check()

    if not args.book_plan_id:
        parser.error("Provide --book-plan-id UUID or --dry-run")

    import asyncio

    asyncio.run(_run(args.book_plan_id))


if __name__ == "__main__":
    main()
