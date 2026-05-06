"""Royalty Snapshot Writer — aggregates monthly sales into RoyaltySnapshot records."""

from __future__ import annotations

from datetime import date
from typing import Any

from loguru import logger


class RoyaltySnapshotWriter:
    def __init__(self, prisma: Any) -> None:
        self._prisma = prisma

    async def write_monthly(self, account_id: str, year_month: str) -> dict[str, Any]:
        year_str, month_str = year_month.split("-")
        year = int(year_str)
        month = int(month_str)

        start = date(year, month, 1)
        end_exclusive = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        rows = await self._prisma.salesdaily.find_many(
            where={
                "accountId": account_id,
                "date": {"gte": start, "lt": end_exclusive},
            }
        )

        total_royalty: float = float(sum(row.royalty for row in rows))
        total_units: int = sum(row.unitsSold for row in rows)
        book_count: int = len({row.bookId for row in rows})

        winners = await self._count_winners(account_id, year_month)
        live_books = await self._count_live_books(account_id)
        hit_rate = winners / live_books * 100.0 if live_books > 0 else 0.0

        await self._prisma.royaltysnapshot.upsert(
            where={"yearMonth_accountId": {"yearMonth": year_month, "accountId": account_id}},
            data={
                "create": {
                    "yearMonth": year_month,
                    "accountId": account_id,
                    "totalRoyalty": total_royalty,
                    "totalUnits": total_units,
                    "bookCount": book_count,
                    "hitRate": hit_rate,
                },
                "update": {
                    "totalRoyalty": total_royalty,
                    "totalUnits": total_units,
                    "bookCount": book_count,
                    "hitRate": hit_rate,
                },
            },
        )

        result: dict[str, Any] = {
            "account_id": account_id,
            "year_month": year_month,
            "total_royalty": total_royalty,
            "total_units": total_units,
            "book_count": book_count,
            "winners": winners,
            "live_books": live_books,
            "hit_rate": hit_rate,
        }
        logger.info("Royalty snapshot written", **result)
        return result

    async def _count_winners(self, account_id: str, year_month: str) -> int:
        year_str, month_str = year_month.split("-")
        year = int(year_str)
        month = int(month_str)

        start = date(year, month, 1)
        end_exclusive = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        rows = await self._prisma.salesdaily.find_many(
            where={
                "accountId": account_id,
                "date": {"gte": start, "lt": end_exclusive},
            }
        )

        royalty_by_book: dict[str, float] = {}
        for row in rows:
            royalty_by_book[row.bookId] = royalty_by_book.get(row.bookId, 0.0) + float(row.royalty)

        return sum(1 for v in royalty_by_book.values() if v >= 50.0)

    async def _count_live_books(self, account_id: str) -> int:
        count: int = await self._prisma.book.count(
            where={"accountId": account_id, "status": "LIVE"}
        )
        return count
