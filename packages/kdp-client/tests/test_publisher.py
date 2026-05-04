"""Tests for publisher.py -- step execution and resumption."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from colorforge_kdp.publisher import BookDraftData, KDPPublisher, ListingData
from colorforge_kdp.types import PublishJobState


def _make_listing() -> ListingData:
    return ListingData(
        title="Test Book",
        subtitle="A Subtitle",
        author_first="Jane",
        author_last="Doe",
        description="A great coloring book.",
        keywords=["art", "color", "mandala", "adult", "relax", "zen", "calm"],
        price_usd=9.99,
        price_eur=8.99,
        price_gbp=7.99,
        bisac_categories=["ART015000"],
    )


def _make_draft(tmp_path: Path) -> BookDraftData:
    interior = tmp_path / "interior.pdf"
    cover = tmp_path / "cover.pdf"
    interior.write_bytes(b"%PDF-1.4")
    cover.write_bytes(b"%PDF-1.4")
    return BookDraftData(interior_pdf=interior, cover_pdf=cover)


def _make_prisma(last_step: str | None = None) -> MagicMock:
    prisma = MagicMock()
    prisma.bookevent = MagicMock()

    event = MagicMock()
    event.eventType = f"publish_step_{last_step}" if last_step else ""

    prisma.bookevent.find_many = AsyncMock(
        return_value=[event] if last_step else []
    )
    prisma.bookevent.create = AsyncMock(return_value=MagicMock())
    return prisma


def _make_page() -> MagicMock:
    page = AsyncMock()
    page.url = "https://kdp.amazon.com/bookshelf"
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock()
    page.type = AsyncMock()
    page.keyboard = AsyncMock()
    page.mouse = AsyncMock()
    page.locator = MagicMock(return_value=AsyncMock())

    # Make wait_for_selector return an element with bounding_box
    el = AsyncMock()
    el.bounding_box = AsyncMock(
        return_value={"x": 100.0, "y": 100.0, "width": 50.0, "height": 20.0}
    )
    el.click = AsyncMock()
    page.wait_for_selector = AsyncMock(return_value=el)

    return page


def test_listing_rejects_too_few_keywords() -> None:
    with pytest.raises(ValueError, match="keywords must be exactly 7"):
        ListingData(
            title="T",
            subtitle="S",
            author_first="A",
            author_last="B",
            description="D",
            keywords=["only", "six", "words", "here", "not", "enough"],
            price_usd=9.99,
            price_eur=8.99,
            price_gbp=7.99,
            bisac_categories=[],
        )


def test_listing_rejects_too_many_keywords() -> None:
    with pytest.raises(ValueError, match="keywords must be exactly 7"):
        ListingData(
            title="T",
            subtitle="S",
            author_first="A",
            author_last="B",
            description="D",
            keywords=["a", "b", "c", "d", "e", "f", "g", "h"],
            price_usd=9.99,
            price_eur=8.99,
            price_gbp=7.99,
            bisac_categories=[],
        )


def test_listing_accepts_exactly_7_keywords() -> None:
    listing = ListingData(
        title="T",
        subtitle="S",
        author_first="A",
        author_last="B",
        description="D",
        keywords=["a", "b", "c", "d", "e", "f", "g"],
        price_usd=9.99,
        price_eur=8.99,
        price_gbp=7.99,
        bisac_categories=[],
    )
    assert listing.title == "T"


async def test_publish_executes_all_steps_when_no_prior_progress(
    tmp_path: Path,
) -> None:
    page = _make_page()
    prisma = _make_prisma(last_step=None)
    job_state = PublishJobState(book_id="book-001", account_id="acc-001")
    publisher = KDPPublisher(page, job_state, tmp_path, prisma)
    listing = _make_listing()
    draft = _make_draft(tmp_path)

    with (
        patch.object(publisher, "_step_navigate", new_callable=AsyncMock) as nav,
        patch.object(publisher, "_step_book_details", new_callable=AsyncMock) as det,
        patch.object(
            publisher, "_step_keywords_categories", new_callable=AsyncMock
        ) as kw,
        patch.object(publisher, "_step_upload_interior", new_callable=AsyncMock) as ui,
        patch.object(publisher, "_step_upload_cover", new_callable=AsyncMock) as uc,
        patch.object(publisher, "_step_pricing", new_callable=AsyncMock) as pr,
        patch.object(publisher, "_step_review", new_callable=AsyncMock) as rv,
        patch.object(
            publisher,
            "_step_submit",
            new_callable=AsyncMock,
            return_value="B00TEST1234",
        ) as sub,
        patch.object(publisher, "_human_delay", new_callable=AsyncMock),
    ):
        asin = await publisher.publish(listing, draft)

    assert asin == "B00TEST1234"
    nav.assert_called_once()
    det.assert_called_once()
    kw.assert_called_once()
    ui.assert_called_once()
    uc.assert_called_once()
    pr.assert_called_once()
    rv.assert_called_once()
    sub.assert_called_once()
    assert prisma.bookevent.create.call_count == 8


async def test_publish_skips_completed_steps(tmp_path: Path) -> None:
    page = _make_page()
    # Simulate steps 1-3 already done
    prisma = _make_prisma(last_step="keywords_categories")
    job_state = PublishJobState(book_id="book-002", account_id="acc-001")
    publisher = KDPPublisher(page, job_state, tmp_path, prisma)
    listing = _make_listing()
    draft = _make_draft(tmp_path)

    with (
        patch.object(publisher, "_step_navigate", new_callable=AsyncMock) as nav,
        patch.object(publisher, "_step_book_details", new_callable=AsyncMock) as det,
        patch.object(
            publisher, "_step_keywords_categories", new_callable=AsyncMock
        ) as kw,
        patch.object(publisher, "_step_upload_interior", new_callable=AsyncMock) as ui,
        patch.object(publisher, "_step_upload_cover", new_callable=AsyncMock) as uc,
        patch.object(publisher, "_step_pricing", new_callable=AsyncMock) as pr,
        patch.object(publisher, "_step_review", new_callable=AsyncMock) as rv,
        patch.object(
            publisher,
            "_step_submit",
            new_callable=AsyncMock,
            return_value="B00RESUME01",
        ) as sub,
        patch.object(publisher, "_human_delay", new_callable=AsyncMock),
    ):
        asin = await publisher.publish(listing, draft)

    # Steps 1-3 skipped, 4-8 run
    nav.assert_not_called()
    det.assert_not_called()
    kw.assert_not_called()
    ui.assert_called_once()
    uc.assert_called_once()
    pr.assert_called_once()
    rv.assert_called_once()
    sub.assert_called_once()
    assert asin == "B00RESUME01"
    # Only 5 steps saved to DB (4-8)
    assert prisma.bookevent.create.call_count == 5


async def test_publish_resumes_from_last_step_only(tmp_path: Path) -> None:
    """When all steps except SUBMIT are done, only SUBMIT runs."""
    page = _make_page()
    prisma = _make_prisma(last_step="review")
    job_state = PublishJobState(book_id="book-003", account_id="acc-001")
    publisher = KDPPublisher(page, job_state, tmp_path, prisma)
    listing = _make_listing()
    draft = _make_draft(tmp_path)

    with (
        patch.object(publisher, "_step_navigate", new_callable=AsyncMock) as nav,
        patch.object(publisher, "_step_book_details", new_callable=AsyncMock) as det,
        patch.object(
            publisher, "_step_keywords_categories", new_callable=AsyncMock
        ) as kw,
        patch.object(publisher, "_step_upload_interior", new_callable=AsyncMock) as ui,
        patch.object(publisher, "_step_upload_cover", new_callable=AsyncMock) as uc,
        patch.object(publisher, "_step_pricing", new_callable=AsyncMock) as pr,
        patch.object(publisher, "_step_review", new_callable=AsyncMock) as rv,
        patch.object(
            publisher,
            "_step_submit",
            new_callable=AsyncMock,
            return_value="B00LAST0001",
        ) as sub,
        patch.object(publisher, "_human_delay", new_callable=AsyncMock),
    ):
        asin = await publisher.publish(listing, draft)

    nav.assert_not_called()
    det.assert_not_called()
    kw.assert_not_called()
    ui.assert_not_called()
    uc.assert_not_called()
    pr.assert_not_called()
    rv.assert_not_called()
    sub.assert_called_once()
    assert asin == "B00LAST0001"
    assert prisma.bookevent.create.call_count == 1


def test_book_draft_stores_paths(tmp_path: Path) -> None:
    interior = tmp_path / "interior.pdf"
    cover = tmp_path / "cover.pdf"
    interior.write_bytes(b"%PDF-1.4")
    cover.write_bytes(b"%PDF-1.4")
    draft = BookDraftData(interior_pdf=interior, cover_pdf=cover)
    assert draft.interior_pdf == interior
    assert draft.cover_pdf == cover
