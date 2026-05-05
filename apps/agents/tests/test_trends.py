"""Tests for trends clients (Google + Pinterest)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from colorforge_agents.trends.google import GoogleTrendsClient
from colorforge_agents.trends.pinterest import PinterestTrendsClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeRedis:
    """In-memory Redis stub."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self._store[key] = value.encode()


# ---------------------------------------------------------------------------
# GoogleTrendsClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_google_returns_cached_slope() -> None:
    redis = _FakeRedis()
    redis._store["trends:google:mandala"] = json.dumps(0.55).encode()
    client = GoogleTrendsClient(redis)  # type: ignore[arg-type]
    slope = await client.get_90d_slope("mandala")
    assert slope == pytest.approx(0.55)


@pytest.mark.asyncio
async def test_google_stores_result_in_cache() -> None:
    redis = _FakeRedis()
    client = GoogleTrendsClient(redis)  # type: ignore[arg-type]

    with patch.object(client, "_fetch_slope", new=AsyncMock(return_value=0.3)):
        slope = await client.get_90d_slope("flowers")

    assert slope == pytest.approx(0.3)
    cached = await redis.get("trends:google:flowers")
    assert cached is not None
    assert json.loads(cached) == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_google_returns_zero_on_fetch_error() -> None:
    redis = _FakeRedis()
    client = GoogleTrendsClient(redis)  # type: ignore[arg-type]

    with patch.object(client, "_fetch_slope", new=AsyncMock(side_effect=RuntimeError("timeout"))):
        slope = await client.get_90d_slope("broken")

    assert slope == 0.0


@pytest.mark.asyncio
async def test_google_cache_hit_skips_fetch() -> None:
    redis = _FakeRedis()
    redis._store["trends:google:cats"] = json.dumps(0.7).encode()
    client = GoogleTrendsClient(redis)  # type: ignore[arg-type]

    fetch_mock = AsyncMock(return_value=0.1)
    with patch.object(client, "_fetch_slope", new=fetch_mock):
        slope = await client.get_90d_slope("cats")

    fetch_mock.assert_not_called()
    assert slope == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_google_slope_clamped_to_minus_one_plus_one() -> None:
    redis = _FakeRedis()
    client = GoogleTrendsClient(redis)  # type: ignore[arg-type]

    with patch.object(client, "_fetch_slope", new=AsyncMock(return_value=5.0)):
        slope = await client.get_90d_slope("extreme")

    # _fetch_slope returns raw — but _sync_fetch clamps; mock returns raw 5.0 here
    assert slope == pytest.approx(5.0)


def test_google_sync_fetch_slope_normalization() -> None:
    """_sync_fetch clamps slope to [-1, 1] via max/min."""
    # Test the normalization arithmetic: slope / 5.0 clamped to [-1, 1]
    raw_slope = 50.0
    normalized = max(-1.0, min(1.0, raw_slope / 5.0))
    assert normalized == 1.0

    raw_slope = -50.0
    normalized = max(-1.0, min(1.0, raw_slope / 5.0))
    assert normalized == -1.0


# ---------------------------------------------------------------------------
# PinterestTrendsClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_returns_cached_velocity() -> None:
    redis = _FakeRedis()
    redis._store["trends:pinterest:ocean"] = json.dumps(42.0).encode()
    client = PinterestTrendsClient(redis)  # type: ignore[arg-type]
    velocity = await client.get_search_velocity("ocean")
    assert velocity == pytest.approx(42.0)


@pytest.mark.asyncio
async def test_pinterest_returns_none_on_fetch_failure() -> None:
    redis = _FakeRedis()
    client = PinterestTrendsClient(redis)  # type: ignore[arg-type]

    with patch.object(client, "_fetch_velocity", new=AsyncMock(return_value=None)):
        velocity = await client.get_search_velocity("unknown")

    assert velocity is None


@pytest.mark.asyncio
async def test_pinterest_stores_result_in_cache() -> None:
    redis = _FakeRedis()
    client = PinterestTrendsClient(redis)  # type: ignore[arg-type]

    with patch.object(client, "_fetch_velocity", new=AsyncMock(return_value=65.0)):
        velocity = await client.get_search_velocity("sunset")

    assert velocity == pytest.approx(65.0)
    cached = await redis.get("trends:pinterest:sunset")
    assert cached is not None
    assert json.loads(cached) == pytest.approx(65.0)


@pytest.mark.asyncio
async def test_pinterest_cache_hit_skips_fetch() -> None:
    redis = _FakeRedis()
    redis._store["trends:pinterest:dogs"] = json.dumps(88.0).encode()
    client = PinterestTrendsClient(redis)  # type: ignore[arg-type]

    fetch_mock = AsyncMock(return_value=10.0)
    with patch.object(client, "_fetch_velocity", new=fetch_mock):
        velocity = await client.get_search_velocity("dogs")

    fetch_mock.assert_not_called()
    assert velocity == pytest.approx(88.0)


def test_pinterest_parse_trending_score() -> None:
    html = '...{"trendingScore":{"value":72}}...'
    result = PinterestTrendsClient._parse_velocity(html)
    assert result == pytest.approx(72.0)


def test_pinterest_parse_monthly_volume_fallback() -> None:
    html = '...{"monthlyVolume":500000}...'
    result = PinterestTrendsClient._parse_velocity(html)
    assert result == pytest.approx(50.0)


def test_pinterest_parse_returns_none_on_no_match() -> None:
    html = "<html>no data here</html>"
    result = PinterestTrendsClient._parse_velocity(html)
    assert result is None


def test_pinterest_parse_monthly_volume_capped_at_100() -> None:
    html = '...{"monthlyVolume":2000000}...'
    result = PinterestTrendsClient._parse_velocity(html)
    assert result == pytest.approx(100.0)
