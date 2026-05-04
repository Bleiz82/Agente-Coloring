"""KDP 8-step atomic publish flow.

Each step is idempotent and resumable. The Publisher checks book_events in
the DB to find the last completed step and resumes from the next one.

IMPORTANT: All CSS selectors are placeholders marked # VERIFY_SELECTOR.
The operator must validate them against the live KDP UI on first run.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from loguru import logger
from playwright.async_api import Page

from colorforge_kdp.exceptions import PublishStepFailed, SelectorMissing
from colorforge_kdp.types import PublishJobState, PublishStep

# ---------------------------------------------------------------------------
# KDP UI selectors — ALL must be verified against live KDP UI
# ---------------------------------------------------------------------------


class _Sel:
    # Step 1 — Navigate
    PAPERBACK_RADIO: Final = "input[value='paperback']"  # VERIFY_SELECTOR
    CREATE_NEW_BTN: Final = "a[data-action='create-new-title']"  # VERIFY_SELECTOR

    # Step 2 — Book Details
    TITLE_INPUT: Final = "#data-print-book-title"  # VERIFY_SELECTOR
    SUBTITLE_INPUT: Final = "#data-print-book-subtitle"  # VERIFY_SELECTOR
    AUTHOR_FIRST: Final = "#data-print-book-contributors-first-name-0"  # VERIFY_SELECTOR
    AUTHOR_LAST: Final = "#data-print-book-contributors-last-name-0"  # VERIFY_SELECTOR
    DESCRIPTION: Final = "#data-print-book-description"  # VERIFY_SELECTOR
    AI_DISCLOSURE_YES: Final = "input[name='ai-disclosure'][value='YES']"  # VERIFY_SELECTOR
    DETAILS_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 3 — Keywords & Categories
    KEYWORD_INPUT: Final = "#data-print-book-keywords-{n}"  # VERIFY_SELECTOR (format with n=0..6)
    CATEGORY_BTN: Final = "#data-print-book-categories-button"  # VERIFY_SELECTOR
    CATEGORY_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 4 — Upload Interior
    INTERIOR_UPLOAD: Final = "input[type='file'][name='interior-file']"  # VERIFY_SELECTOR
    INTERIOR_SUCCESS: Final = "text=Upload successful"  # VERIFY_SELECTOR
    INTERIOR_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 5 — Upload Cover
    COVER_UPLOAD: Final = "input[type='file'][name='cover-file']"  # VERIFY_SELECTOR
    COVER_SUCCESS: Final = "text=Cover uploaded successfully"  # VERIFY_SELECTOR
    COVER_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 6 — Pricing
    PRICE_USD: Final = "#data-print-book-price-input-usd"  # VERIFY_SELECTOR
    PRICE_EUR: Final = "#data-print-book-price-input-eur"  # VERIFY_SELECTOR
    PRICE_GBP: Final = "#data-print-book-price-input-gbp"  # VERIFY_SELECTOR
    ROYALTY_60: Final = "input[name='royalty-plan'][value='0.60']"  # VERIFY_SELECTOR
    PRICING_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 7 — Review / Preview
    REVIEW_SAVE_BTN: Final = "#save-and-continue-announce"  # VERIFY_SELECTOR

    # Step 8 — Submit
    PUBLISH_BTN: Final = "#publish-announce"  # VERIFY_SELECTOR
    ASIN_LOCATOR: Final = "a[href*='/title/']"  # VERIFY_SELECTOR (contains ASIN in href)


class ListingData:
    """Minimal listing fields needed by the publisher."""

    __slots__ = (
        "title",
        "subtitle",
        "author_first",
        "author_last",
        "description",
        "keywords",
        "price_usd",
        "price_eur",
        "price_gbp",
        "bisac_categories",
    )

    def __init__(
        self,
        title: str,
        subtitle: str,
        author_first: str,
        author_last: str,
        description: str,
        keywords: list[str],
        price_usd: float,
        price_eur: float,
        price_gbp: float,
        bisac_categories: list[str],
    ) -> None:
        if len(keywords) != 7:
            msg = f"keywords must be exactly 7, got {len(keywords)}"
            raise ValueError(msg)
        self.title = title
        self.subtitle = subtitle
        self.author_first = author_first
        self.author_last = author_last
        self.description = description
        self.keywords = keywords
        self.price_usd = price_usd
        self.price_eur = price_eur
        self.price_gbp = price_gbp
        self.bisac_categories = bisac_categories


class BookDraftData:
    """Minimal book draft fields needed by the publisher."""

    __slots__ = ("interior_pdf", "cover_pdf")

    def __init__(self, interior_pdf: Path, cover_pdf: Path) -> None:
        self.interior_pdf = interior_pdf
        self.cover_pdf = cover_pdf


class KDPPublisher:
    """Executes the 8-step KDP paperback publish flow.

    Usage::

        async with AccountBrowserManager(account, ...) as (ctx, page):
            publisher = KDPPublisher(page, job_state, assets_dir, prisma)
            asin = await publisher.publish(listing, book_draft)
    """

    _KDP_NEW_TITLE: Final = "https://kdp.amazon.com/title/new?publishingMethod=BOOK"

    def __init__(
        self,
        page: Page,
        job_state: PublishJobState,
        assets_dir: Path,
        prisma: Any,
    ) -> None:
        self._page = page
        self._job_state = job_state
        self._assets_dir = assets_dir
        self._prisma: Any = prisma

    async def publish(self, listing: ListingData, book_draft: BookDraftData) -> str:
        """Run all 8 steps, resuming from last completed step. Returns ASIN."""
        last = await self._load_last_step()
        logger.info(
            "book={} starting publish, last_completed_step={}",
            self._job_state.book_id,
            last,
        )

        steps: list[tuple[PublishStep, Callable[[], Awaitable[str | None]]]] = [
            (PublishStep.NAVIGATE, self._step_navigate),
            (
                PublishStep.BOOK_DETAILS,
                lambda: self._step_book_details(listing),
            ),
            (
                PublishStep.KEYWORDS_CATEGORIES,
                lambda: self._step_keywords_categories(listing),
            ),
            (
                PublishStep.UPLOAD_INTERIOR,
                lambda: self._step_upload_interior(book_draft),
            ),
            (
                PublishStep.UPLOAD_COVER,
                lambda: self._step_upload_cover(book_draft),
            ),
            (PublishStep.PRICING, lambda: self._step_pricing(listing)),
            (PublishStep.REVIEW, self._step_review),
            (PublishStep.SUBMIT, self._step_submit),
        ]

        asin: str = ""
        for step_enum, step_fn in steps:
            if last is not None and step_enum <= last:
                logger.debug(
                    "book={} skipping completed step={}",
                    self._job_state.book_id,
                    step_enum.name,
                )
                continue
            result = await self._execute_step(step_enum, step_fn)
            if step_enum == PublishStep.SUBMIT and result:
                asin = result

        if not asin:
            logger.warning(
                "book={} ASIN not captured after publish",
                self._job_state.book_id,
            )
        return asin

    async def _execute_step(
        self,
        step: PublishStep,
        fn: Callable[[], Awaitable[str | None]],
    ) -> str | None:
        logger.info(
            "book={} executing step={}",
            self._job_state.book_id,
            step.name,
        )
        try:
            result = await fn()
            await self._save_step(step)
            await self._human_delay()
            return result
        except (SelectorMissing, PublishStepFailed):
            raise
        except Exception as exc:
            screenshot = await self._screenshot(step)
            raise PublishStepFailed(
                step=step.name,
                book_id=self._job_state.book_id,
                reason=str(exc),
                screenshot_path=screenshot,
            ) from exc

    async def _load_last_step(self) -> PublishStep | None:
        events: Any = await self._prisma.bookevent.find_many(
            where={
                "bookId": self._job_state.book_id,
                "eventType": {"startswith": "publish_step_"},
            },
            order_by={"createdAt": "desc"},
            take=1,
        )
        if not events:
            return None
        event_type: str = events[0].eventType
        step_name = event_type.removeprefix("publish_step_")
        try:
            return PublishStep[step_name.upper()]
        except KeyError:
            return None

    async def _save_step(self, step: PublishStep) -> None:
        await self._prisma.bookevent.create(
            data={
                "bookId": self._job_state.book_id,
                "eventType": f"publish_step_{step.name.lower()}",
                "createdAt": datetime.now(UTC),
                "payload": {},
            }
        )

    async def _screenshot(self, step: PublishStep) -> Path:
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = self._assets_dir / f"fail_{step.name.lower()}_{ts}.png"
        await self._page.screenshot(path=str(path))
        logger.warning(
            "book={} screenshot saved to {}",
            self._job_state.book_id,
            path,
        )
        return path

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _step_navigate(self) -> None:
        await self._page.goto(self._KDP_NEW_TITLE)
        await self._page.wait_for_load_state("networkidle")
        await self._click(_Sel.PAPERBACK_RADIO, "NAVIGATE")

    async def _step_book_details(self, listing: ListingData) -> None:
        await self._fill(_Sel.TITLE_INPUT, listing.title, "BOOK_DETAILS")
        await self._fill(_Sel.SUBTITLE_INPUT, listing.subtitle, "BOOK_DETAILS")
        await self._fill(_Sel.AUTHOR_FIRST, listing.author_first, "BOOK_DETAILS")
        await self._fill(_Sel.AUTHOR_LAST, listing.author_last, "BOOK_DETAILS")
        await self._fill(_Sel.DESCRIPTION, listing.description, "BOOK_DETAILS")
        await self._click(_Sel.AI_DISCLOSURE_YES, "BOOK_DETAILS")
        await self._click(_Sel.DETAILS_SAVE_BTN, "BOOK_DETAILS")
        await self._page.wait_for_load_state("networkidle")

    async def _step_keywords_categories(self, listing: ListingData) -> None:
        for n, kw in enumerate(listing.keywords):
            sel = _Sel.KEYWORD_INPUT.replace("{n}", str(n))
            await self._fill(sel, kw, "KEYWORDS_CATEGORIES")
        await self._click(_Sel.CATEGORY_BTN, "KEYWORDS_CATEGORIES")
        await self._page.wait_for_load_state("networkidle")
        await self._click(_Sel.CATEGORY_SAVE_BTN, "KEYWORDS_CATEGORIES")
        await self._page.wait_for_load_state("networkidle")

    async def _step_upload_interior(self, book_draft: BookDraftData) -> None:
        file_input = self._page.locator(_Sel.INTERIOR_UPLOAD)
        await file_input.set_input_files(str(book_draft.interior_pdf))
        await self._page.wait_for_selector(_Sel.INTERIOR_SUCCESS, timeout=120_000)
        await self._click(_Sel.INTERIOR_SAVE_BTN, "UPLOAD_INTERIOR")
        await self._page.wait_for_load_state("networkidle")

    async def _step_upload_cover(self, book_draft: BookDraftData) -> None:
        file_input = self._page.locator(_Sel.COVER_UPLOAD)
        await file_input.set_input_files(str(book_draft.cover_pdf))
        await self._page.wait_for_selector(_Sel.COVER_SUCCESS, timeout=120_000)
        await self._click(_Sel.COVER_SAVE_BTN, "UPLOAD_COVER")
        await self._page.wait_for_load_state("networkidle")

    async def _step_pricing(self, listing: ListingData) -> None:
        await self._fill(_Sel.PRICE_USD, f"{listing.price_usd:.2f}", "PRICING")
        await self._fill(_Sel.PRICE_EUR, f"{listing.price_eur:.2f}", "PRICING")
        await self._fill(_Sel.PRICE_GBP, f"{listing.price_gbp:.2f}", "PRICING")
        await self._click(_Sel.ROYALTY_60, "PRICING")
        await self._click(_Sel.PRICING_SAVE_BTN, "PRICING")
        await self._page.wait_for_load_state("networkidle")

    async def _step_review(self) -> None:
        await self._click(_Sel.REVIEW_SAVE_BTN, "REVIEW")
        await self._page.wait_for_load_state("networkidle")

    async def _step_submit(self) -> str:
        await self._click(_Sel.PUBLISH_BTN, "SUBMIT")
        await self._page.wait_for_load_state("networkidle")
        # Try to extract ASIN from the confirmation page URL or a link
        asin = ""
        try:
            loc = self._page.locator(_Sel.ASIN_LOCATOR).first
            href = await loc.get_attribute("href") or ""
            # KDP confirmation URL typically: /title/XXXXXXXXXX/...
            parts = [p for p in href.split("/") if len(p) == 10 and p.isalnum()]
            if parts:
                asin = parts[0].upper()
        except Exception:  # noqa: BLE001
            logger.warning(
                "book={} could not extract ASIN from page",
                self._job_state.book_id,
            )
        logger.info(
            "book={} publish submitted, asin={}",
            self._job_state.book_id,
            asin or "unknown",
        )
        return asin

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _click(self, selector: str, step: str) -> None:
        try:
            el = await self._page.wait_for_selector(selector, timeout=15_000)
            if el is None:
                raise SelectorMissing(selector=selector, step=step)
            box = await el.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
                cy = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                await self._page.mouse.move(cx, cy)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            await el.click()
        except SelectorMissing:
            raise
        except Exception as exc:
            raise SelectorMissing(selector=selector, step=step) from exc

    async def _fill(self, selector: str, value: str, step: str) -> None:
        try:
            el = await self._page.wait_for_selector(selector, timeout=15_000)
            if el is None:
                raise SelectorMissing(selector=selector, step=step)
            await el.click(click_count=3)
            await self._page.keyboard.press("Control+a")
            await self._page.type(selector, value, delay=random.randint(60, 120))
        except SelectorMissing:
            raise
        except Exception as exc:
            raise SelectorMissing(selector=selector, step=step) from exc

    @staticmethod
    async def _human_delay() -> None:
        await asyncio.sleep(random.uniform(1.5, 4.0))


__all__ = ["KDPPublisher", "ListingData", "BookDraftData"]
