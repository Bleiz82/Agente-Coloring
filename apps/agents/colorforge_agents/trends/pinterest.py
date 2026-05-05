"""Pinterest Trends client with Redis cache."""

from __future__ import annotations

import json
import re
from typing import Protocol

import httpx
from loguru import logger


class RedisClient(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def setex(self, key: str, ttl: int, value: str) -> None: ...


class PinterestTrendsClient:
    """Scrapes trends.pinterest.com for monthly search velocity, cached in Redis."""

    _CACHE_PREFIX = "trends:pinterest:"
    _BASE_URL = "https://trends.pinterest.com/explore/"

    def __init__(self, redis_client: RedisClient, cache_ttl: int = 21_600) -> None:
        self._redis = redis_client
        self._ttl = cache_ttl

    async def get_search_velocity(self, keyword: str) -> float | None:
        """Return relative monthly search velocity (0-100) or None on failure."""
        cache_key = f"{self._CACHE_PREFIX}{keyword}"

        cached = await self._redis.get(cache_key)
        if cached is not None:
            value = json.loads(cached)
            return float(value) if value is not None else None

        velocity = await self._fetch_velocity(keyword)

        await self._redis.setex(cache_key, self._ttl, json.dumps(velocity))
        return velocity

    async def _fetch_velocity(self, keyword: str) -> float | None:
        slug = keyword.replace(" ", "-").lower()
        url = f"{self._BASE_URL}{slug}"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; colorforge/1.0)"},
                )
                if response.status_code != 200:
                    logger.debug(
                        "Pinterest Trends returned {} for '{}'", response.status_code, keyword
                    )
                    return None
                return self._parse_velocity(response.text)
        except Exception as exc:
            logger.debug("Pinterest Trends fetch failed for '{}': {}", keyword, exc)
            return None

    @staticmethod
    def _parse_velocity(html: str) -> float | None:
        """Extract the trend score from Pinterest page JSON blob."""
        # Pinterest embeds trend data as: "trendingScore":{"value":72}
        match = re.search(r'"trendingScore"\s*:\s*\{"value"\s*:\s*(\d+(?:\.\d+)?)\}', html)
        if match:
            return float(match.group(1))
        # Fallback: look for monthly volume indicator
        match = re.search(r'"monthlyVolume"\s*:\s*(\d+(?:\.\d+)?)', html)
        if match:
            raw = float(match.group(1))
            return min(100.0, raw / 1_000_000 * 100.0)
        return None
