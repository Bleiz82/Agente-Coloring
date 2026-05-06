"""Domain exceptions for colorforge-kdp-client."""

from __future__ import annotations

from pathlib import Path


class ColorforgeKDPError(Exception):
    """Base exception for all kdp-client errors."""


class QuotaExceeded(ColorforgeKDPError):
    def __init__(self, account_id: str, limit: int, current_count: int) -> None:
        self.account_id = account_id
        self.limit = limit
        self.current_count = current_count
        super().__init__(
            f"Account {account_id} has reached weekly per-format publish limit"
            f" ({current_count}/{limit})"
        )


class SelectorMissing(ColorforgeKDPError):
    def __init__(self, selector: str, step: str, screenshot_path: Path | None = None) -> None:
        self.selector = selector
        self.step = step
        self.screenshot_path = screenshot_path
        super().__init__(f"Selector '{selector}' not found at step '{step}'")


class LoginRequired(ColorforgeKDPError):
    def __init__(self, account_id: str, redirect_url: str) -> None:
        self.account_id = account_id
        self.redirect_url = redirect_url
        super().__init__(f"Account {account_id} session expired — redirected to {redirect_url}")


class PublishStepFailed(ColorforgeKDPError):
    def __init__(
        self,
        step: str,
        book_id: str,
        reason: str,
        screenshot_path: Path | None = None,
    ) -> None:
        self.step = step
        self.book_id = book_id
        self.reason = reason
        self.screenshot_path = screenshot_path
        super().__init__(f"Publish step '{step}' failed for book {book_id}: {reason}")


class StorageStateError(ColorforgeKDPError):
    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"StorageState error at '{path}': {reason}")


class CaptchaDetected(ColorforgeKDPError):
    def __init__(self, url: str, screenshot_path: Path | None = None) -> None:
        self.url = url
        self.screenshot_path = screenshot_path
        super().__init__(f"Captcha detected at {url}")


class ScraperRateLimitExceeded(ColorforgeKDPError):
    def __init__(self, pages_per_hour: int, limit: int) -> None:
        self.pages_per_hour = pages_per_hour
        self.limit = limit
        super().__init__(
            f"Scraper rate limit exceeded: {pages_per_hour} pages/hour (limit {limit})"
        )
