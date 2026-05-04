"""NicheCandidate contract — output of Niche Hunter."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompetitorSnap(BaseModel):
    """Snapshot of a single competitor book from Amazon Bestsellers."""

    asin: str
    title: str
    author: str
    bsr: int = Field(gt=0)
    price: float = Field(gt=0)
    review_count: int = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    publication_date: str | None = None
    page_count: int | None = Field(default=None, gt=0)


class ProfitabilityBreakdown(BaseModel):
    """8 normalized signals (0-1) plus weighted total (0-100)."""

    demand: float = Field(ge=0, le=1)
    price: float = Field(ge=0, le=1)
    competition: float = Field(ge=0, le=1)
    quality_gap: float = Field(ge=0, le=1)
    trend: float = Field(ge=0, le=1)
    seasonality: float = Field(ge=0, le=1)
    catalog_fit: float = Field(ge=0, le=1)
    saturation: float = Field(ge=0, le=1)
    weighted_total: float = Field(ge=0, le=100)


class TrendSignal(BaseModel):
    """Trend data from Google Trends, Pinterest, Amazon Suggest."""

    google_trends_90d_slope: float
    pinterest_search_velocity: float | None = None
    amazon_suggest_count: int | None = Field(default=None, ge=0)


class NicheCandidate(BaseModel):
    """Full output of Niche Hunter for a single niche."""

    category_path: list[str] = Field(min_length=1)
    primary_keyword: str = Field(min_length=1)
    top_competitors: list[CompetitorSnap]
    profitability: ProfitabilityBreakdown
    trend_signals: TrendSignal
    scan_timestamp: datetime
    raw_html_hashes: list[str] | None = None


NICHE_CANDIDATE_EXAMPLE = NicheCandidate(
    category_path=[
        "Books",
        "Crafts, Hobbies & Home",
        "Coloring Books for Grown-Ups",
        "Mandala",
    ],
    primary_keyword="ocean mandala coloring book",
    top_competitors=[
        CompetitorSnap(
            asin="B0EXAMPLE01",
            title="Ocean Mandala Coloring Book for Adults",
            author="Jane Artist",
            bsr=15420,
            price=7.99,
            review_count=342,
            rating=4.3,
            publication_date="2025-06-15",
            page_count=75,
        ),
    ],
    profitability=ProfitabilityBreakdown(
        demand=0.72,
        price=0.65,
        competition=0.45,
        quality_gap=0.80,
        trend=0.55,
        seasonality=0.90,
        catalog_fit=0.85,
        saturation=0.40,
        weighted_total=68.4,
    ),
    trend_signals=TrendSignal(
        google_trends_90d_slope=0.12,
        pinterest_search_velocity=0.35,
        amazon_suggest_count=8,
    ),
    scan_timestamp=datetime.fromisoformat("2026-04-29T02:00:00+00:00"),
)
