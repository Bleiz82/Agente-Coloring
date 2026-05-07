"""BookDraft contract — output of Generator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DraftPage(BaseModel):
    """A single generated page within a BookDraft."""

    index: int = Field(ge=0)
    image_path: str
    prompt_used: str
    validation_status: Literal["pending", "pass", "warn", "fail"]


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""

    generator_model_version: str
    total_generation_time_ms: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    pages_generated: int = Field(ge=0)
    pages_regenerated: int = Field(ge=0)


class BookDraft(BaseModel):
    """Complete generated book draft with manuscript and cover PDFs."""

    book_id: str
    manuscript_pdf_path: str = Field(min_length=1)
    cover_pdf_path: str = Field(min_length=1)
    pages: list[DraftPage] = Field(min_length=1)
    spine_width_inches: float = Field(gt=0)
    total_pages: int = Field(gt=0)
    generation_metadata: GenerationMetadata
    # M8: cover compositor and front matter fields
    title: str = Field(default="", description="Book title — matches BookPlan target_keyword title")
    subtitle: str | None = Field(default=None, description="Optional subtitle")
    author: str = Field(default="", description="Author name — matches BookPlan.brand_author")

    @property
    def page_count(self) -> int:
        """Alias for total_pages — used by CoverCompositor and FrontMatterAssembler."""
        return self.total_pages


BOOK_DRAFT_EXAMPLE = BookDraft(
    book_id="770e8400-e29b-41d4-a716-446655440002",
    title="Ocean Mandala Coloring Book",
    author="Stefano Demuru",
    manuscript_pdf_path="/var/colorforge/assets/stefano-main/770e8400/manuscript.pdf",
    cover_pdf_path="/var/colorforge/assets/stefano-main/770e8400/cover.pdf",
    pages=[
        DraftPage(
            index=0,
            image_path="/var/colorforge/assets/stefano-main/770e8400/pages/page_000.png",
            prompt_used="Black and white coloring book line art for adults...",
            validation_status="pass",
        ),
    ],
    spine_width_inches=0.169,
    total_pages=75,
    generation_metadata=GenerationMetadata(
        generator_model_version="gemini-3-1-flash-image",
        total_generation_time_ms=900000,
        total_cost_usd=2.93,
        pages_generated=75,
        pages_regenerated=3,
    ),
)
