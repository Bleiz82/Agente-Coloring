"""Niche Hunter core and CrewAI wrapper."""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from loguru import logger
from pydantic import BaseModel, Field

from colorforge_agents.contracts.niche_candidate import (
    CompetitorSnap,
    NicheCandidate,
    TrendSignal,
)
from colorforge_agents.scoring.profitability import ScoreInputs, compute_profitability_score

# ---------------------------------------------------------------------------
# Protocols — injectable dependencies
# ---------------------------------------------------------------------------


class AmazonScraper(Protocol):
    async def scrape_bestsellers(
        self, category_url: str, max_books: int
    ) -> list[dict[str, Any]]: ...


class TrendsClient(Protocol):
    async def get_90d_slope(self, keyword: str) -> float: ...


class PinterestClient(Protocol):
    async def get_search_velocity(self, keyword: str) -> float | None: ...


class PrismaClient(Protocol):
    async def niche_candidate_create(self, *, data: dict[str, Any]) -> Any: ...
    async def niche_candidate_find_first(self, *, where: dict[str, Any]) -> Any: ...


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class NicheHunterConfig(BaseModel):
    categories: list[str] = Field(min_length=1)
    freshness_threshold_hours: int = Field(default=23, ge=1)
    top_k: int = Field(default=5, ge=1)
    max_competitors: int = Field(default=20, ge=1)
    new_pubs_30d_p90: int = Field(default=50, ge=1)


# ---------------------------------------------------------------------------
# Core business logic
# ---------------------------------------------------------------------------


