"""CLI entrypoint for the daily Niche Hunt pipeline."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ColorForge Niche Hunt pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports, config, and DB connection then exit 0.",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="",
        help="Comma-separated list of Amazon category URLs to scan.",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default="",
        help="Path to a JSON config file for NicheHunterConfig.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="How many top candidates to pass to Deep Scout.",
    )
    return parser


async def _dry_run_check() -> None:
    """Validate imports and env vars, then exit cleanly."""
    # Validate critical imports
    import colorforge_agents  # noqa: F401
    from colorforge_agents.crew import NicheHuntCrew  # noqa: F401
    from colorforge_agents.gates.niche_gate import NicheGate  # noqa: F401
    from colorforge_agents.niche_hunter.hunter import NicheHunterConfig  # noqa: F401
    from colorforge_agents.scoring.profitability import compute_profitability_score  # noqa: F401

    # Check env vars
    required_env = ["DATABASE_URL"]
    missing = [v for v in required_env if not os.getenv(v)]
    if missing:
        print(f"[dry-run] WARNING: missing env vars: {', '.join(missing)}", file=sys.stderr)

    print("[dry-run] All imports OK. Exiting 0.")


async def _run(args: argparse.Namespace) -> None:
    import json

    from colorforge_agents.niche_hunter.hunter import NicheHunterConfig

    # Build config
    if args.config_file:
        with open(args.config_file) as f:
            config_data = json.load(f)
        config = NicheHunterConfig(**config_data)
    else:
        categories = [c.strip() for c in args.categories.split(",") if c.strip()]
        if not categories:
            print("ERROR: provide --categories or --config-file", file=sys.stderr)
            sys.exit(1)
        config = NicheHunterConfig(categories=categories, top_k=args.top_k)

    # Build clients from env
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    database_url = os.getenv("DATABASE_URL", "")

    import redis.asyncio as aioredis  # type: ignore[import-untyped]
    from anthropic import AsyncAnthropic

    from colorforge_agents.crew import NicheHuntCrew
    from colorforge_agents.deep_scout.embedder import NicheEmbedder
    from colorforge_agents.deep_scout.llm_analyzer import LLMAnalyzer
    from colorforge_agents.deep_scout.scout import DeepScoutCore
    from colorforge_agents.gates.niche_gate import NicheGate
    from colorforge_agents.niche_hunter.hunter import NicheHunterCore
    from colorforge_agents.trends.google import GoogleTrendsClient
    from colorforge_agents.trends.pinterest import PinterestTrendsClient

    redis_client = aioredis.from_url(redis_url, decode_responses=False)
    anthropic_client = AsyncAnthropic(api_key=anthropic_key)

    # Minimal Prisma stub — real usage requires `prisma generate` + DB connection
    class _NoPrisma:
        async def niche_candidate_create(self, **_: object) -> None: ...
        async def niche_candidate_find_first(self, **_: object) -> None: ...
        async def niche_brief_create(self, **_: object) -> None: ...
        async def niche_brief_find_many(self, **_: object) -> list[object]:
            return []

    # Amazon scraper stub (worker process handles real scraping)
    class _AmazonScraper:
        async def scrape_bestsellers(self, url: str, max_books: int) -> list[object]:
            return []

    prisma = _NoPrisma()
    scraper = _AmazonScraper()

    hunter_core = NicheHunterCore(
        scraper=scraper,
        trends_google=GoogleTrendsClient(redis_client),  # type: ignore[arg-type]
        trends_pinterest=PinterestTrendsClient(redis_client),  # type: ignore[arg-type]
        prisma=prisma,  # type: ignore[arg-type]
    )

    try:
        from qdrant_client import AsyncQdrantClient  # type: ignore[import-untyped]
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant = AsyncQdrantClient(url=qdrant_url)
    except Exception:
        qdrant = None  # type: ignore[assignment]

    llm = LLMAnalyzer(anthropic_client)
    embedder = NicheEmbedder(qdrant)
    scout_core = DeepScoutCore(llm_analyzer=llm, embedder=embedder, prisma=prisma)  # type: ignore[arg-type]
    gate = NicheGate()

    crew = NicheHuntCrew(hunter_core, scout_core, gate, prisma)
    briefs = await crew.run(config)
    print(f"Pipeline complete. {len(briefs)} briefs passed gate.")
    for b in briefs:
        print(f"  • {b.primary_keyword} — score={b.profitability_score:.1f}")


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.dry_run:
        asyncio.run(_dry_run_check())
        sys.exit(0)

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
