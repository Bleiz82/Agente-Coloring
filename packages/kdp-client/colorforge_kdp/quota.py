"""KDP publish quota enforcement.

Rules (SPEC.md §2):
- First 60 days of account life: max 5 publishes/day
- After 60 days: max 10 publishes/day
- Quota is checked before every publish; NOT decremented here (Publisher handles state transitions).
- "today" is always UTC midnight boundary.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Protocol

from loguru import logger

from colorforge_kdp.exceptions import QuotaExceeded
from colorforge_kdp.types import AccountRecord

_RAMP_DAYS = 60
_RAMP_LIMIT = 5
_STEADY_LIMIT = 10

if TYPE_CHECKING:
    # We accept any async Prisma-like client without a hard import dependency.
    # The real prisma client satisfies this at runtime.
    class _PrismaLike(Protocol):
        @property
        def book(self) -> Any: ...


def get_daily_limit(account: AccountRecord) -> int:
    """Return the publish limit for today based on account age."""
    if account.account_age_days < _RAMP_DAYS:
        return _RAMP_LIMIT
    return _STEADY_LIMIT


async def get_today_publish_count(account_id: str, prisma: Any) -> int:
    """Count books for this account published today (UTC).

    Counts books whose state is 'publishing' or 'live' AND whose updatedAt >= today 00:00 UTC.
    """
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=UTC)
    books = await prisma.book.find_many(
        where={
            "accountId": account_id,
            "state": {"in": ["publishing", "live"]},
            "updatedAt": {"gte": today_start},
        }
    )
    return len(books)


async def check_and_consume_quota(account: AccountRecord, prisma: Any) -> None:
    """Raise QuotaExceeded if the account has reached its daily publish limit.

    Does NOT consume quota — merely checks. The Publisher transitions book state
    to 'publishing', which is what get_today_publish_count counts.
    """
    limit = get_daily_limit(account)
    count = await get_today_publish_count(account.id, prisma)
    logger.info(
        "account={} quota_check today_count={} limit={}",
        account.label,
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
    "get_daily_limit",
    "get_today_publish_count",
    "check_and_consume_quota",
]
