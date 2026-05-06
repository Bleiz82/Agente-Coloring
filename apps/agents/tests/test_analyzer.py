"""Tests for DifferentialAnalyzer — statistical signal extraction."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from colorforge_agents.exceptions import InsufficientSalesData
from colorforge_agents.monitor.analyzer import DifferentialAnalyzer


def _make_analyzer() -> DifferentialAnalyzer:
    return DifferentialAnalyzer(prisma=MagicMock())


# ── _cohens_d ─────────────────────────────────────────────────────────────────

def test_cohens_d_identical_groups():
    d = _make_analyzer()._cohens_d([10.0, 10.0, 10.0], [10.0, 10.0, 10.0])
    assert d == 0.0


def test_cohens_d_clear_separation():
    d = _make_analyzer()._cohens_d([10.0, 11.0, 12.0], [1.0, 2.0, 3.0])
    assert d > 1.0


def test_cohens_d_is_absolute():
    a = _make_analyzer()._cohens_d([1.0, 2.0, 3.0], [10.0, 11.0, 12.0])
    b = _make_analyzer()._cohens_d([10.0, 11.0, 12.0], [1.0, 2.0, 3.0])
    assert abs(a - b) < 1e-9


def test_cohens_d_too_few_samples():
    assert _make_analyzer()._cohens_d([5.0], [5.0]) == 0.0


def test_cohens_d_zero_variance():
    d = _make_analyzer()._cohens_d([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
    assert d == 0.0


# ── _cramers_v ────────────────────────────────────────────────────────────────

def test_cramers_v_single_category():
    v = _make_analyzer()._cramers_v(["A", "A", "A"], ["A", "A", "A"])
    assert v == 0.0


def test_cramers_v_perfect_separation():
    v = _make_analyzer()._cramers_v(["A", "A", "A"], ["B", "B", "B"])
    assert abs(v - 1.0) < 1e-9


def test_cramers_v_between_zero_and_one():
    v = _make_analyzer()._cramers_v(["A", "A", "B"], ["A", "B", "B"])
    assert 0.0 <= v <= 1.0


def test_cramers_v_empty():
    v = _make_analyzer()._cramers_v([], [])
    assert v == 0.0


# ── analyze (async, mocked DB) ────────────────────────────────────────────────

def _make_book(book_id: str, niche_cat: str = "floral", style: str = "detailed") -> MagicMock:
    book = MagicMock()
    book.id = book_id
    book.pageCount = 50
    book.styleTag = style
    book.createdAt = MagicMock()
    book.createdAt.date.return_value = __import__("datetime").date(2026, 1, 1)
    book.niche = MagicMock()
    book.niche.category = niche_cat
    book.niche.profitabilityScore = 70.0
    return book


@pytest.mark.asyncio
async def test_analyze_insufficient_data_raises():
    prisma = MagicMock()
    prisma.book.find_many = AsyncMock(return_value=[_make_book("b1"), _make_book("b2")])
    # All books have tiny royalties → all losers, no winners
    prisma.salesdaily.find_many = AsyncMock(return_value=[MagicMock(royalty=1.0)])
    prisma.listing.find_first = AsyncMock(return_value=MagicMock(priceUsd=7.99))

    analyzer = DifferentialAnalyzer(prisma)
    with pytest.raises(InsufficientSalesData):
        await analyzer.analyze("acc-1", window_days=30)


@pytest.mark.asyncio
async def test_analyze_returns_report_with_signals():
    prisma = MagicMock()

    winner_books = [_make_book(f"w{i}", "mandala") for i in range(4)]
    loser_books = [_make_book(f"l{i}", "floral") for i in range(4)]
    all_books = winner_books + loser_books

    prisma.book.find_many = AsyncMock(return_value=all_books)

    async def fake_sales(where: dict) -> list[MagicMock]:  # type: ignore[type-arg]
        book_id: str = where["bookId"]
        if book_id.startswith("w"):
            return [MagicMock(royalty=60.0)]
        return [MagicMock(royalty=5.0)]

    prisma.salesdaily.find_many = AsyncMock(side_effect=fake_sales)
    prisma.listing.find_first = AsyncMock(return_value=MagicMock(priceUsd=9.99))

    analyzer = DifferentialAnalyzer(prisma)
    report = await analyzer.analyze("acc-1", window_days=30)

    assert report.winners_count == 4
    assert report.losers_count == 4
    assert len(report.signals) > 0
    # signals sorted by effect_size descending
    effect_sizes = [s.effect_size for s in report.signals]
    assert effect_sizes == sorted(effect_sizes, reverse=True)
