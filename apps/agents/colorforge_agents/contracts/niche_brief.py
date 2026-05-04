"""NicheBrief contract — output of Deep Scout."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PainPoint(BaseModel):
    """A pain point extracted from 1-2 star reviews."""

    text: str
    source_review_ids: list[str]
    severity: int = Field(ge=1, le=5)
    category: str


class StyleClassification(BaseModel):
    """A visual style identified in the niche."""

    name: str
    prevalence: float = Field(ge=0, le=100)
    examples: list[str]


class Differentiator(BaseModel):
    """A suggested differentiator for this niche."""

    description: str
    rationale: str
    estimated_impact: Literal["low", "medium", "high"]


class NicheBrief(BaseModel):
    """Enriched niche analysis from Deep Scout."""

    niche_id: str
    category_path: list[str] = Field(min_length=1)
    primary_keyword: str = Field(min_length=1)
    profitability_score: float = Field(ge=0, le=100)
    pain_points: list[PainPoint]
    style_classifications: list[StyleClassification]
    differentiators: list[Differentiator]
    vision_analysis_summary: str
    qdrant_vector_id: str | None = None
    created_at: datetime


NICHE_BRIEF_EXAMPLE = NicheBrief(
    niche_id="550e8400-e29b-41d4-a716-446655440000",
    category_path=["Books", "Crafts, Hobbies & Home", "Coloring Books for Grown-Ups", "Mandala"],
    primary_keyword="ocean mandala coloring book",
    profitability_score=68.4,
    pain_points=[
        PainPoint(
            text="Lines are too thin and bleed through the page",
            source_review_ids=["rev-001", "rev-015", "rev-023"],
            severity=4,
            category="line_quality",
        ),
        PainPoint(
            text="Only 30 unique designs, rest are duplicates",
            source_review_ids=["rev-008", "rev-042"],
            severity=3,
            category="subject_variety",
        ),
    ],
    style_classifications=[
        StyleClassification(
            name="geometric-mandala", prevalence=65, examples=["B0EX01", "B0EX02"]
        ),
        StyleClassification(
            name="organic-floral-mandala", prevalence=25, examples=["B0EX03"]
        ),
    ],
    differentiators=[
        Differentiator(
            description="Use thick bold lines (2-3px) to prevent bleed-through",
            rationale="Top pain point in 1-2 star reviews",
            estimated_impact="high",
        ),
    ],
    vision_analysis_summary="Dominant style is geometric mandala with thin lines.",
    qdrant_vector_id="vec-niche-001",
    created_at=datetime.fromisoformat("2026-04-29T03:30:00+00:00"),
)
