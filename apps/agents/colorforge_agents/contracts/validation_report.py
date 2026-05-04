"""ValidationReport contract — output of Critic."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PageFlag(BaseModel):
    """A single validation flag on a page."""

    page_index: int = Field(ge=0)
    type: Literal[
        "text_contamination",
        "shading_detected",
        "color_detected",
        "double_lines",
        "anatomy_malformed",
        "composition_off_center",
        "subject_too_small",
        "watermark_detected",
        "artifact_detected",
        "prompt_mismatch",
    ]
    severity: int = Field(ge=1, le=5)
    detail: str


class CoverAssessment(BaseModel):
    """Cover validation assessment."""

    readability_score: int = Field(ge=0, le=100)
    issues: list[str]


class ValidationReport(BaseModel):
    """Full validation report from the Critic agent."""

    book_id: str
    verdict: Literal["pass", "fail", "needs_regen"]
    per_page_flags: list[list[PageFlag]]
    cover_assessment: CoverAssessment
    pdf_spec_compliance: bool
    pdf_spec_details: list[str]
    recommended_action: Literal["publish", "regenerate_pages", "kill"]
    critic_model_version: str


VALIDATION_REPORT_EXAMPLE = ValidationReport(
    book_id="770e8400-e29b-41d4-a716-446655440002",
    verdict="pass",
    per_page_flags=[
        [],
        [
            PageFlag(
                page_index=1,
                type="composition_off_center",
                severity=2,
                detail="Subject slightly left of center, minor issue",
            ),
        ],
    ],
    cover_assessment=CoverAssessment(readability_score=85, issues=[]),
    pdf_spec_compliance=True,
    pdf_spec_details=[],
    recommended_action="publish",
    critic_model_version="claude-sonnet-4-6-20260301",
)
