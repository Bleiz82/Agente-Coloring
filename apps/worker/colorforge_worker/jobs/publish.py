"""RQ job: publish a book to KDP."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

# colorforge_kdp is installed as a workspace package
from colorforge_kdp.browser import AccountBrowserManager
from colorforge_kdp.publisher import BookDraftData, KDPPublisher, ListingData
from colorforge_kdp.quota import check_and_consume_quota
from colorforge_kdp.types import AccountRecord, Fingerprint, ProxyConfig, PublishJobState
from loguru import logger


def handle_publish_job(
    book_id: str,
    account_id: str,
    account_data: dict[str, Any],
    listing_data: dict[str, Any],
    interior_pdf: str,
    cover_pdf: str,
    assets_dir: str,
    age_key_path: str,
) -> dict[str, Any]:
    """RQ entry point -- synchronous wrapper around async publish logic."""
    return asyncio.run(
        _async_publish(
            book_id=book_id,
            account_id=account_id,
            account_data=account_data,
            listing_data=listing_data,
            interior_pdf=Path(interior_pdf),
            cover_pdf=Path(cover_pdf),
            assets_dir=Path(assets_dir),
            age_key_path=Path(age_key_path),
        )
    )


async def _async_publish(
    book_id: str,
    account_id: str,
    account_data: dict[str, Any],
    listing_data: dict[str, Any],
    interior_pdf: Path,
    cover_pdf: Path,
    assets_dir: Path,
    age_key_path: Path,
) -> dict[str, Any]:
    start = time.monotonic()

    account = AccountRecord(
        id=account_data["id"],
        label=account_data["label"],
        proxy_config=ProxyConfig(**account_data["proxy_config"]),
        fingerprint=Fingerprint(**account_data["fingerprint"]),
        storage_state_encrypted_path=Path(account_data["storage_state_encrypted_path"]),
        daily_quota=account_data.get("daily_quota", 5),
        created_at=account_data["created_at"],
    )

    # Quota check (raises QuotaExceeded if at limit -- RQ will mark job as failed)
    # We use a lazily imported prisma client to avoid importing at module level
    from prisma import Prisma

    prisma = Prisma()
    await prisma.connect()
    try:
        await check_and_consume_quota(account, prisma)

        job_state = PublishJobState(book_id=book_id, account_id=account_id)
        listing = ListingData(
            title=listing_data["title"],
            subtitle=listing_data.get("subtitle", ""),
            author_first=listing_data["author_first"],
            author_last=listing_data["author_last"],
            description=listing_data["description"],
            keywords=listing_data["keywords"],
            price_usd=listing_data["price_usd"],
            price_eur=listing_data["price_eur"],
            price_gbp=listing_data["price_gbp"],
            bisac_categories=listing_data.get("bisac_categories", []),
        )
        book_draft = BookDraftData(interior_pdf=interior_pdf, cover_pdf=cover_pdf)

        async with AccountBrowserManager(account, age_key_path) as (_ctx, page):
            publisher = KDPPublisher(page, job_state, assets_dir, prisma)
            asin = await publisher.publish(listing, book_draft)
    finally:
        await prisma.disconnect()

    duration_s = round(time.monotonic() - start, 2)
    logger.info("book={} publish done asin={} duration_s={}", book_id, asin, duration_s)
    return {"asin": asin, "book_id": book_id, "duration_s": duration_s}


__all__ = ["handle_publish_job"]
