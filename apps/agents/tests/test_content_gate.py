"""Tests for ContentGate — deterministic logic, high coverage target."""

from __future__ import annotations

import pytest

from colorforge_agents.contracts.validation_report import (
    CoverAssessment,
    PageFlag,
    ValidationReport,
)
from colorforge_agents.exceptions import ContentGateBlocked
from colorforge_agents.gates.content_gate import ContentGate


def _report(
    verdict: str,
    flags_per_page: list[list[tuple[int, str]]] | None = None,
    cover_score: int = 85,
    pdf_ok: bool = True,
) -> ValidationReport:
    """Helper: build a ValidationReport quickly.

    flags_per_page: list of pages; each page is list of (severity, type) tuples.
    """
    action_map = {"pass": "publish", "needs_regen": "regenerate_pages", "fail": "kill"}
    per_page: list[list[PageFlag]] = []
    for page_idx, page_flags in enumerate(flags_per_page or []):
        per_page.append(
            [
                PageFlag(page_index=page_idx, type=t, severity=s, detail="test")  # type: ignore[arg-type]
                for s, t in page_flags
            ]
        )
    return ValidationReport(
        book_id="book-test",
        verdict=verdict,  # type: ignore[arg-type]
        per_page_flags=per_page,
        cover_assessment=CoverAssessment(readability_score=cover_score, issues=[]),
        pdf_spec_compliance=pdf_ok,
        pdf_spec_details=[],
        recommended_action=action_map[verdict],  # type: ignore[arg-type]
        critic_model_version="claude-sonnet-4-6",
    )


gate = ContentGate()


class TestPassVerdict:
    def test_clean_pass(self) -> None:
        report = _report("pass", flags_per_page=[])
        ok, reason = gate.passes(report)
        assert ok is True
        assert reason == ""

    def test_pass_with_minor_flags(self) -> None:
        report = _report("pass", flags_per_page=[[(2, "composition_off_center")]])
        ok, _ = gate.passes(report)
        assert ok is True

    def test_pass_with_many_minor_pages(self) -> None:
        # 5 pages each with severity-2 flag — still "pass" verdict
        flags = [[(2, "composition_off_center")] for _ in range(5)]
        report = _report("pass", flags_per_page=flags)
        ok, _ = gate.passes(report)
        assert ok is True


class TestNeedsRegenVerdict:
    def test_needs_regen_one_critical_page_passes(self) -> None:
        # 1 page with severity-4 flag — needs_regen but only 1 critical page → passes gate
        report = _report("needs_regen", flags_per_page=[[(4, "artifact_detected")]])
        ok, _ = gate.passes(report)
        assert ok is True

    def test_needs_regen_two_critical_pages_blocked(self) -> None:
        # 2 pages with severity-4 flags → blocked
        flags = [[(4, "artifact_detected")], [(4, "shading_detected")]]
        report = _report("needs_regen", flags_per_page=flags)
        with pytest.raises(ContentGateBlocked) as exc_info:
            gate.passes(report)
        assert exc_info.value.book_id == "book-test"
        assert "needs_regen" in str(exc_info.value)

    def test_needs_regen_three_critical_pages_blocked(self) -> None:
        flags = [[(4, "artifact_detected")], [(5, "text_contamination")], [(4, "color_detected")]]
        report = _report("needs_regen", flags_per_page=flags)
        with pytest.raises(ContentGateBlocked):
            gate.passes(report)

    def test_needs_regen_mixed_severity_passes(self) -> None:
        # severity-3 flags don't count as critical
        flags = [[(3, "composition_off_center")], [(3, "subject_too_small")]]
        report = _report("needs_regen", flags_per_page=flags)
        ok, _ = gate.passes(report)
        assert ok is True


class TestFailVerdict:
    def test_fail_always_blocked(self) -> None:
        report = _report("fail", flags_per_page=[])
        with pytest.raises(ContentGateBlocked) as exc_info:
            gate.passes(report)
        assert exc_info.value.verdict == "fail"

    def test_fail_blocked_with_no_flags(self) -> None:
        report = _report("fail", flags_per_page=[], cover_score=30, pdf_ok=False)
        with pytest.raises(ContentGateBlocked):
            gate.passes(report)

    def test_fail_exception_contains_book_id(self) -> None:
        report = _report("fail")
        with pytest.raises(ContentGateBlocked) as exc_info:
            gate.passes(report)
        assert exc_info.value.book_id == "book-test"
        assert "book-test" in str(exc_info.value)


class TestEdgeCases:
    def test_empty_per_page_flags_pass(self) -> None:
        report = _report("pass", flags_per_page=[])
        ok, _ = gate.passes(report)
        assert ok is True

    def test_needs_regen_exactly_one_severity4_passes(self) -> None:
        flags = [[(4, "double_lines")]]
        report = _report("needs_regen", flags_per_page=flags)
        ok, _ = gate.passes(report)
        assert ok is True

    def test_needs_regen_severity5_on_single_page_passes(self) -> None:
        # severity-5 on 1 page — only 1 critical page, still passes gate
        flags = [[(5, "text_contamination")]]
        report = _report("needs_regen", flags_per_page=flags)
        ok, _ = gate.passes(report)
        assert ok is True

    def test_content_gate_blocked_str(self) -> None:
        exc = ContentGateBlocked(book_id="abc", verdict="fail", reason="cover too dark")
        assert "abc" in str(exc)
        assert "fail" in str(exc)
