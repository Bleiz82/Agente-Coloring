"""KDP publish quota enforcement.

Rules (KDP_OFFICIAL_SPECS.md §1):
- Max 10 titles per format per week (paperback and hardcover counted separately).
- Quota is checked before every publish; NOT decremented here (Publisher handles state
  transitions which is what get_weekly_format_publish_count counts).
- "this week" is a rolling 7-day window anchored at UTC now.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

from loguru import logger

from colorforge_kdp.exceptions import QuotaExceeded
from colorforge_kdp.types import AccountRecord

_WEEKLY_FORMAT_LIMIT = 10  # KDP official: 10 titles/format/week per account

if TYPE_CHECKING:
    class _PrismaLike(Protocol):
        @property
        def book(self) -> Any: ...


def get_weekly_limit() -> int:
    """Return the KDP weekly publish limit per format per account."""
    return _WEEKLY_FORMAT_LIMIT


async def get_weekly_format_publish_count(
    account_id: str,
    book_format: str,
    prisma: Any,
) -> int:
    """Count books for this account+format published in the last 7 days (UTC rolling window).

    Args:
        account_id: KDP account identifier.
        book_format: "PAPERBACK" or "HARDCOVER" — counted separately per KDP rules.
        prisma: Async Prisma client.

    Returns:
        Number of titles in 'publishing' or 'live' state updated in the last 7 days.
    """
    week_start = datetime.now(tz=UTC) - timedelta(days=7)
    books = await prisma.book.find_many(
        where={
            "accountId": account_id,
            "bookFormat": book_format,
            "state": {"in": ["publishing", "live"]},
            "updatedAt": {"gte": week_start},
        }
    )
    return len(books)


async def check_and_consume_quota(
    account: AccountRecord,
    prisma: Any,
    book_format: str = "PAPERBACK",
) -> None:
    """Raise QuotaExceeded if the account has reached its weekly per-format publish limit.

    Does NOT consume quota — merely checks. The Publisher transitions book state
    to 'publishing', which is what get_weekly_format_publish_count counts.

    Args:
        account: KDP account record.
        prisma: Async Prisma client.
        book_format: "PAPERBACK" or "HARDCOVER" (default "PAPERBACK").

    Raises:
        QuotaExceeded: If weekly format count >= 10.
    """
    limit = get_weekly_limit()
    count = await get_weekly_format_publish_count(account.id, book_format, prisma)
    logger.info(
        "account={} format={} quota_check weekly_count={} limit={}",
        account.label,
        book_format,
        count,
        limit,
    )
    if count >= limit:
        raise QuotaExceeded(
            account_id=account.id,
            limit=limit,
            current_count=count,
        )


__all__ = [
    "get_weekly_limit",
    "get_weekly_format_publish_count",
    "check_and_consume_quota",
]
