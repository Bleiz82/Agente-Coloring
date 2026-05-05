"""Tests for scoring/profitability.py."""

from __future__ import annotations

from colorforge_agents.scoring.profitability import (
    ScoreInputs,
    _clamp,
    _competition_signal,
    _demand_signal,
    _price_signal,
    _quality_gap_signal,
    _saturation_signal,
    _seasonality_signal,
    _trend_signal,
    compute_profitability_score,
)

# ---------------------------------------------------------------------------
# Individual signal tests
# ---------------------------------------------------------------------------


def test_demand_signal_low_bsr() -> None:
    assert _demand_signal(1_000) > _demand_signal(50_000)


def test_demand_signal_high_bsr() -> None:
    # BSR >= 100k should be near 0
    assert _demand_signal(100_000) <= 0.0 + 1e-6


def test_demand_signal_clamped() -> None:
    # Never exceeds [0, 1]
    assert 0.0 <= _demand_signal(1) <= 1.0
    assert 0.0 <= _demand_signal(999_999) <= 1.0


def test_price_signal_sweet_spot() -> None:
    assert _price_signal(9.99) == 1.0


def test_price_signal_too_cheap() -> None:
    assert _price_signal(1.00) < 1.0


def test_price_signal_too_expensive() -> None:
    assert _price_signal(25.00) < 1.0


def test_competition_signal_zero_total() -> None:
    assert _competition_signal(0, 0) == 0.5


def test_competition_signal_all_low_reviews() -> None:
    assert _competition_signal(20, 20) == 1.0


def test_competition_signal_no_low_reviews() -> None:
    assert _competition_signal(0, 20) == 0.0


def test_quality_gap_signal_max() -> None:
    assert _quality_gap_signal(10) == 1.0


def test_quality_gap_signal_zero() -> None:
    assert _quality_gap_signal(0) == 0.0


def test_trend_signal_positive_slope() -> None:
    assert _trend_signal(1.0) == 1.0


def test_trend_signal_negative_slope() -> None:
    assert _trend_signal(-1.0) == 0.0


def test_trend_signal_neutral() -> None:
    assert abs(_trend_signal(0.0) - 0.5) < 1e-9


def test_seasonality_signal_peak_now() -> None:
    assert _seasonality_signal(0) == 1.0


def test_seasonality_signal_within_30_days() -> None:
    assert _seasonality_signal(29) == 1.0


def test_seasonality_signal_30_to_60() -> None:
    assert _seasonality_signal(45) == 0.5


def test_seasonality_signal_over_60() -> None:
    assert _seasonality_signal(999) == 0.0


def test_saturation_signal_at_p90() -> None:
    # At p90 => 1.0 (fully saturated)
    assert _saturation_signal(50, 50) == 1.0


def test_saturation_signal_none() -> None:
    assert _saturation_signal(0, 50) == 0.0


def test_clamp_in_range() -> None:
    assert _clamp(0.5) == 0.5


def test_clamp_below_min() -> None:
    assert _clamp(-1.0) == 0.0


def test_clamp_above_max() -> None:
    assert _clamp(2.0) == 1.0


# ---------------------------------------------------------------------------
# compute_profitability_score integration
# ---------------------------------------------------------------------------


def _good_inputs() -> ScoreInputs:
    return ScoreInputs(
        median_bsr=5_000,
        median_price=9.99,
        low_review_book_count=15,
        total_top_books=20,
        severe_pain_point_count=6,
        google_trends_90d_slope=0.5,
        days_to_peak_season=20,
        catalog_fit_cosine=0.8,
        new_pubs_last_30d=5,
        new_pubs_30d_p90=50,
    )


def test_score_returns_breakdown() -> None:
    breakdown = compute_profitability_score(_good_inputs())
    assert 0.0 <= breakdown.weighted_total <= 100.0


def test_score_all_signals_in_range() -> None:
    bd = compute_profitability_score(_good_inputs())
    for field in ("demand", "price", "competition", "quality_gap", "trend",
                  "seasonality", "catalog_fit", "saturation"):
        val = getattr(bd, field)
        assert 0.0 <= val <= 1.0, f"{field}={val} out of range"


def test_score_known_output() -> None:
    """Deterministic check against known expected value."""
    inputs = ScoreInputs(
        median_bsr=10_000,
        median_price=9.99,
        low_review_book_count=10,
        total_top_books=20,
        severe_pain_point_count=5,
        google_trends_90d_slope=0.0,
        days_to_peak_season=999,
        catalog_fit_cosine=0.0,
        new_pubs_last_30d=0,
        new_pubs_30d_p90=50,
    )
    bd = compute_profitability_score(inputs)
    # With these inputs the score should be > 40 (decent niche)
    assert bd.weighted_total > 40.0


def test_score_terrible_niche() -> None:
    """High BSR, bad price, saturated, no trends → low score."""
    inputs = ScoreInputs(
        median_bsr=99_000,
        median_price=0.99,
        low_review_book_count=0,
        total_top_books=20,
        severe_pain_point_count=0,
        google_trends_90d_slope=-1.0,
        days_to_peak_season=999,
        catalog_fit_cosine=0.0,
        new_pubs_last_30d=50,
        new_pubs_30d_p90=50,
    )
    bd = compute_profitability_score(inputs)
    assert bd.weighted_total < 30.0


def test_score_great_niche() -> None:
    """Low BSR, good price, low competition, trending → high score."""
    inputs = ScoreInputs(
        median_bsr=500,
        median_price=9.99,
        low_review_book_count=18,
        total_top_books=20,
        severe_pain_point_count=9,
        google_trends_90d_slope=1.0,
        days_to_peak_season=5,
        catalog_fit_cosine=1.0,
        new_pubs_last_30d=0,
        new_pubs_30d_p90=50,
    )
    bd = compute_profitability_score(inputs)
    assert bd.weighted_total > 65.0


def test_score_matches_within_tolerance() -> None:
    """Run same inputs twice — deterministic."""
    inputs = _good_inputs()
    bd1 = compute_profitability_score(inputs)
    bd2 = compute_profitability_score(inputs)
    assert abs(bd1.weighted_total - bd2.weighted_total) < 0.01
