"""SuccessScore contract — output of Performance Monitor."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SuccessScore(BaseModel):
    """Per-book success metric at a given time window."""

    book_id: str
    window_days: Literal[7, 14, 30]
    units_sold: int = Field(ge=0)
    royalty_total: float = Field(ge=0)
    kenp_read: int = Field(ge=0)
    refund_count: int = Field(ge=0)
    computed_score: float = Field(ge=0, le=100)
    classification: Literal["winner", "flat", "loser"]
    percentile_within_account: float = Field(ge=0, le=100)
    percentile_within_niche: float = Field(ge=0, le=100)


SUCCESS_SCORE_EXAMPLE = SuccessScore(
    book_id="770e8400-e29b-41d4-a716-446655440002",
    window_days=30,
    units_sold=47,
    royalty_total=84.32,
    kenp_read=1250,
    refund_count=1,
    computed_score=78,
    classification="winner",
    percentile_within_account=92,
    percentile_within_niche=88,
)
