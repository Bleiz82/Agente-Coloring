"""Listing contract — output of SEO Listing agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ListingContract(BaseModel):
    """KDP listing data for a book."""

    book_id: str
    title: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=200)
    keywords: list[str] = Field(min_length=7, max_length=7)
    description_html: str = Field(max_length=4000)
    bisac_codes: list[str] = Field(min_length=1, max_length=3)
    price_usd: float = Field(gt=0, le=250)
    price_eur: float | None = Field(default=None, gt=0)
    price_gbp: float | None = Field(default=None, gt=0)
    ai_disclosure: Literal[True] = True
    publication_target_date: datetime | None = None


LISTING_EXAMPLE = ListingContract(
    book_id="770e8400-e29b-41d4-a716-446655440002",
    title="Ocean Mandala Coloring Book for Adults: 75 Relaxing Sea-Themed Designs",
    subtitle="Stress Relief Coloring with Intricate Ocean Waves, Seashells & Coral Mandalas",
    keywords=[
        "ocean coloring book adults",
        "mandala coloring book stress relief",
        "sea themed adult coloring",
        "relaxation coloring pages women",
        "intricate mandala designs",
        "ocean wave patterns coloring",
        "gift coloring book teens adults",
    ],
    description_html=(
        "<b>Dive Into Calm with 75 Stunning Ocean Mandalas</b>"
        "<br><br>Each page features a unique design."
    ),
    bisac_codes=["ART015000", "CRA019000"],
    price_usd=7.99,
    price_eur=7.49,
    price_gbp=6.49,
    ai_disclosure=True,
    publication_target_date=datetime.fromisoformat("2026-05-05T00:00:00+00:00"),
)
