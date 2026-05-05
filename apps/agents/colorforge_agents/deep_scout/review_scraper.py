"""Amazon low-rated review scraper."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    pass


async def scrape_low_rated_reviews(
    asin: str,
    page: Any,  # playwright Page
    max_reviews: int = 50,
) -> list[dict[str, Any]]:
    """Scrape 1-2 star reviews from Amazon for a given ASIN.

    Returns a list of {text, rating, review_id}.
    Returns empty list on any failure.
    """
    reviews: list[dict[str, Any]] = []
    try:
        reviews = await _scrape_reviews(asin, page, max_reviews)
    except Exception as exc:
        logger.warning("Review scrape failed for ASIN {}: {}", asin, exc)
    return reviews


async def _scrape_reviews(
    asin: str, page: Any, max_reviews: int
) -> list[dict[str, Any]]:
    url = (
        f"https://www.amazon.com/product-reviews/{asin}"
        "?filterByStar=critical&reviewerType=all_reviews&pageNumber=1"
    )
    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    reviews: list[dict[str, Any]] = []
    page_num = 1

    while len(reviews) < max_reviews:
        items = await page.query_selector_all("[data-hook='review']")
        for item in items:
            if len(reviews) >= max_reviews:
                break
            review = await _extract_review(item)
            if review:
                reviews.append(review)

        next_btn = await page.query_selector(
            "li.a-last:not(.a-disabled) a"
        )
        if not next_btn or page_num >= 5:
            break

        page_num += 1
        next_url = (
            f"https://www.amazon.com/product-reviews/{asin}"
            f"?filterByStar=critical&reviewerType=all_reviews&pageNumber={page_num}"
        )
        await page.goto(next_url, wait_until="domcontentloaded", timeout=30_000)

    return reviews


async def _extract_review(item: Any) -> dict[str, Any] | None:
    try:
        id_attr: str | None = await item.get_attribute("id")
        review_id = id_attr or "unknown"

        rating_el = await item.query_selector("[data-hook='review-star-rating']")
        rating_text: str = await rating_el.inner_text() if rating_el else "1"
        rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
        rating = float(rating_match.group(1)) if rating_match else 1.0

        if rating > 2.5:
            return None

        body_el = await item.query_selector("[data-hook='review-body']")
        body: str = await body_el.inner_text() if body_el else ""
        body = body.strip()

        if not body:
            return None

        return {"text": body, "rating": rating, "review_id": review_id}
    except Exception:
        return None