class NicheHunterCore:
    """Pure business logic — no CrewAI. Injected scraper + trends clients."""

    def __init__(
        self,
        scraper: AmazonScraper,
        trends_google: TrendsClient,
        trends_pinterest: PinterestClient,
        prisma: PrismaClient,
    ) -> None:
        self._scraper = scraper
        self._google = trends_google
        self._pinterest = trends_pinterest
        self._prisma = prisma

    async def run(self, config: NicheHunterConfig) -> list[NicheCandidate]:
        """Scan all categories, compute scores, persist, return top-K."""
        candidates: list[NicheCandidate] = []
        run_id = str(uuid.uuid4())

        for category_url in config.categories:
            candidate = await self._scan_category(category_url, config, run_id)
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda c: c.profitability.weighted_total, reverse=True)
        return candidates[: config.top_k]

    async def _scan_category(
        self, category_url: str, config: NicheHunterConfig, run_id: str
    ) -> NicheCandidate | None:
        logger.info("Scanning category: {}", category_url)
        try:
            raw_books = await self._scraper.scrape_bestsellers(
                category_url, config.max_competitors
            )
        except Exception as exc:
            logger.error("Scraper failed for {}: {}", category_url, exc)
            return None

        if not raw_books:
            logger.warning("No books found for {}", category_url)
            return None

        competitors = [c for b in raw_books if (c := self._parse_competitor(b)) is not None]
        if not competitors:
            return None

        primary_keyword = self._extract_keyword(competitors, category_url)
        trend_signals = await self._fetch_trends(primary_keyword)
        profitability = self._compute_score(competitors, trend_signals, config)

        category_path = category_url.rstrip("/").split("/")[-3:]
        candidate = NicheCandidate(
            category_path=category_path or [category_url],
            primary_keyword=primary_keyword,
            top_competitors=competitors,
            profitability=profitability,
            trend_signals=trend_signals,
            scan_timestamp=datetime.now(tz=UTC),
        )

        await self._write_to_db(candidate, run_id)
        return candidate

    def _parse_competitor(self, raw: dict[str, Any]) -> CompetitorSnap | None:
        try:
            return CompetitorSnap(
                asin=str(raw["asin"]),
                title=str(raw.get("title", "")),
                author=str(raw.get("author", "")),
                bsr=int(raw.get("bsr", 1)),
                price=float(raw.get("price", 0.01)),
                review_count=int(raw.get("review_count", 0)),
                rating=float(raw.get("rating", 0.0)),
                publication_date=raw.get("publication_date"),
                page_count=raw.get("page_count"),
            )
        except Exception:
            return None

    @staticmethod
    def _extract_keyword(competitors: list[CompetitorSnap], category_url: str) -> str:
        """Derive the primary keyword from the category slug."""
        slug = category_url.rstrip("/").split("/")[-1]
        return slug.replace("-", " ").replace("_", " ").lower() or competitors[0].title

    async def _fetch_trends(self, keyword: str) -> TrendSignal:
        google_slope = await self._google.get_90d_slope(keyword)
        pinterest_velocity = await self._pinterest.get_search_velocity(keyword)
        return TrendSignal(
            google_trends_90d_slope=google_slope,
            pinterest_search_velocity=pinterest_velocity,
        )

    def _compute_score(
        self,
        competitors: list[CompetitorSnap],
        trends: TrendSignal,
        config: NicheHunterConfig,
    ) -> Any:
        bsrs = [c.bsr for c in competitors if c.bsr > 0]
        prices = [c.price for c in competitors if c.price > 0]
        low_review_count = sum(1 for c in competitors if c.review_count < 50)
        # Approximate pain points from low ratings (books rated <3.5 likely have complaints)
        severe_pain_count = sum(1 for c in competitors if c.rating < 3.5)

        inputs = ScoreInputs(
            median_bsr=int(statistics.median(bsrs)) if bsrs else 100_000,
            median_price=statistics.median(prices) if prices else 9.99,
            low_review_book_count=low_review_count,
            total_top_books=len(competitors),
            severe_pain_point_count=severe_pain_count,
            google_trends_90d_slope=trends.google_trends_90d_slope,
            days_to_peak_season=999,
            catalog_fit_cosine=0.0,
            new_pubs_last_30d=0,
            new_pubs_30d_p90=config.new_pubs_30d_p90,
        )
        return compute_profitability_score(inputs)

    async def _write_to_db(self, candidate: NicheCandidate, run_id: str) -> str:
        record_id = str(uuid.uuid4())
        try:
            await self._prisma.niche_candidate_create(
                data={
                    "id": record_id,
                    "runId": run_id,
                    "primaryKeyword": candidate.primary_keyword,
                    "categoryPath": candidate.category_path,
                    "profitabilityScore": candidate.profitability.weighted_total,
                    "profitabilityBreakdown": candidate.profitability.model_dump(),
                    "trendSignals": candidate.trend_signals.model_dump(),
                    "competitorCount": len(candidate.top_competitors),
                    "scannedAt": candidate.scan_timestamp.isoformat(),
                }
            )
            logger.info(
                "Persisted NicheCandidate {} for '{}'", record_id, candidate.primary_keyword
            )
        except Exception as exc:
            logger.error("DB write failed for '{}': {}", candidate.primary_keyword, exc)
        return record_id


# ---------------------------------------------------------------------------
# CrewAI wrapper
# ---------------------------------------------------------------------------


class NicheHunterAgent:
    """Thin CrewAI wrapper around NicheHunterCore."""

    def __init__(self, core: NicheHunterCore) -> None:
        self._core = core

    def as_crewai_agent(self) -> Any:
        try:
            from crewai import Agent
        except ImportError as exc:
            raise ImportError("crewai is required for NicheHunterAgent.as_crewai_agent()") from exc
        return Agent(
            role="Niche Hunter",
            goal=(
                "Scan Amazon KDP bestseller categories, compute profitability scores for each "
                "niche, and return the top-K NicheCandidate records ranked by score."
            ),
            backstory=(
                "Expert Amazon KDP market analyst with deep knowledge of coloring book niches, "
                "BSR trends, and competitive dynamics."
            ),
            allow_delegation=False,
            verbose=True,
        )

    def as_crewai_task(self, config: NicheHunterConfig) -> Any:
        try:
            from crewai import Task
        except ImportError as exc:
            raise ImportError("crewai is required for NicheHunterAgent.as_crewai_task()") from exc

        async def _run() -> list[NicheCandidate]:
            return await self._core.run(config)

        return Task(
            description=(
                f"Hunt niches for categories: {config.categories}. "
                f"Return top-{config.top_k} candidates by profitability score."
            ),
            expected_output="List of NicheCandidate records as JSON",
            agent=self.as_crewai_agent(),
        )
