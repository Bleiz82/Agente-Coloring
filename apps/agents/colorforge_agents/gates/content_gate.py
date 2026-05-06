"""Content Gate — sits between Generator and SEO Listing."""

from __future__ import annotations

from colorforge_agents.contracts.validation_report import ValidationReport
from colorforge_agents.exceptions import ContentGateBlocked

_CRITICAL_SEVERITY = 4  # severity >= 4 is a "critical" flag


class ContentGate:
    """Passes BookDraft only if ValidationReport meets quality bar."""

    def passes(self, report: ValidationReport) -> tuple[bool, str]:
        """Return (True, "") if the draft passes, or raise ContentGateBlocked if blocked.

        Rules (in priority order):
        1. verdict == "fail" → always blocked
        2. verdict == "needs_regen" with ≥2 pages having severity-4+ flags → blocked
        3. Otherwise → passes (verdict "pass" or light "needs_regen")
        """
        if report.verdict == "fail":
            reason = (
                f"verdict=fail cover_score={report.cover_assessment.readability_score} "
                f"pdf_ok={report.pdf_spec_compliance}"
            )
            raise ContentGateBlocked(
                book_id=report.book_id, verdict=report.verdict, reason=reason
            )

        if report.verdict == "needs_regen":
            critical_pages = sum(
                1
                for page_flags in report.per_page_flags
                if any(f.severity >= _CRITICAL_SEVERITY for f in page_flags)
            )
            if critical_pages >= 2:
                reason = f"needs_regen with {critical_pages} pages having severity≥4 flags"
                raise ContentGateBlocked(
                    book_id=report.book_id, verdict=report.verdict, reason=reason
                )

        return True, ""
