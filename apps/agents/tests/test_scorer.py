"""Tests for SuccessScorer — score computation and classification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from colorforge_agents.monitor.scorer import SuccessScorer


def _make_scorer() -> SuccessScorer:
    return SuccessScorer(prisma=MagicMock())


# ── _calc_score ────────────────────────────────────────────────────────────────

def test_calc_score_winner_full():
    s = _make_scorer()
    score = s._calc_score(units=20, royalty=50.0, kenp=500, refunds=0)
    assert score == 95.0  # 60 + 25 + 10 - 0


def test_calc_score_zero_sales():
    s = _make_scorer()
    assert s._calc_score(0, 0.0, 0, 0) == 0.0


def test_calc_score_clamped_at_max():
    s = _make_scorer()
    score = s._calc_score(units=1000, royalty=1000.0, kenp=10000, refunds=0)
    # max achievable = 60 + 25 + 10 = 95 (each component individually capped)
    assert score == 95.0


def test_calc_score_refund_penalty():
    s = _make_scorer()
    # 60 + 25 + 10 = 95, then -15 from 3 refunds
    score = s._calc_score(units=20, royalty=50.0, kenp=500, refunds=3)
    assert score == 80.0


def test_calc_score_refund_capped_at_15():
    s = _make_scorer()
    score = s._calc_score(units=20, royalty=50.0, kenp=500, refunds=100)
    assert score == 80.0  # penalty capped at 15


def test_calc_score_no_floor_below_zero():
    s = _make_scorer()
    score = s._calc_score(units=0, royalty=0.0, kenp=0, refunds=100)
    assert score == 0.0


# ── _classify ─────────────────────────────────────────────────────────────────

def test_classify_winner():
    assert _make_scorer()._classify(50.0) == "winner"


def test_classify_winner_above():
    assert _make_scorer()._classify(200.0) == "winner"


def test_classify_flat_lower_bound():
    assert _make_scorer()._classify(10.0) == "flat"


def test_classify_flat_upper_bound():
    assert _make_scorer()._classify(49.99) == "flat"


def test_classify_loser():
    assert _make_scorer()._classify(9.99) == "loser"


def test_classify_loser_zero():
    assert _make_scorer()._classify(0.0) == "loser"


# ── _percentile ───────────────────────────────────────────────────────────────

def test_percentile_empty_population():
    assert _make_scorer()._percentile(10.0, []) == 50.0


def test_percentile_top():
    assert _make_scorer()._percentile(10.0, [1.0, 5.0, 10.0]) == 100.0


def test_percentile_bottom():
    assert _make_scorer()._percentile(0.0, [1.0, 5.0, 10.0]) == 0.0


def test_percentile_middle():
    result = _make_scorer()._percentile(5.0, [1.0, 5.0, 10.0])
    assert abs(result - 66.67) < 0.01


# ── compute (async, mocked DB) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_winner():
    prisma = MagicMock()
    sales_rows = [
        MagicMock(unitsSold=10, royalty=30.0, kenpRead=200, refunds=0),
        MagicMock(unitsSold=10, royalty=25.0, kenpRead=300, refunds=0),
    ]
    prisma.salesdaily.find_many = AsyncMock(return_value=sales_rows)
    book = MagicMock(accountId="acc-1", nicheId="niche-1")
    prisma.book.find_unique = AsyncMock(return_value=book)
    prisma.book.find_many = AsyncMock(return_value=[MagicMock(id="book-1")])

    scorer = SuccessScorer(prisma)
    result = await scorer.compute("book-1", 30)

    assert result.royalty_total == 55.0
    assert result.classification == "winner"
    assert result.units_sold == 20
    assert result.kenp_read == 500


@pytest.mark.asyncio
async def test_compute_loser_no_sales():
    prisma = MagicMock()
    prisma.salesdaily.find_many = AsyncMock(return_value=[])
    prisma.book.find_unique = AsyncMock(return_value=MagicMock(accountId="acc-1", nicheId=None))
    prisma.book.find_many = AsyncMock(return_value=[])

    scorer = SuccessScorer(prisma)
    result = await scorer.compute("book-x", 7)

    assert result.royalty_total == 0.0
    assert result.classification == "loser"
    assert result.computed_score == 0.0
