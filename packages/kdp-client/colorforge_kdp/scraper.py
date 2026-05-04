"""Amazon Bestsellers scraper with rate limiting and human-like delays.

Extracts CompetitorSnap records from Amazon bestseller pages.
All CSS selectors are placeholders marked # VERIFY_SELECTOR.
"""

from __future__ import annotations

import asyncio
import random
import re
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from loguru import logger
from playwright.async_api import Locator, Page

from colorforge_kdp.exceptions import CaptchaDetected
from colorforge_kdp.types import CompetitorSnap

# ---------------------------------------------------------------------------
# Selectors — all must be verified against live Amazon UI
# ---------------------------------------------------------------------------


class _Sel:
    # Captcha detection
    CAPTCHA_FORM = "form[action='/errors/validateCaptcha']"  # VERIFY_SELECTOR

    # Bestseller grid item
    GRID_ITEM = "div.zg-grid-general-faceout"  # VERIFY_SELECTOR
    RANK_TEXT = "span.zg-bdg-text"  # VERIFY_SELECTOR (within item)
    TITLE = "div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1"  # VERIFY_SELECTOR (within item)
    AUTHOR = "a.a-size-small.a-link-child"  # VERIFY_SELECTOR (within item)
    PRICE = "span.a-price > span.a-offscreen"  # VERIFY_SELECTOR (within item)
    REVIEW_COUNT = "span.a-size-small"  # VERIFY_SELECTOR (within item)
    COVER_IMG = "img.a-dynamic-image"  # VERIFY_SELECTOR (within item)
    ITEM_LINK = "a.a-link-normal"  # VERIFY_SELECTOR (within item)

    # Pagination
    NEXT_PAGE = "li.a-last a"  # VERIFY_SELECTOR


_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")
_PRICE_RE = re.compile(r"[\d.,]+")


class AmazonScraper:
    """Scrapes Amazon bestseller pages for competitor data.

    Rate limit: max `rate_limit` pages per hour per proxy IP.
    Human-like delays between pages.
    """

    def __init__(self, page: Page, rate_limit: int = 200) -> None:
        self._page = page
        self._rate_limit = rate_limit
        # Sliding window: timestamps of recent page loads
        self._page_times: deque[datetime] = deque()

    async def scrape_bestsellers(
        self, category_url: str, max_pages: int = 5
    ) -> list[CompetitorSnap]:
        """Scrape up to max_pages of bestseller results for category_url.

        Returns a deduplicated list of CompetitorSnap sorted by rank ascending.
        """
        results: list[CompetitorSnap] = []
        seen_asins: set[str] = set()
        url: str | None = category_url

        for page_num in range(1, max_pages + 1):
            if url is None:
                break
            await self._rate_check()
            logger.info("scraping bestsellers page={} url={}", page_num, url)
            await self._page.goto(url, wait_until="domcontentloaded")
            await self._detect_captcha()
            self._record_page_load()

            snaps = await self._extract_page()
            for snap in snaps:
                if snap.asin not in seen_asins:
                    seen_asins.add(snap.asin)
                    results.append(snap)

            url = await self._next_page_url()
            await asyncio.sleep(random.uniform(2.0, 5.0))

        results.sort(key=lambda s: s.rank)
        logger.info("scraped {} competitors from {}", len(results), category_url)
        return results

    async def _extract_page(self) -> list[CompetitorSnap]:
        snaps: list[CompetitorSnap] = []
        items = await self._page.locator(_Sel.GRID_ITEM).all()
        for item in items:
            try:
                snap = await self._extract_item(item)
                snaps.append(snap)
            except Exception as exc:  # noqa: BLE001
                logger.debug("skipping item due to extraction error: {}", exc)
        return snaps

    async def _extract_item(self, item: Locator) -> CompetitorSnap:
        # Rank
        rank_text = await item.locator(_Sel.RANK_TEXT).first.inner_text()
        rank = int(re.sub(r"\D", "", rank_text) or "0") or 1

        # Title
        title = (await item.locator(_Sel.TITLE).first.inner_text()).strip()

        # Author
        try:
            author = (await item.locator(_Sel.AUTHOR).first.inner_text()).strip()
        except Exception:  # noqa: BLE001
            author = ""

        # Price
        try:
            price_raw = await item.locator(_Sel.PRICE).first.inner_text()
            price_match = _PRICE_RE.search(price_raw.replace(",", "."))
            price_usd = float(price_match.group()) if price_match else 0.0
        except Exception:  # noqa: BLE001
            price_usd = 0.0

        # Review count
        try:
            reviews_texts = await item.locator(_Sel.REVIEW_COUNT).all_inner_texts()
            review_count = 0
            for rt in reviews_texts:
                digits = re.sub(r"\D", "", rt)
                if digits and int(digits) > review_count:
                    review_count = int(digits)
        except Exception:  # noqa: BLE001
            review_count = 0

        # Cover URL
        try:
            cover_url = await item.locator(_Sel.COVER_IMG).first.get_attribute("src") or ""
        except Exception:  # noqa: BLE001
            cover_url = ""

        # ASIN from item link href
        asin = ""
        try:
            href = await item.locator(_Sel.ITEM_LINK).first.get_attribute("href") or ""
            m = _ASIN_RE.search(href)
            if m:
                asin = m.group(1)
        except Exception:  # noqa: BLE001
            pass

        if not asin or len(asin) != 10:
            msg = f"Could not extract valid ASIN from item (rank={rank})"
            raise ValueError(msg)

        return CompetitorSnap(
            rank=rank,
            asin=asin,
            title=title,
            author=author,
            price_usd=price_usd,
            review_count=review_count,
            cover_url=cover_url,
        )

    async def _next_page_url(self) -> str | None:
        try:
            next_el = self._page.locator(_Sel.NEXT_PAGE).first
            href = await next_el.get_attribute("href")
            if not href:
                return None
            if href.startswith("http"):
                return href
            parsed = urlparse(self._page.url)
            return urlunparse(parsed._replace(path=href, query=""))
        except Exception:  # noqa: BLE001
            return None

    async def _detect_captcha(self) -> None:
        try:
            captcha = await self._page.locator(_Sel.CAPTCHA_FORM).count()
            if captcha > 0:
                screenshot_path: Path | None = None
                try:
                    path = Path("/tmp/captcha.png")
                    await self._page.screenshot(path=str(path))
                    screenshot_path = path
                except Exception:  # noqa: BLE001
                    pass
                raise CaptchaDetected(url=self._page.url, screenshot_path=screenshot_path)
        except CaptchaDetected:
            raise
        except Exception:  # noqa: BLE001
            pass

    def _record_page_load(self) -> None:
        now = datetime.now(UTC)
        self._page_times.append(now)
        # Keep only last hour
        cutoff = now.timestamp() - 3600
        while self._page_times and self._page_times[0].timestamp() < cutoff:
            self._page_times.popleft()

    async def _rate_check(self) -> None:
        if len(self._page_times) >= self._rate_limit:
            oldest = self._page_times[0]
            wait_s = 3600 - (datetime.now(UTC).timestamp() - oldest.timestamp())
            if wait_s > 0:
                logger.warning(
                    "rate limit {} pages/hour reached, sleeping {:.1f}s",
                    self._rate_limit,
                    wait_s,
                )
                await asyncio.sleep(wait_s)


__all__ = ["AmazonScraper"]
