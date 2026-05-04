"""RQ job: scrape Amazon bestsellers for a niche."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from colorforge_kdp.browser import AccountBrowserManager
from colorforge_kdp.scraper import AmazonScraper
from colorforge_kdp.types import AccountRecord, Fingerprint, ProxyConfig
from loguru import logger


def handle_scrape_job(
    category_url: str,
    account_id: str,
    niche_id: str,
    account_data: dict[str, Any],
    age_key_path: str,
    max_pages: int = 5,
) -> dict[str, Any]:
    """RQ entry point -- synchronous wrapper around async scrape logic."""
    return asyncio.run(
        _async_scrape(
            category_url=category_url,
            niche_id=niche_id,
            account_data=account_data,
            age_key_path=Path(age_key_path),
            max_pages=max_pages,
        )
    )


async def _async_scrape(
    category_url: str,
    niche_id: str,
    account_data: dict[str, Any],
    age_key_path: Path,
    max_pages: int,
) -> dict[str, Any]:
    account = AccountRecord(
        id=account_data["id"],
        label=account_data["label"],
        proxy_config=ProxyConfig(**account_data["proxy_config"]),
        fingerprint=Fingerprint(**account_data["fingerprint"]),
        storage_state_encrypted_path=Path(account_data["storage_state_encrypted_path"]),
        daily_quota=account_data.get("daily_quota", 5),
        created_at=account_data["created_at"],
    )

    from prisma import Prisma

    prisma = Prisma()
    await prisma.connect()
    try:
        async with AccountBrowserManager(account, age_key_path) as (_ctx, page):
            scraper = AmazonScraper(page)
            snaps = await scraper.scrape_bestsellers(category_url, max_pages=max_pages)

        # Upsert competitor snaps to DB
        for snap in snaps:
            await prisma.reviewscraped.upsert(
                where={"reviewHash": f"bsr_{snap.asin}_{niche_id}"},
                data={
                    "create": {
                        "nicheId": niche_id,
                        "reviewHash": f"bsr_{snap.asin}_{niche_id}",
                        "asin": snap.asin,
                        "text": snap.title,
                        "rating": 0,
                        "source": "bestseller_scrape",
                    },
                    "update": {"text": snap.title},
                },
            )
    finally:
        await prisma.disconnect()

    logger.info("niche={} scraped {} competitors", niche_id, len(snaps))
    return {"niche_id": niche_id, "count": len(snaps)}


__all__ = ["handle_scrape_job"]
