"""BookPlan contract — output of Strategist."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

_TRIM_DIMENSIONS: dict[str, tuple[float, float]] = {
    "8.5x11": (8.5, 11.0),
    "8.5x8.5": (8.5, 8.5),
    "8x10": (8.0, 10.0),
    "7x10": (7.0, 10.0),
    "6x9": (6.0, 9.0),
}

_PAPER_SPINE_MULTIPLIERS: dict[str, float] = {
    "WHITE": 0.002252,
    "CREAM": 0.0025,
    "PREMIUM_COLOR": 0.002347,
    "STANDARD_COLOR": 0.002252,
}


class BookFormat(StrEnum):
    """KDP book format — paperback and hardcover quotas are tracked separately."""

    PAPERBACK = "PAPERBACK"
    HARDCOVER = "HARDCOVER"


class TrimSize(StrEnum):
    """KDP paperback trim sizes most relevant for coloring books.

    Source: KDP_OFFICIAL_SPECS.md §2.
    """

    LETTER = "8.5x11"         # adult coloring (default)
    SQUARE_LARGE = "8.5x8.5"  # mandala / square
    KIDS = "8x10"              # children's coloring
    INTERMEDIATE = "7x10"     # workbook / activity
    POCKET = "6x9"             # travel / pocket coloring

    @property
    def width_inches(self) -> float:
        """Trim width in inches."""
        return _TRIM_DIMENSIONS[self.value][0]

    @property
    def height_inches(self) -> float:
        """Trim height in inches."""
        return _TRIM_DIMENSIONS[self.value][1]


class PaperType(StrEnum):
    """KDP paper type — controls spine width multiplier and print cost.

    Source: KDP_OFFICIAL_SPECS.md §5, §16.

    Raises:
        KeyError: should never occur; all values are in _PAPER_SPINE_MULTIPLIERS.
    """

    WHITE = "WHITE"
    CREAM = "CREAM"
    PREMIUM_COLOR = "PREMIUM_COLOR"
    STANDARD_COLOR = "STANDARD_COLOR"

    @property
    def spine_multiplier(self) -> float:
        """Spine width in inches per page per KDP official spec §5."""
        return _PAPER_SPINE_MULTIPLIERS[self.value]


class CoverFinish(StrEnum):
    """KDP cover laminate finish.

    Informational only — used at KDP submission, cannot be changed after publish.
    """

    GLOSSY = "GLOSSY"
    MATTE = "MATTE"


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
    trim_size: TrimSize = TrimSize.LETTER
    paper_type: PaperType = PaperType.WHITE
    cover_finish: CoverFinish = CoverFinish.MATTE
    book_format: BookFormat = BookFormat.PAPERBACK
    # M8: front matter and publishing metadata
    imprint: str = "ColorForge Studio"
    imprint_country: str = "United States"
    publication_year: int = Field(default_factory=lambda: datetime.now().year)
    include_dedication: bool = False
    dedication_text: str | None = None


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
