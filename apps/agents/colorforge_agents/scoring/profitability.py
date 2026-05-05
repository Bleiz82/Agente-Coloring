"""8-signal Profitability Score formula."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from colorforge_agents.contracts.niche_candidate import ProfitabilityBreakdown

# Signal weights — must sum to 1.0
_W_DEMAND: float = 0.20
_W_PRICE: float = 0.15
_W_COMPETITION: float = 0.20  # NEGATIVE
_W_QUALITY_GAP: float = 0.15
_W_TREND: float = 0.10
_W_SEASONALITY: float = 0.05
_W_CATALOG_FIT: float = 0.10
_W_SATURATION: float = 0.05  # NEGATIVE


class ScoreInputs(BaseModel):
    """Raw inputs for the profitability score engine."""

    median_bsr: int = Field(gt=0)
    median_price: float = Field(gt=0)
    low_review_book_count: int = Field(ge=0)
    total_top_books: int = Field(ge=1)
    severe_pain_point_count: int = Field(ge=0)
    google_trends_90d_slope: float
    days_to_peak_season: int = Field(ge=0)
    catalog_fit_cosine: float = Field(ge=0.0, le=1.0, default=0.0)
    new_pubs_last_30d: int = Field(ge=0)
    new_pubs_30d_p90: int = Field(ge=1)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _demand_signal(median_bsr: int) -> float:
    """Inverse BSR normalized against 100k ceiling. BSR 1 → 1.0, BSR 100k+ → ~0."""
    return _clamp(1.0 - math.log10(median_bsr) / math.log10(100_000))


def _price_signal(median_price: float) -> float:
    """Normalize price to $4–$15 sweet spot. Outside → lower score."""
    lo, hi = 4.0, 15.0
    if median_price < lo:
        return _clamp(median_price / lo)
    if median_price > hi:
        return _clamp(1.0 - (median_price - hi) / hi)
    return 1.0


def _competition_signal(low_review_count: int, total_books: int) -> float:
    """Fraction of top books with <50 reviews (lower competition → higher signal)."""
    if total_books == 0:
        return 0.5
    return _clamp(low_review_count / total_books)


def _quality_gap_signal(severe_pain_count: int) -> float:
    """More pain points in competitors → larger gap to exploit. Normalized 0–10."""
    return _clamp(severe_pain_count / 10.0)


def _trend_signal(slope: float) -> float:
    """Map slope from -1..1 range to 0..1."""
    return _clamp((slope + 1.0) / 2.0)


def _seasonality_signal(days_to_peak: int) -> float:
    """1.0 if peak ≤30 days, 0.5 if 30–60 days, 0.0 if >60 days."""
    if days_to_peak <= 30:
        return 1.0
    if days_to_peak <= 60:
        return 0.5
    return 0.0


def _saturation_signal(new_pubs_30d: int, new_pubs_30d_p90: int) -> float:
    """High new-pub velocity relative to p90 → higher saturation (negative signal)."""
    return _clamp(new_pubs_30d / new_pubs_30d_p90)


def compute_profitability_score(inputs: ScoreInputs) -> ProfitabilityBreakdown:
    """Compute the 8-signal profitability score from raw inputs."""
    demand = _demand_signal(inputs.median_bsr)
    price = _price_signal(inputs.median_price)
    competition = _competition_signal(inputs.low_review_book_count, inputs.total_top_books)
    quality_gap = _quality_gap_signal(inputs.severe_pain_point_count)
    trend = _trend_signal(inputs.google_trends_90d_slope)
    seasonality = _seasonality_signal(inputs.days_to_peak_season)
    catalog_fit = _clamp(inputs.catalog_fit_cosine)
    saturation = _saturation_signal(inputs.new_pubs_last_30d, inputs.new_pubs_30d_p90)

    # Competition and saturation are negative signals (lower is better for publisher)
    weighted_total = (
        _W_DEMAND * demand
        + _W_PRICE * price
        + _W_COMPETITION * (1.0 - competition)
        + _W_QUALITY_GAP * quality_gap
        + _W_TREND * trend
        + _W_SEASONALITY * seasonality
        + _W_CATALOG_FIT * catalog_fit
        + _W_SATURATION * (1.0 - saturation)
    ) * 100.0

    return ProfitabilityBreakdown(
        demand=demand,
        price=price,
        competition=competition,
        quality_gap=quality_gap,
        trend=trend,
        seasonality=seasonality,
        catalog_fit=catalog_fit,
        saturation=saturation,
        weighted_total=_clamp(weighted_total, 0.0, 100.0),
    )
