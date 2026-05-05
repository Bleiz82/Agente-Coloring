"""Google Trends client with Redis cache."""

from __future__ import annotations

import json
from typing import Any, Protocol

from loguru import logger

from colorforge_agents.exceptions import TrendsUnavailable


class RedisClient(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def setex(self, key: str, ttl: int, value: str) -> None: ...


class GoogleTrendsClient:
    """Fetches 90-day trend slope for a keyword via pytrends, cached in Redis."""

    _CACHE_PREFIX = "trends:google:"

    def __init__(self, redis_client: RedisClient, cache_ttl: int = 21_600) -> None:
        self._redis = redis_client
        self._ttl = cache_ttl

    async def get_90d_slope(self, keyword: str) -> float:
        """Return linear regression slope of Google Trends interest over last 90 days.

        Returns 0.0 on any error (graceful degradation per SPEC).
        """
        cache_key = f"{self._CACHE_PREFIX}{keyword}"

        cached = await self._redis.get(cache_key)
        if cached is not None:
            return float(json.loads(cached))

        try:
            slope = await self._fetch_slope(keyword)
        except TrendsUnavailable:
            logger.warning("Google Trends unavailable for '{}', using 0.0", keyword)
            return 0.0
        except Exception as exc:
            logger.warning("Google Trends error for '{}': {}, using 0.0", keyword, exc)
            return 0.0

        await self._redis.setex(cache_key, self._ttl, json.dumps(slope))
        return slope

    async def _fetch_slope(self, keyword: str) -> float:
        """Call pytrends synchronously in a thread, then compute slope."""
        import asyncio

        try:
            slope = await asyncio.get_event_loop().run_in_executor(
                None, self._sync_fetch, keyword
            )
        except Exception as exc:
            raise TrendsUnavailable(str(exc)) from exc
        return slope

    @staticmethod
    def _sync_fetch(keyword: str) -> float:
        """Blocking pytrends call — runs in executor thread."""
        import numpy as np
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
        pytrends.build_payload([keyword], timeframe="today 3-m")
        df: Any = pytrends.interest_over_time()
        if df.empty or keyword not in df.columns:
            return 0.0

        values = df[keyword].values.astype(float)
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values), dtype=float)
        slope = float(np.polyfit(x, values, 1)[0])
        # Normalize roughly to -1..1 range (raw slope units are ~interest-points/week)
        return max(-1.0, min(1.0, slope / 5.0))
