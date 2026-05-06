"""Differential Analyzer — compares winners vs losers to extract signals."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from statistics import mean, median, variance
from typing import Any, Literal

from loguru import logger

from colorforge_agents.exceptions import InsufficientSalesData

_MIN_GROUP_SIZE = 3
_NUMERIC_FEATURES = ["page_count", "price_usd", "profitability_score", "days_since_publish"]
_CATEGORICAL_FEATURES = ["niche_category", "style_tag"]


@dataclass
class DifferentialSignal:
    feature_name: str
    winner_value: float | str
    loser_value: float | str
    effect_size: float
    direction: Literal["higher_is_better", "lower_is_better", "categorical"]


@dataclass
class DifferentialReport:
    winners_count: int
    losers_count: int
    signals: list[DifferentialSignal] = field(default_factory=list)
    analysis_date: datetime = field(default_factory=lambda: datetime.now(UTC))


class DifferentialAnalyzer:
    def __init__(self, prisma: Any) -> None:
        self._db = prisma

    async def analyze(self, account_id: str, window_days: int = 30) -> DifferentialReport:
        cutoff = date.today() - timedelta(days=window_days)
        books = await self._db.book.find_many(
            where={"accountId": account_id, "status": "LIVE"},
            include={"niche": True},
        )

        winners: list[dict[str, Any]] = []
        losers: list[dict[str, Any]] = []

        for book in books:
            rows = await self._db.salesdaily.find_many(
                where={"bookId": book.id, "date": {"gte": cutoff}}
            )
            royalty = float(sum(r.royalty for r in rows))

            listing = await self._db.listing.find_first(
                where={"bookId": book.id},
                order={"createdAt": "desc"},
            )

            feature: dict[str, Any] = {
                "page_count": getattr(book, "pageCount", None),
                "price_usd": float(listing.priceUsd) if listing is not None else None,
                "profitability_score": (
                    float(book.niche.profitabilityScore)
                    if book.niche is not None
                    else None
                ),
                "days_since_publish": (date.today() - book.createdAt.date()).days,
                "niche_category": (
                    book.niche.category if book.niche is not None else "unknown"
                ),
                "style_tag": getattr(book, "styleTag", None) or "unknown",
                "_royalty": royalty,
            }

            if royalty >= 50.0:
                winners.append(feature)
            elif royalty < 10.0:
                losers.append(feature)

        logger.info(
            "differential analysis groups",
            account_id=account_id,
            winners=len(winners),
            losers=len(losers),
        )

        if len(winners) < _MIN_GROUP_SIZE or len(losers) < _MIN_GROUP_SIZE:
            raise InsufficientSalesData(
                account_id, _MIN_GROUP_SIZE, min(len(winners), len(losers))
            )

        signals = (
            self._numeric_signals(winners, losers)
            + self._categorical_signals(winners, losers)
        )
        signals.sort(key=lambda s: s.effect_size, reverse=True)

        return DifferentialReport(
            winners_count=len(winners),
            losers_count=len(losers),
            signals=signals,
        )

    def _numeric_signals(
        self,
        winners: list[dict[str, Any]],
        losers: list[dict[str, Any]],
    ) -> list[DifferentialSignal]:
        signals: list[DifferentialSignal] = []
        for feature in _NUMERIC_FEATURES:
            w_vals = [float(w[feature]) for w in winners if w.get(feature) is not None]
            l_vals = [float(lo[feature]) for lo in losers if lo.get(feature) is not None]
            if len(w_vals) < 2 or len(l_vals) < 2:
                continue
            d = self._cohens_d(w_vals, l_vals)
            w_med = median(w_vals)
            l_med = median(l_vals)
            direction: Literal["higher_is_better", "lower_is_better"] = (
                "higher_is_better" if w_med >= l_med else "lower_is_better"
            )
            signals.append(
                DifferentialSignal(
                    feature_name=feature,
                    winner_value=w_med,
                    loser_value=l_med,
                    effect_size=d,
                    direction=direction,
                )
            )
        return signals

    def _categorical_signals(
        self,
        winners: list[dict[str, Any]],
        losers: list[dict[str, Any]],
    ) -> list[DifferentialSignal]:
        signals: list[DifferentialSignal] = []
        for feature in _CATEGORICAL_FEATURES:
            w_vals = [str(w[feature]) for w in winners if w.get(feature) is not None]
            l_vals = [str(lo[feature]) for lo in losers if lo.get(feature) is not None]
            if not w_vals or not l_vals:
                continue
            v = self._cramers_v(w_vals, l_vals)
            w_mode = Counter(w_vals).most_common(1)[0][0]
            l_mode = Counter(l_vals).most_common(1)[0][0]
            signals.append(
                DifferentialSignal(
                    feature_name=feature,
                    winner_value=w_mode,
                    loser_value=l_mode,
                    effect_size=v,
                    direction="categorical",
                )
            )
        return signals

    def _cohens_d(self, a: list[float], b: list[float]) -> float:
        if len(a) < 2 or len(b) < 2:
            return 0.0
        n_a, n_b = len(a), len(b)
        var_a = variance(a)
        var_b = variance(b)
        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
        if pooled_var == 0.0:
            return 0.0
        return abs((mean(a) - mean(b)) / math.sqrt(pooled_var))

    def _cramers_v(self, a: list[str], b: list[str]) -> float:
        categories = list({*a, *b})
        k = len(categories)
        if k <= 1:
            return 0.0
        grand_total = len(a) + len(b)
        if grand_total == 0:
            return 0.0

        cat_index = {c: i for i, c in enumerate(categories)}
        table = [[0] * k for _ in range(2)]
        for val in a:
            table[0][cat_index[val]] += 1
        for val in b:
            table[1][cat_index[val]] += 1

        row_totals = [sum(table[r]) for r in range(2)]
        col_totals = [sum(table[r][c] for r in range(2)) for c in range(k)]

        chi2 = 0.0
        for r in range(2):
            for c in range(k):
                expected = row_totals[r] * col_totals[c] / grand_total
                if expected == 0.0:
                    continue
                chi2 += (table[r][c] - expected) ** 2 / expected

        v = math.sqrt(chi2 / (grand_total * (min(2, k) - 1)))
        return max(0.0, min(1.0, v))
