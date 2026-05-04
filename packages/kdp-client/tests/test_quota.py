"""Tests for quota.py -- daily publish limit enforcement."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from colorforge_kdp.exceptions import QuotaExceeded
from colorforge_kdp.quota import (
    check_and_consume_quota,
    get_daily_limit,
    get_today_publish_count,
)
from colorforge_kdp.types import AccountRecord, Fingerprint, ProxyConfig


def _make_account(age_days: int = 10, daily_quota: int = 5) -> AccountRecord:
    created = datetime.now(UTC) - timedelta(days=age_days)
    return AccountRecord(
        id="acc-001",
        label="test-account",
        proxy_config=ProxyConfig(
            server="http://proxy:8080", username="u", password="p"
        ),
        fingerprint=Fingerprint(
            user_agent="Mozilla/5.0",
            viewport_width=1280,
            viewport_height=800,
            screen_width=1920,
            screen_height=1080,
        ),
        storage_state_encrypted_path=Path("/tmp/state.age"),
        daily_quota=daily_quota,
        created_at=created,
    )


def _make_prisma(book_count: int) -> MagicMock:
    prisma = MagicMock()
    prisma.book = MagicMock()
    prisma.book.find_many = AsyncMock(return_value=[MagicMock()] * book_count)
    return prisma


def test_get_daily_limit_ramp_period() -> None:
    """Account age < 60 days should return ramp limit (5)."""
    acc = _make_account(age_days=10)
    assert get_daily_limit(acc) == 5


def test_get_daily_limit_steady_state() -> None:
    """Account age >= 60 days should return steady-state limit (10)."""
    acc = _make_account(age_days=61)
    assert get_daily_limit(acc) == 10


def test_get_daily_limit_boundary_day_59() -> None:
    """Day 59 is still in ramp period (< 60)."""
    acc = _make_account(age_days=59)
    assert get_daily_limit(acc) == 5


def test_get_daily_limit_boundary_day_60() -> None:
    """Day 60 enters steady state (>= 60)."""
    acc = _make_account(age_days=60)
    assert get_daily_limit(acc) == 10


async def test_get_today_publish_count() -> None:
    prisma = _make_prisma(3)
    count = await get_today_publish_count("acc-001", prisma)
    assert count == 3


async def test_get_today_publish_count_zero() -> None:
    prisma = _make_prisma(0)
    count = await get_today_publish_count("acc-001", prisma)
    assert count == 0


async def test_check_and_consume_quota_passes_under_limit() -> None:
    acc = _make_account(age_days=10)  # limit=5
    prisma = _make_prisma(4)  # 4 books today < 5
    await check_and_consume_quota(acc, prisma)  # should not raise


async def test_check_and_consume_quota_raises_at_limit() -> None:
    acc = _make_account(age_days=10)  # limit=5
    prisma = _make_prisma(5)  # 5 books today == 5
    with pytest.raises(QuotaExceeded) as exc_info:
        await check_and_consume_quota(acc, prisma)
    assert exc_info.value.limit == 5
    assert exc_info.value.current_count == 5
    assert exc_info.value.account_id == "acc-001"


async def test_check_and_consume_quota_raises_over_limit() -> None:
    acc = _make_account(age_days=10)  # limit=5
    prisma = _make_prisma(7)  # 7 > 5
    with pytest.raises(QuotaExceeded):
        await check_and_consume_quota(acc, prisma)


async def test_check_and_consume_quota_steady_state_passes() -> None:
    acc = _make_account(age_days=61)  # limit=10
    prisma = _make_prisma(9)  # 9 < 10
    await check_and_consume_quota(acc, prisma)  # should not raise


async def test_check_and_consume_quota_steady_state_raises() -> None:
    acc = _make_account(age_days=61)  # limit=10
    prisma = _make_prisma(10)  # 10 == 10
    with pytest.raises(QuotaExceeded) as exc_info:
        await check_and_consume_quota(acc, prisma)
    assert exc_info.value.limit == 10
