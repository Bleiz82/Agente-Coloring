"""Critic agent — validates BookDraft via vision and produces ValidationReport."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.validation_report import (
    CoverAssessment,
    PageFlag,
    ValidationReport,
)
from colorforge_agents.config.models import CRITIC_MODEL
from colorforge_agents.critic.vision_checker import VisionChecker


class CriticCore:
    """Orchestrates vision checking and produces a ValidationReport."""

    def __init__(self, vision_checker: VisionChecker, prisma: Any) -> None:
        self._vision = vision_checker
        self._prisma = prisma

    async def critique(self, draft: BookDraft) -> ValidationReport:
        """Run full validation: pages → cover → PDF specs → verdict."""
        logger.info("Critic starting validation for book_id={}", draft.book_id)

        # 1. Check all pages
        page_paths = [Path(p.image_path) for p in draft.pages]
        per_page_flags = await self._vision.check_pages(page_paths)

        # 2. Check cover
        cover_path = Path(draft.cover_pdf_path).with_suffix(".png")
        if not cover_path.exists():
            # Try the raw cover png sibling
            cover_path = Path(draft.cover_pdf_path).parent / "cover.png"
        cover_assessment = await self._vision.check_cover(cover_path)

        # 3. Check PDF specs (pypdf)
        pdf_compliant, pdf_issues = await self._vision.check_pdf_specs(
            Path(draft.manuscript_pdf_path), Path(draft.cover_pdf_path)
        )

        # 4. Determine verdict
        verdict, recommended_action = _determine_verdict(
            per_page_flags, cover_assessment, pdf_compliant, draft.total_pages
        )

        report = ValidationReport(
            book_id=draft.book_id,
            verdict=verdict,
            per_page_flags=per_page_flags,
            cover_assessment=cover_assessment,
            pdf_spec_compliance=pdf_compliant,
            pdf_spec_details=pdf_issues,
            recommended_action=recommended_action,
            critic_model_version=CRITIC_MODEL,
        )

        await self._persist(report)
        logger.info(
            "Critic verdict={} book_id={} cover_score={}",
            verdict,
            draft.book_id,
            cover_assessment.readability_score,
        )
        return report

    async def _persist(self, report: ValidationReport) -> None:
        try:
            await self._prisma.validation_create(
                data={
                    "bookId": report.book_id,
                    "verdict": report.verdict,
                    "perPageFlags": [
                        [f.model_dump() for f in flags] for flags in report.per_page_flags
                    ],
                    "coverReadabilityScore": report.cover_assessment.readability_score,
                    "coverIssues": report.cover_assessment.issues,
                    "pdfSpecCompliance": report.pdf_spec_compliance,
                    "pdfSpecDetails": report.pdf_spec_details,
                    "recommendedAction": report.recommended_action,
                    "criticModelVersion": report.critic_model_version,
                    "createdAt": datetime.now(tz=UTC).isoformat(),
                }
            )
        except Exception as exc:
            logger.error("DB write failed for ValidationReport {}: {}", report.book_id, exc)


def _determine_verdict(
    per_page_flags: list[list[PageFlag]],
    cover: CoverAssessment,
    pdf_compliant: bool,
    total_pages: int,
) -> tuple[Any, Any]:
    """Compute verdict and recommended_action from validation data."""
    from typing import Literal

    all_flags = [f for page_flags in per_page_flags for f in page_flags]
    has_critical = any(f.severity >= 5 for f in all_flags)
    has_major = any(f.severity >= 4 for f in all_flags)
    cover_poor = cover.readability_score < 50
    flagged_pages = sum(1 for page_flags in per_page_flags if page_flags)
    minor_fraction = flagged_pages / max(total_pages, 1)

    if has_critical or cover_poor or not pdf_compliant:
        verdict: Literal["pass", "fail", "needs_regen"] = "fail"
        action: Literal["publish", "regenerate_pages", "kill"] = "kill"
    elif has_major or minor_fraction > 0.10:
        verdict = "needs_regen"
        action = "regenerate_pages"
    else:
        verdict = "pass"
        action = "publish"

    return verdict, action
