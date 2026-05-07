"""Tests for expanded K05 trademark blacklist (120+ terms, tier system)."""

from __future__ import annotations

import pytest

from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.exceptions import ListingGateBlocked
from colorforge_agents.gates.listing_gate import (
    ListingGate,
    _TIER_DEALBREAKER,
    _TIER_HIGH_RISK,
    _TIER_MEDIUM_RISK,
    _TIER_REVIEW_REQUIRED,
    _WHITELIST,
)


def _make_clean_listing(**overrides: object) -> ListingContract:
    base = dict(
        book_id="book-test-001",
        title="Ocean Mandala Coloring Book",
        subtitle=None,
        keywords=["mandala", "coloring", "adult", "relaxing", "zen", "patterns", "book"],
        description_html="<b>Beautiful mandala designs for adults.</b>",
        bisac_codes=["ART015000"],
        price_usd=7.99,
        ai_disclosure=True,
    )
    base.update(overrides)
    return ListingContract(**base)  # type: ignore[arg-type]


gate = ListingGate()


# ---------------------------------------------------------------------------
# Tests: tier coverage
# ---------------------------------------------------------------------------


def test_all_tiers_have_terms() -> None:
    assert len(_TIER_DEALBREAKER) >= 15
    assert len(_TIER_HIGH_RISK) >= 30
    assert len(_TIER_MEDIUM_RISK) >= 25
    assert len(_TIER_REVIEW_REQUIRED) >= 20
    total = len(_TIER_DEALBREAKER) + len(_TIER_HIGH_RISK) + len(_TIER_MEDIUM_RISK) + len(_TIER_REVIEW_REQUIRED)
    assert total >= 100, f"Expected >=100 terms, got {total}"


# ---------------------------------------------------------------------------
# Tests: DEALBREAKER terms blocked in title
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("term", sorted(_TIER_DEALBREAKER)[:8])
def test_dealbreaker_in_title_blocked(term: str) -> None:
    listing = _make_clean_listing(title=f"A {term} coloring book")
    with pytest.raises(ListingGateBlocked) as exc_info:
        gate.passes(listing)
    assert "DEALBREAKER" in str(exc_info.value) or any(
        "DEALBREAKER" in c for c in exc_info.value.failed_checks
    )


@pytest.mark.parametrize("term", ["disney", "marvel", "pokemon", "lego", "barbie"])
def test_dealbreaker_in_description_blocked(term: str) -> None:
    listing = _make_clean_listing(description_html=f"<b>Inspired by {term} characters.</b>")
    with pytest.raises(ListingGateBlocked):
        gate.passes(listing)


@pytest.mark.parametrize("term", ["star wars", "peppa pig", "paw patrol", "hello kitty"])
def test_dealbreaker_multi_word_in_keywords_blocked(term: str) -> None:
    kws = ["mandala", "coloring", "adult", "relaxing", "zen", "patterns", term[:50]]
    listing = _make_clean_listing(keywords=kws)
    with pytest.raises(ListingGateBlocked):
        gate.passes(listing)


# ---------------------------------------------------------------------------
# Tests: HIGH_RISK terms blocked
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("term", ["batman", "superman", "minecraft", "roblox", "mario"])
def test_high_risk_in_title_blocked(term: str) -> None:
    listing = _make_clean_listing(title=f"Fun {term} coloring book")
    with pytest.raises(ListingGateBlocked):
        gate.passes(listing)


# ---------------------------------------------------------------------------
# Tests: false positive prevention (word-boundary matching)
# ---------------------------------------------------------------------------


def test_no_false_positive_on_substring() -> None:
    """'bats' should not trigger 'batman' match."""
    listing = _make_clean_listing(title="Bats and Caves Nature Coloring Book")
    result, _ = gate.passes(listing)
    assert result is True


def test_no_false_positive_spider_in_word() -> None:
    """'Spider plant coloring' should not trigger 'spider-man'."""
    listing = _make_clean_listing(title="Spider Plant Garden Coloring Book")
    result, _ = gate.passes(listing)
    assert result is True


def test_no_false_positive_frozen_lake() -> None:
    """'frozen' in 'frozen lake' triggers because 'frozen' is a dealbreaker term."""
    # This IS intentionally blocked — 'frozen' on its own is the Frozen franchise
    listing = _make_clean_listing(title="Frozen Lake Winter Coloring Book")
    with pytest.raises(ListingGateBlocked):
        gate.passes(listing)


def test_no_false_positive_kids_in_compound() -> None:
    """'Kindergarten' does not contain any standalone trademark term."""
    listing = _make_clean_listing(title="Kindergarten Learning Coloring Book")
    result, _ = gate.passes(listing)
    assert result is True


def test_no_false_positive_anime_standalone() -> None:
    """'anime' alone is review_required, not a dealbreaker — gate should block it."""
    listing = _make_clean_listing(title="Anime Style Coloring Book")
    with pytest.raises(ListingGateBlocked) as exc_info:
        gate.passes(listing)
    assert "REVIEW_REQUIRED" in str(exc_info.value.failed_checks)


# ---------------------------------------------------------------------------
# Tests: clean listing passes
# ---------------------------------------------------------------------------


def test_clean_listing_passes() -> None:
    listing = _make_clean_listing()
    result, _ = gate.passes(listing)
    assert result is True


@pytest.mark.parametrize(
    "title",
    [
        "Beautiful Ocean Mandala Coloring Book",
        "Relaxing Geometric Patterns for Adults",
        "Stress Relief Coloring Pages",
        "Nature Inspired Designs Coloring Book",
        "Floral Abstract Art Coloring for Grown-Ups",
    ],
)
def test_safe_titles_pass(title: str) -> None:
    listing = _make_clean_listing(title=title)
    result, _ = gate.passes(listing)
    assert result is True


# ---------------------------------------------------------------------------
# Tests: whitelist (empty by default — verify interface exists)
# ---------------------------------------------------------------------------


def test_whitelist_is_frozenset() -> None:
    assert isinstance(_WHITELIST, frozenset)


# ---------------------------------------------------------------------------
# Tests: case-insensitive matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", ["DISNEY", "Disney", "disney", "DiSnEy"])
def test_case_insensitive_blocking(variant: str) -> None:
    listing = _make_clean_listing(title=f"A {variant} coloring book")
    with pytest.raises(ListingGateBlocked):
        gate.passes(listing)
