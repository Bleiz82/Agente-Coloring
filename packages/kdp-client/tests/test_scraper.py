"""Tests for scraper.py -- bestseller extraction and rate limiting."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from colorforge_kdp.exceptions import CaptchaDetected
from colorforge_kdp.scraper import AmazonScraper


def _make_page(captcha: bool = False, items: int = 0) -> MagicMock:
    """Build a mock Playwright Page suitable for AmazonScraper.

    captcha: if True, the captcha form selector returns count > 0.
    items: number of grid items to return (0 = empty page).
    """
    page = AsyncMock()
    page.url = "https://www.amazon.com/Best-Sellers-Books/zgbs/books/1"
    page.goto = AsyncMock()
    page.screenshot = AsyncMock()

    # Build mock grid items
    def _make_item(rank: int) -> MagicMock:
        item = AsyncMock()
        asin = f"B00TEST{rank:04d}"

        def _item_locator(sel: str) -> MagicMock:
            loc = MagicMock()
            first = AsyncMock()
            loc.first = first
            loc.all_inner_texts = AsyncMock(return_value=[str(rank * 100)])

            # Rank text
            first.inner_text = AsyncMock(return_value=f"#{rank}")
            # ASIN link
            first.get_attribute = AsyncMock(
                return_value=f"https://www.amazon.com/dp/{asin}/ref=zg_bs"
            )
            return loc

        item.locator = MagicMock(side_effect=_item_locator)
        return item

    # Captcha locator
    captcha_loc = MagicMock()
    captcha_loc.count = AsyncMock(return_value=1 if captcha else 0)

    # Grid locator
    grid_loc = MagicMock()
    grid_loc.all = AsyncMock(return_value=[_make_item(i + 1) for i in range(items)])

    # Next page locator
    next_loc = MagicMock()
    next_first = AsyncMock()
    next_first.get_attribute = AsyncMock(return_value=None)  # no next page
    next_loc.first = next_first

    def _page_locator(sel: str) -> MagicMock:
        if "validateCaptcha" in sel:
            return captcha_loc
        if "zg-grid" in sel:
            return grid_loc
        if "a-last" in sel:
            return next_loc
        m = MagicMock()
        m.count = AsyncMock(return_value=0)
        m.all = AsyncMock(return_value=[])
        return m

    page.locator = MagicMock(side_effect=_page_locator)
    return page


async def test_scraper_detects_captcha() -> None:
    page = _make_page(captcha=True)
    scraper = AmazonScraper(page)
    with pytest.raises(CaptchaDetected):
        await scraper.scrape_bestsellers(
            "https://amazon.com/zgbs/books/1", max_pages=1
        )


async def test_scraper_rate_limiting_records_page_loads() -> None:
    page = _make_page(captcha=False, items=0)
    scraper = AmazonScraper(page, rate_limit=10)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await scraper.scrape_bestsellers(
            "https://amazon.com/zgbs/books/1", max_pages=1
        )
    assert len(scraper._page_times) == 1


async def test_scraper_empty_page_returns_no_results() -> None:
    page = _make_page(captcha=False, items=0)
    scraper = AmazonScraper(page, rate_limit=200)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        results = await scraper.scrape_bestsellers(
            "https://amazon.com/zgbs/books/1", max_pages=1
        )
    assert results == []


def test_scraper_instantiation() -> None:
    page = MagicMock()
    scraper = AmazonScraper(page, rate_limit=200)
    assert scraper._rate_limit == 200


def test_scraper_default_rate_limit() -> None:
    page = MagicMock()
    scraper = AmazonScraper(page)
    assert scraper._rate_limit == 200


async def test_scraper_page_times_initially_empty() -> None:
    page = MagicMock()
    scraper = AmazonScraper(page)
    assert len(scraper._page_times) == 0
