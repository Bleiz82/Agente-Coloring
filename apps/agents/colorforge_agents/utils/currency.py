"""CurrencyService — dynamic exchange rate fetching with Redis cache and drift detection.

K15: replaces hardcoded EUR/GBP rates in pricing_optimizer and royalty_calc.

Features:
- Redis cache with 24h TTL (falls back to in-memory dict if Redis unavailable)
- Drift detection: logs alert when new rate differs >5% from previous
- Fetches from exchangerate-api.com (free tier, no API key required for latest USD rates)
"""

from __future__ import annotations

import json
import time
from typing import Final

import httpx
from loguru import logger

from colorforge_agents.exceptions import CurrencyServiceError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_EXCHANGE_API_URL: Final = "https://api.exchangerate-api.com/v4/latest/USD"
_CACHE_TTL_SECONDS: Final = 86_400  # 24h
_DRIFT_ALERT_THRESHOLD: Final = 0.05  # 5%
_REDIS_KEY: Final = "colorforge:currency:usd_rates"

# Hardcoded fallback rates (used when fetch fails and no cache available)
_FALLBACK_RATES: Final[dict[str, float]] = {
    "EUR": 0.93,
    "GBP": 0.79,
    "CAD": 1.37,
    "AUD": 1.54,
    "JPY": 149.5,
}


class CurrencyService:
    """Fetches and caches USD exchange rates with drift detection.

    Usage:
        svc = CurrencyService()
        rate = await svc.get_rate("EUR")  # e.g. 0.93

    Redis is optional — falls back to in-memory LRU-style dict when unavailable.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._redis: object | None = None
        self._memory_cache: dict[str, tuple[float, float]] = {}  # currency → (rate, fetched_at)
        self._last_rates: dict[str, float] = {}
        self._redis_available = False

        if redis_url:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: str) -> None:
        try:
            import redis as redis_lib
            self._redis = redis_lib.Redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
            self._redis.ping()  # type: ignore[union-attr]
            self._redis_available = True
            logger.debug("CurrencyService: Redis connected at {}", redis_url)
        except Exception as exc:
            logger.warning("CurrencyService: Redis unavailable ({}), using in-memory cache", exc)
            self._redis_available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_rate(self, currency: str) -> float:
        """Return current USD→{currency} exchange rate.

        Checks cache first (Redis or in-memory). On miss, fetches from API.
        Falls back to hardcoded rates if API is unreachable.

        Args:
            currency: ISO 4217 currency code (e.g. "EUR", "GBP").

        Returns:
            Exchange rate as float (e.g. 0.93 means 1 USD = 0.93 EUR).

        Raises:
            CurrencyServiceError: only if currency is completely unknown.
        """
        currency = currency.upper()

        cached = self._read_cache(currency)
        if cached is not None:
            return cached

        rates = await self._fetch_rates()
        if currency not in rates:
            if currency in _FALLBACK_RATES:
                logger.warning("CurrencyService: {} not in API response, using hardcoded fallback", currency)
                return _FALLBACK_RATES[currency]
            raise CurrencyServiceError(f"Unknown currency: {currency!r}")

        return rates[currency]

    async def get_rates(self, currencies: list[str]) -> dict[str, float]:
        """Return rates for multiple currencies in one call."""
        result: dict[str, float] = {}
        for currency in currencies:
            result[currency] = await self.get_rate(currency)
        return result

    def invalidate_cache(self) -> None:
        """Force next get_rate() to re-fetch from API."""
        self._memory_cache.clear()
        if self._redis_available and self._redis is not None:
            try:
                self._redis.delete(_REDIS_KEY)  # type: ignore[union-attr]
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Private: cache
    # ------------------------------------------------------------------

    def _read_cache(self, currency: str) -> float | None:
        now = time.time()

        if self._redis_available and self._redis is not None:
            try:
                raw = self._redis.get(_REDIS_KEY)  # type: ignore[union-attr]
                if raw:
                    data = json.loads(raw)
                    fetched_at = data.get("fetched_at", 0)
                    if now - fetched_at < _CACHE_TTL_SECONDS:
                        rates = data.get("rates", {})
                        if currency in rates:
                            return float(rates[currency])
            except Exception as exc:
                logger.debug("CurrencyService: Redis read failed: {}", exc)

        if currency in self._memory_cache:
            rate, fetched_at = self._memory_cache[currency]
            if now - fetched_at < _CACHE_TTL_SECONDS:
                return rate

        return None

    def _write_cache(self, rates: dict[str, float]) -> None:
        now = time.time()
        payload = json.dumps({"rates": rates, "fetched_at": now})

        if self._redis_available and self._redis is not None:
            try:
                self._redis.setex(_REDIS_KEY, _CACHE_TTL_SECONDS, payload)  # type: ignore[union-attr]
            except Exception as exc:
                logger.debug("CurrencyService: Redis write failed: {}", exc)

        for currency, rate in rates.items():
            self._memory_cache[currency] = (rate, now)

    # ------------------------------------------------------------------
    # Private: fetch
    # ------------------------------------------------------------------

    async def _fetch_rates(self) -> dict[str, float]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(_EXCHANGE_API_URL)
                resp.raise_for_status()
                data = resp.json()
                rates: dict[str, float] = {k: float(v) for k, v in data.get("rates", {}).items()}
        except Exception as exc:
            logger.warning("CurrencyService: API fetch failed ({}), using fallback rates", exc)
            rates = dict(_FALLBACK_RATES)

        self._detect_drift(rates)
        self._write_cache(rates)
        self._last_rates = dict(rates)
        return rates

    def _detect_drift(self, new_rates: dict[str, float]) -> None:
        """Log alert when any rate drifts >5% from last known value."""
        for currency, new_rate in new_rates.items():
            if currency not in self._last_rates:
                continue
            old_rate = self._last_rates[currency]
            if old_rate == 0:
                continue
            drift = abs(new_rate - old_rate) / old_rate
            if drift > _DRIFT_ALERT_THRESHOLD:
                logger.warning(
                    "CurrencyService: {} rate drifted {:.1f}% ({:.4f} -> {:.4f})",
                    currency, drift * 100, old_rate, new_rate,
                )
