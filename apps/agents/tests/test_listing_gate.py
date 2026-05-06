"""Tests for ListingGate — deterministic listing compliance checks."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.exceptions import ListingGateBlocked
from colorforge_agents.gates.listing_gate import ListingGate

gate = ListingGate()

_BOOK_ID = "test-book-001"
_NOW = datetime.now(tz=UTC)


def _valid_listing(**overrides: object) -> ListingContract:
    defaults: dict[str, object] = {
        "book_id": _BOOK_ID,
        "title": "Ocean Mandala Coloring Book for Adults: 75 Relaxing Designs",
        "subtitle": "Stress Relief Coloring with Sea-Themed Patterns",
        "keywords": [
            "ocean coloring book adults",
            "mandala coloring stress relief",
            "sea themed adult coloring",
            "relaxation coloring pages",
            "intricate mandala designs",
            "ocean wave patterns coloring",
            "gift coloring book adults",
        ],
        "description_html": "<b>Beautiful designs for relaxation.</b><br>75 unique pages.",
        "bisac_codes": ["GAM019000", "ART015000"],
        "price_usd": 7.99,
        "price_eur": 7.43,
        "price_gbp": 6.31,
        "ai_disclosure": True,
        "publication_target_date": _NOW,
    }
    defaults.update(overrides)
    return ListingContract(**defaults)  # type: ignore[arg-type]


class TestValidListing:
    def test_valid_listing_passes(self) -> None:
        result, issues = gate.passes(_valid_listing())
        assert result is True
        assert issues == []

    def test_passes_returns_true_tuple(self) -> None:
        ok, issues = gate.passes(_valid_listing())
        assert ok is True
        assert isinstance(issues, list)


class TestTrademarkCheck:
    def test_blocks_disney_in_title(self) -> None:
        listing = _valid_listing(title="Disney Princess Coloring Book for Adults")
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("disney" in c for c in exc_info.value.failed_checks)

    def test_blocks_marvel_in_description(self) -> None:
        listing = _valid_listing(description_html="<b>Marvel heroes coloring!</b>")
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)

    def test_blocks_pokemon_in_keywords(self) -> None:
        kws = ["pokemon coloring book", "pikachu art", "anime coloring", "adult art",
               "relaxation", "zen coloring", "gift idea"]
        listing = _valid_listing(keywords=kws)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("pokemon" in c or "pikachu" in c for c in exc_info.value.failed_checks)

    def test_allows_legitimate_ocean_terms(self) -> None:
        listing = _valid_listing(title="Ocean Wave Patterns — Adult Coloring Book")
        result, _ = gate.passes(listing)
        assert result is True

    def test_case_insensitive_trademark(self) -> None:
        listing = _valid_listing(subtitle="DISNEY-Inspired Fairy Tales")
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)


class TestBestsellerClaimsCheck:
    def test_blocks_number_one_best(self) -> None:
        listing = _valid_listing(title="#1 Best Coloring Book for Adults")
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("bestseller" in c for c in exc_info.value.failed_checks)

    def test_blocks_bestselling(self) -> None:
        listing = _valid_listing(description_html="<b>The bestselling coloring book on Amazon!</b>")
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)

    def test_blocks_award_winning(self) -> None:
        listing = _valid_listing(subtitle="Award-Winning Designs for Relaxation")
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)

    def test_allows_popular_without_superlatives(self) -> None:
        listing = _valid_listing(
            description_html="<b>A crowd-pleasing collection of ocean designs.</b>"
        )
        result, _ = gate.passes(listing)
        assert result is True


class TestLengthCheck:
    def test_blocks_title_over_200(self) -> None:
        # Use model_construct to bypass Pydantic max_length validation
        listing = ListingContract.model_construct(**{
            **_valid_listing().model_dump(),
            "title": "A" * 201,
        })
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("title too long" in c for c in exc_info.value.failed_checks)

    def test_allows_title_exactly_200(self) -> None:
        listing = _valid_listing(title="A" * 200)
        result, _ = gate.passes(listing)
        assert result is True

    def test_blocks_description_over_4000(self) -> None:
        listing = ListingContract.model_construct(**{
            **_valid_listing().model_dump(),
            "description_html": "<b>" + "A" * 4000 + "</b>",
        })
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)


class TestBISACCheck:
    def test_blocks_invalid_bisac_format(self) -> None:
        listing = _valid_listing(bisac_codes=["INVALID"])
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("BISAC" in c for c in exc_info.value.failed_checks)

    def test_allows_valid_bisac(self) -> None:
        listing = _valid_listing(bisac_codes=["GAM019000"])
        result, _ = gate.passes(listing)
        assert result is True

    def test_blocks_lowercase_bisac(self) -> None:
        listing = _valid_listing(bisac_codes=["gam019000"])
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)


class TestPriceCheck:
    def test_blocks_price_below_minimum(self) -> None:
        listing = _valid_listing(price_usd=1.99)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("below minimum" in c for c in exc_info.value.failed_checks)

    def test_blocks_price_above_maximum(self) -> None:
        listing = _valid_listing(price_usd=29.99)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("above maximum" in c for c in exc_info.value.failed_checks)

    def test_allows_boundary_price_min(self) -> None:
        listing = _valid_listing(price_usd=2.99)
        result, _ = gate.passes(listing)
        assert result is True

    def test_allows_boundary_price_max(self) -> None:
        listing = _valid_listing(price_usd=24.99)
        result, _ = gate.passes(listing)
        assert result is True


class TestKeywordsCheck:
    def test_blocks_keyword_over_50_chars(self) -> None:
        long_kw = "a" * 51
        kws = [long_kw, "kw2", "kw3", "kw4", "kw5", "kw6", "kw7"]
        listing = _valid_listing(keywords=kws)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("too long" in c for c in exc_info.value.failed_checks)

    def test_blocks_duplicate_keywords(self) -> None:
        kws = ["ocean coloring", "ocean coloring", "kw3", "kw4", "kw5", "kw6", "kw7"]
        listing = _valid_listing(keywords=kws)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert any("duplicate" in c for c in exc_info.value.failed_checks)

    def test_duplicate_case_insensitive(self) -> None:
        kws = ["Ocean Coloring", "ocean coloring", "kw3", "kw4", "kw5", "kw6", "kw7"]
        listing = _valid_listing(keywords=kws)
        with pytest.raises(ListingGateBlocked):
            gate.passes(listing)


class TestListingGateBlocked:
    def test_exception_carries_book_id(self) -> None:
        listing = _valid_listing(price_usd=0.99)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert exc_info.value.book_id == _BOOK_ID

    def test_exception_carries_failed_checks(self) -> None:
        listing = _valid_listing(price_usd=0.99)
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert len(exc_info.value.failed_checks) >= 1

    def test_multiple_failures_all_reported(self) -> None:
        # Bypass Pydantic validation to construct a listing with multiple violations
        listing = ListingContract.model_construct(**{
            **_valid_listing().model_dump(),
            "price_usd": 0.99,                               # too low
            "title": "Disney Coloring Book " + "A" * 200,   # trademark + too long
        })
        with pytest.raises(ListingGateBlocked) as exc_info:
            gate.passes(listing)
        assert len(exc_info.value.failed_checks) >= 2
