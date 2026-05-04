"""Tests for browser.py -- AccountBrowserManager context isolation."""
# ruff: noqa: E402, I001
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import playwright_stealth as _ps
import pytest

# playwright_stealth v2.x removed stealth_async; browser.py imports it at
# module level. We must monkey-patch the attribute BEFORE importing browser.
if not hasattr(_ps, "stealth_async"):
    _ps.stealth_async = AsyncMock()  # type: ignore[attr-defined]

from colorforge_kdp.browser import AccountBrowserManager
from colorforge_kdp.exceptions import LoginRequired
from colorforge_kdp.types import AccountRecord, Fingerprint, ProxyConfig


def _make_account() -> AccountRecord:
    return AccountRecord(
        id="acc-001",
        label="test-account",
        proxy_config=ProxyConfig(
            server="http://proxy:8080", username="user", password="pass"
        ),
        fingerprint=Fingerprint(
            user_agent="Mozilla/5.0 (compatible)",
            viewport_width=1280,
            viewport_height=800,
            locale="en-US",
            timezone_id="America/New_York",
            screen_width=1920,
            screen_height=1080,
        ),
        storage_state_encrypted_path=Path("/encrypted/state.age"),
        daily_quota=5,
        created_at=datetime.now(UTC),
    )


async def test_browser_manager_passes_fingerprint_to_context(tmp_path: Path) -> None:
    account = _make_account()

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.storage_state = AsyncMock(return_value={})
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.stop = AsyncMock()

    # async_playwright() returns an object whose .start() returns a Playwright
    mock_pw_factory = MagicMock()
    mock_pw_factory.start = AsyncMock(return_value=mock_pw)

    with (
        patch(
            "colorforge_kdp.browser.decrypt_storage_state",
            new_callable=AsyncMock,
        ) as mock_decrypt,
        patch(
            "colorforge_kdp.browser.async_playwright",
            return_value=mock_pw_factory,
        ),
        patch("colorforge_kdp.browser.stealth_async", new_callable=AsyncMock),
    ):
        # Force fallback to None state by raising StorageStateError
        from colorforge_kdp.exceptions import StorageStateError

        mock_decrypt.side_effect = StorageStateError(
            Path("/encrypted/state.age"), "no age binary"
        )

        mgr = AccountBrowserManager(account, Path("/key.age"), tmpfs_dir=tmp_path)
        async with mgr as (ctx, page):
            assert ctx is mock_context
            assert page is mock_page

        # new_context called with correct fingerprint fields
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["user_agent"] == account.fingerprint.user_agent
        assert call_kwargs["locale"] == account.fingerprint.locale
        assert call_kwargs["timezone_id"] == account.fingerprint.timezone_id
        assert call_kwargs["storage_state"] is None


async def test_browser_manager_uses_decrypted_state(tmp_path: Path) -> None:
    account = _make_account()
    decrypted_path = tmp_path / "state.json"
    decrypted_path.write_text('{"cookies": [], "origins": []}')

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.storage_state = AsyncMock(return_value={})
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.stop = AsyncMock()

    mock_pw_factory = MagicMock()
    mock_pw_factory.start = AsyncMock(return_value=mock_pw)

    with (
        patch(
            "colorforge_kdp.browser.decrypt_storage_state",
            new_callable=AsyncMock,
            return_value=decrypted_path,
        ),
        patch(
            "colorforge_kdp.browser.async_playwright",
            return_value=mock_pw_factory,
        ),
        patch("colorforge_kdp.browser.stealth_async", new_callable=AsyncMock),
    ):
        mgr = AccountBrowserManager(account, Path("/key.age"), tmpfs_dir=tmp_path)
        async with mgr as (ctx, page):
            pass

        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["storage_state"] == str(decrypted_path)


async def test_detect_login_expiry_raises_on_signin_url(tmp_path: Path) -> None:
    account = _make_account()
    mgr = AccountBrowserManager(account, Path("/key.age"), tmpfs_dir=tmp_path)

    page = MagicMock()
    page.url = "https://www.amazon.com/ap/signin?openid..."

    with pytest.raises(LoginRequired) as exc_info:
        await mgr.detect_login_expiry(page)
    assert exc_info.value.account_id == "acc-001"
    assert "signin" in exc_info.value.redirect_url


async def test_detect_login_expiry_passes_on_kdp_url(tmp_path: Path) -> None:
    account = _make_account()
    mgr = AccountBrowserManager(account, Path("/key.age"), tmpfs_dir=tmp_path)

    page = MagicMock()
    page.url = "https://kdp.amazon.com/en_US/bookshelf"

    await mgr.detect_login_expiry(page)  # should not raise


async def test_detect_login_expiry_passes_on_kdp_title_page(tmp_path: Path) -> None:
    account = _make_account()
    mgr = AccountBrowserManager(account, Path("/key.age"), tmpfs_dir=tmp_path)

    page = MagicMock()
    page.url = "https://kdp.amazon.com/title/new?publishingMethod=BOOK"

    await mgr.detect_login_expiry(page)  # should not raise
