"""BookPlan contract — output of Strategist."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PagePrompt(BaseModel):
    """A single page prompt within a BookPlan."""

    index: int = Field(ge=0)
    prompt: str = Field(min_length=1)
    complexity_tier: Literal["sparse", "medium", "dense"]
    theme: str


class CoverBrief(BaseModel):
    """Cover generation brief."""

    subject: str
    style_fingerprint: str
    palette_hint: str
    background_hint: str


class BookPlan(BaseModel):
    """Full production plan for a single book."""

    niche_brief_id: str
    account_id: str
    style_fingerprint: str = Field(min_length=1)
    page_count: int = Field(ge=20, le=200)
    page_prompts: list[PagePrompt] = Field(min_length=1)
    cover_brief: CoverBrief
    target_keyword: str = Field(min_length=1)
    target_price: float = Field(gt=0)
    brand_author: str = Field(min_length=1)
    expected_production_minutes: float | None = Field(default=None, gt=0)


BOOK_PLAN_EXAMPLE = BookPlan(
    niche_brief_id="550e8400-e29b-41d4-a716-446655440000",
    account_id="660e8400-e29b-41d4-a716-446655440001",
    style_fingerprint="stefano-main-mandala-flow",
    page_count=75,
    page_prompts=[
        PagePrompt(
            index=0,
            prompt=(
                "Black and white coloring book line art for adults. Subject: intricate ocean"
                " wave mandala with seashells and coral. Style: clean bold outlines, uniform"
                " line weight, NO shading, NO gradients. Background: pure white."
                " Composition: centered, fills 80% of frame. Detail level: dense."
            ),
            complexity_tier="dense",
            theme="ocean-wave-mandala",
        ),
    ],
    cover_brief=CoverBrief(
        subject="Majestic ocean mandala with waves, shells, and coral",
        style_fingerprint="stefano-main-mandala-flow",
        palette_hint="#1A0033, #003366, #FFD700",
        background_hint="Deep ocean blue gradient with subtle wave texture",
    ),
    target_keyword="ocean mandala coloring book",
    target_price=7.99,
    brand_author="Stefano Demuru",
    expected_production_minutes=20,
)
