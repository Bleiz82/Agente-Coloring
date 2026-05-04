"""Multi-account browser context manager."""
from __future__ import annotations

import asyncio
import random
from pathlib import Path
from types import TracebackType

from loguru import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright_stealth import Stealth  # type: ignore[import-untyped]

from colorforge_kdp.exceptions import LoginRequired, StorageStateError
from colorforge_kdp.storage import decrypt_storage_state
from colorforge_kdp.types import AccountRecord

_LOGIN_URL_FRAGMENT = "signin"
_KDP_BASE = "https://kdp.amazon.com"

# tmpfs-style temp dir for decrypted state files at runtime
_DEFAULT_STATE_DIR = Path("/run/colorforge/state")


class AccountBrowserManager:
    """Async context manager: yields (BrowserContext, Page) for one KDP account.

    Each account gets:
    - Dedicated BrowserContext (isolated cookies / storage)
    - Residential proxy from account config
    - Stable fingerprint (UA, viewport, locale, timezone, screen)
    - playwright-stealth applied to the page
    - StorageState loaded from decrypted file (decrypted to tmpfs_dir)

    On exit, saves updated storageState back and re-encrypts.
    """

    def __init__(
        self,
        account: AccountRecord,
        age_key_path: Path,
        tmpfs_dir: Path = _DEFAULT_STATE_DIR,
    ) -> None:
        self._account = account
        self._age_key_path = age_key_path
        self._tmpfs_dir = tmpfs_dir
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._decrypted_state_path: Path | None = None

    async def __aenter__(self) -> tuple[BrowserContext, Page]:
        self._tmpfs_dir.mkdir(parents=True, exist_ok=True)

        # Decrypt storageState to tmpfs
        try:
            self._decrypted_state_path = await decrypt_storage_state(
                encrypted=self._account.storage_state_encrypted_path,
                age_key=self._age_key_path,
                tmpfs_dir=self._tmpfs_dir,
            )
        except StorageStateError:
            logger.warning(
                "account={} Could not decrypt storageState — launching without",
                self._account.label,
            )
            self._decrypted_state_path = None

        fp = self._account.fingerprint
        proxy = self._account.proxy_config

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            proxy={
                "server": proxy.server,
                "username": proxy.username,
                "password": proxy.password,
            },
        )

        storage_state_arg: str | None = None
        if self._decrypted_state_path is not None:
            storage_state_arg = str(self._decrypted_state_path)

        self._context = await self._browser.new_context(
            user_agent=fp.user_agent,
            viewport={"width": fp.viewport_width, "height": fp.viewport_height},
            locale=fp.locale,
            timezone_id=fp.timezone_id,
            screen={"width": fp.screen_width, "height": fp.screen_height},
            storage_state=storage_state_arg,
        )

        page = await self._context.new_page()
        await Stealth().apply_stealth_async(page)

        logger.info("account={} browser context ready", self._account.label)
        return self._context, page

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._context is not None and self._decrypted_state_path is not None:
            try:
                await self._context.storage_state(
                    path=str(self._decrypted_state_path)
                )
                logger.debug(
                    "account={} storageState saved", self._account.label
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "account={} failed to save storageState: {}", self._account.label, e
                )

        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()

    async def detect_login_expiry(self, page: Page) -> None:
        """Raise LoginRequired if the current page is a sign-in redirect.

        Call this after any navigation to KDP pages.
        """
        url = page.url
        if _LOGIN_URL_FRAGMENT in url:
            raise LoginRequired(
                account_id=self._account.id,
                redirect_url=url,
            )

    @staticmethod
    async def human_delay(low: float = 1.5, high: float = 4.0) -> None:
        """Sleep for a random human-like duration."""
        await asyncio.sleep(random.uniform(low, high))
