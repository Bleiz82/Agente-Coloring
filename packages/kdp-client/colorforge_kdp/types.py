"""Domain types (Pydantic v2) for colorforge-kdp-client."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Fingerprint(BaseModel):
    user_agent: str
    viewport_width: int = Field(ge=800)
    viewport_height: int = Field(ge=600)
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    screen_width: int = Field(ge=800)
    screen_height: int = Field(ge=600)


class ProxyConfig(BaseModel):
    server: str  # e.g. "http://proxy.example.com:8080"
    username: str
    password: str


class AccountRecord(BaseModel):
    id: str
    label: str
    proxy_config: ProxyConfig
    fingerprint: Fingerprint
    storage_state_encrypted_path: Path
    daily_quota: int = Field(default=5, ge=1, le=25)
    created_at: datetime

    @property
    def account_age_days(self) -> int:
        delta = (
            datetime.now(tz=UTC) - self.created_at.replace(tzinfo=UTC)
            if self.created_at.tzinfo is None
            else datetime.now(tz=UTC) - self.created_at
        )
        return delta.days


class CompetitorSnap(BaseModel):
    rank: int = Field(ge=1)
    asin: str = Field(min_length=10, max_length=10)
    title: str
    author: str
    price_usd: float = Field(ge=0.0)
    review_count: int = Field(ge=0)
    cover_url: str
    bsr_category: str = ""

    @field_validator("asin")
    @classmethod
    def asin_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("ASIN must be alphanumeric")
        return v.upper()


class PublishStep(IntEnum):
    NAVIGATE = 1
    BOOK_DETAILS = 2
    KEYWORDS_CATEGORIES = 3
    UPLOAD_INTERIOR = 4
    UPLOAD_COVER = 5
    PRICING = 6
    REVIEW = 7
    SUBMIT = 8


class PublishJobState(BaseModel):
    book_id: str
    account_id: str
    last_completed_step: PublishStep | None = None
    asin: str | None = None
