"""Tests for niche_hunter/hunter.py."""

from __future__ import annotations

from typing import Any

import pytest

from colorforge_agents.niche_hunter.hunter import NicheHunterConfig, NicheHunterCore

# ---------------------------------------------------------------------------
# Mock dependencies
# ---------------------------------------------------------------------------


class _MockScraper:
    def __init__(self, books: list[dict[str, Any]]) -> None:
        self._books = books

    async def scrape_bestsellers(self, _url: str, max_books: int) -> list[dict[str, Any]]:
        return self._books[:max_books]


class _MockGoogleTrends:
    def __init__(self, slope: float = 0.3) -> None:
        self._slope = slope

    async def get_90d_slope(self, _keyword: str) -> float:
        return self._slope


class _MockPinterestTrends:
    def __init__(self, velocity: float | None = 55.0) -> None:
        self._velocity = velocity

    async def get_search_velocity(self, _keyword: str) -> float | None:
        return self._velocity


class _MockPrisma:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def niche_candidate_create(self, *, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(data)
        return data

    async def niche_candidate_find_first(self, **_: Any) -> None:
        return None


def _sample_books(n: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "asin": f"B0ASIN{i:04d}",
            "title": f"Book {i}",
            "author": f"Author {i}",
            "bsr": 10_000 + i * 1_000,
            "price": 9.99,
            "review_count": 20 + i * 10,
            "rating": 3.8 + i * 0.1,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hunter_returns_candidates_for_each_category() -> None:
    scraper = _MockScraper(_sample_books(5))
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(),
        prisma=prisma,
    )
    config = NicheHunterConfig(
        categories=[
            "https://amazon.com/books/mandala-coloring",
            "https://amazon.com/books/animal-coloring",
        ],
        top_k=5,
    )
    candidates = await core.run(config)
    assert len(candidates) == 2


@pytest.mark.asyncio
async def test_hunter_returns_top_k_sorted_by_score() -> None:
    scraper = _MockScraper(_sample_books(5))
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(),
        prisma=prisma,
    )
    config = NicheHunterConfig(
        categories=[
            "https://amazon.com/books/cat-a",
            "https://amazon.com/books/cat-b",
            "https://amazon.com/books/cat-c",
        ],
        top_k=2,
    )
    candidates = await core.run(config)
    assert len(candidates) <= 2
    # Verify sorted descending
    scores = [c.profitability.weighted_total for c in candidates]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_hunter_writes_to_db_for_each_candidate() -> None:
    scraper = _MockScraper(_sample_books(3))
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(),
        prisma=prisma,
    )
    config = NicheHunterConfig(
        categories=["https://amazon.com/books/mandala"],
        top_k=5,
    )
    await core.run(config)
    assert len(prisma.created) == 1
    record = prisma.created[0]
    assert "primaryKeyword" in record
    assert "profitabilityScore" in record


@pytest.mark.asyncio
async def test_hunter_skips_category_on_scraper_error() -> None:
    class _FailingScraper:
        async def scrape_bestsellers(self, _url: str, _max_books: int) -> list[Any]:
            raise RuntimeError("Network error")

    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=_FailingScraper(),
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(),
        prisma=prisma,
    )
    config = NicheHunterConfig(categories=["https://amazon.com/fail"], top_k=5)
    candidates = await core.run(config)
    assert candidates == []


@pytest.mark.asyncio
async def test_hunter_skips_empty_category() -> None:
    scraper = _MockScraper([])
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(),
        prisma=prisma,
    )
    config = NicheHunterConfig(categories=["https://amazon.com/empty"], top_k=5)
    candidates = await core.run(config)
    assert candidates == []


@pytest.mark.asyncio
async def test_hunter_candidate_has_correct_trend_signals() -> None:
    scraper = _MockScraper(_sample_books(3))
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(slope=0.7),
        trends_pinterest=_MockPinterestTrends(velocity=42.0),
        prisma=prisma,
    )
    config = NicheHunterConfig(categories=["https://amazon.com/books/test-niche"], top_k=5)
    candidates = await core.run(config)
    assert len(candidates) == 1
    signals = candidates[0].trend_signals
    assert signals.google_trends_90d_slope == 0.7
    assert signals.pinterest_search_velocity == 42.0


@pytest.mark.asyncio
async def test_hunter_pinterest_none_allowed() -> None:
    scraper = _MockScraper(_sample_books(3))
    prisma = _MockPrisma()
    core = NicheHunterCore(
        scraper=scraper,
        trends_google=_MockGoogleTrends(),
        trends_pinterest=_MockPinterestTrends(velocity=None),
        prisma=prisma,
    )
    config = NicheHunterConfig(categories=["https://amazon.com/books/no-pinterest"], top_k=5)
    candidates = await core.run(config)
    assert candidates[0].trend_signals.pinterest_search_velocity is None
