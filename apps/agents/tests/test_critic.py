"""Tests for CriticCore, VisionChecker JSON parsing, and verdict logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.validation_report import (
    CoverAssessment,
    PageFlag,
    ValidationReport,
)
from colorforge_agents.critic.critic import CriticCore, _determine_verdict
from colorforge_agents.critic.vision_checker import VisionChecker
from colorforge_agents.exceptions import CriticError


def _draft(n_pages: int = 3, tmp_path: Path | None = None) -> BookDraft:
    base = tmp_path or Path("/tmp/test-book")
    return BookDraft(
        book_id="book-abc",
        manuscript_pdf_path=str(base / "manuscript.pdf"),
        cover_pdf_path=str(base / "cover.pdf"),
        pages=[
            DraftPage(
                index=i,
                image_path=str(base / f"page_{i:03d}.png"),
                prompt_used=f"prompt {i}",
                validation_status="pass",
            )
            for i in range(n_pages)
        ],
        spine_width_inches=0.169,
        total_pages=n_pages,
        generation_metadata=GenerationMetadata(
            generator_model_version="gemini-test",
            total_generation_time_ms=1000,
            total_cost_usd=0.0,
            pages_generated=n_pages,
            pages_regenerated=0,
        ),
    )


class _MockPrisma:
    async def validation_create(self, **_: Any) -> None:
        pass


class TestDetermineVerdict:
    def _flags(self, sev: int, count: int = 1) -> list[list[PageFlag]]:
        page_flags = [
            PageFlag(page_index=0, type="artifact_detected", severity=sev, detail="test")
            for _ in range(count)
        ]
        return [page_flags]

    def test_no_flags_is_pass(self) -> None:
        v, a = _determine_verdict([], CoverAssessment(readability_score=80, issues=[]), True, 10)
        assert v == "pass"
        assert a == "publish"

    def test_severity5_is_fail(self) -> None:
        v, a = _determine_verdict(
            self._flags(5), CoverAssessment(readability_score=80, issues=[]), True, 10
        )
        assert v == "fail"
        assert a == "kill"

    def test_poor_cover_is_fail(self) -> None:
        cover = CoverAssessment(readability_score=30, issues=["blurry"])
        v, a = _determine_verdict([], cover, True, 10)
        assert v == "fail"
        assert a == "kill"

    def test_pdf_non_compliant_is_fail(self) -> None:
        v, a = _determine_verdict([], CoverAssessment(readability_score=80, issues=[]), False, 10)
        assert v == "fail"
        assert a == "kill"

    def test_severity4_is_needs_regen(self) -> None:
        v, a = _determine_verdict(
            self._flags(4), CoverAssessment(readability_score=80, issues=[]), True, 10
        )
        assert v == "needs_regen"
        assert a == "regenerate_pages"

    def test_many_flagged_pages_is_needs_regen(self) -> None:
        # 3 out of 5 pages flagged = 60% > 10%
        flags = [[PageFlag(page_index=i, type="composition_off_center", severity=2, detail="x")]
                 for i in range(3)]
        flags += [[], []]
        v, a = _determine_verdict(flags, CoverAssessment(readability_score=80, issues=[]), True, 5)
        assert v == "needs_regen"
        assert a == "regenerate_pages"

    def test_one_flagged_page_in_ten_is_pass(self) -> None:
        flags = [[PageFlag(page_index=0, type="composition_off_center", severity=2, detail="x")]]
        flags += [[] for _ in range(9)]
        v, a = _determine_verdict(flags, CoverAssessment(readability_score=80, issues=[]), True, 10)
        assert v == "pass"
        assert a == "publish"


class TestVisionCheckerPageParsing:
    def _mock_client(self, response_json: list[list[dict[str, Any]]]) -> Any:
        client = AsyncMock()
        client.messages.create.return_value.content = [
            type("Block", (), {"text": json.dumps(response_json)})()
        ]
        return client

    async def test_empty_pages_returns_empty(self) -> None:
        checker = VisionChecker(AsyncMock())
        result = await checker.check_pages([])
        assert result == []

    async def test_clean_pages_no_flags(self, tmp_path: Path) -> None:
        # Write placeholder PNGs (1×1 white)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
            "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
        )
        paths = []
        for i in range(2):
            p = tmp_path / f"page_{i}.png"
            p.write_bytes(png)
            paths.append(p)

        client = self._mock_client([[], []])
        checker = VisionChecker(client)
        result = await checker.check_pages(paths)
        assert result == [[], []]

    async def test_flags_parsed_correctly(self, tmp_path: Path) -> None:
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
            "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
        )
        p = tmp_path / "page_0.png"
        p.write_bytes(png)

        flag = {"type": "text_contamination", "severity": 5, "detail": "numbers visible"}
        client = self._mock_client([[flag]])
        checker = VisionChecker(client)
        result = await checker.check_pages([p])
        assert len(result) == 1
        assert len(result[0]) == 1
        flag = result[0][0]
        assert flag.type == "text_contamination"
        assert flag.severity == 5
        assert flag.page_index == 0

    async def test_bad_json_raises_critic_error(self, tmp_path: Path) -> None:
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
            "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
        )
        p = tmp_path / "page_0.png"
        p.write_bytes(png)

        client = AsyncMock()
        client.messages.create.return_value.content = [
            type("Block", (), {"text": "not valid json"})()
        ]
        checker = VisionChecker(client)
        with pytest.raises(CriticError):
            await checker.check_pages([p])


class TestVisionCheckerCover:
    def _mock_client_cover(self, score: int, issues: list[str]) -> Any:
        payload = {"readability_score": score, "issues": issues}
        client = AsyncMock()
        client.messages.create.return_value.content = [
            type("Block", (), {"text": json.dumps(payload)})()
        ]
        return client

    async def test_cover_assessment_parsed(self, tmp_path: Path) -> None:
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
            "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
        )
        cover = tmp_path / "cover.png"
        cover.write_bytes(png)

        checker = VisionChecker(self._mock_client_cover(85, []))
        result = await checker.check_cover(cover)
        assert result.readability_score == 85
        assert result.issues == []

    async def test_cover_bad_json_raises(self, tmp_path: Path) -> None:
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
            "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
        )
        cover = tmp_path / "cover.png"
        cover.write_bytes(png)

        client = AsyncMock()
        client.messages.create.return_value.content = [
            type("Block", (), {"text": "broken"})()
        ]
        checker = VisionChecker(client)
        with pytest.raises(CriticError):
            await checker.check_cover(cover)


class TestCriticCore:
    def _mock_vision_checker(
        self,
        page_flags: list[list[PageFlag]] | None = None,
        cover_score: int = 85,
    ) -> VisionChecker:
        checker = AsyncMock(spec=VisionChecker)
        checker.check_pages.return_value = page_flags or [[] for _ in range(3)]
        checker.check_cover.return_value = CoverAssessment(readability_score=cover_score, issues=[])
        checker.check_pdf_specs.return_value = (True, [])
        return checker

    async def test_returns_validation_report(self, tmp_path: Path) -> None:
        core = CriticCore(self._mock_vision_checker(), _MockPrisma())
        report = await core.critique(_draft(3, tmp_path))
        assert isinstance(report, ValidationReport)

    async def test_clean_draft_passes(self, tmp_path: Path) -> None:
        core = CriticCore(self._mock_vision_checker(), _MockPrisma())
        report = await core.critique(_draft(3, tmp_path))
        assert report.verdict == "pass"
        assert report.recommended_action == "publish"

    async def test_critical_flag_fails(self, tmp_path: Path) -> None:
        flags = [[PageFlag(page_index=0, type="text_contamination", severity=5, detail="text")]]
        core = CriticCore(self._mock_vision_checker(page_flags=flags), _MockPrisma())
        report = await core.critique(_draft(1, tmp_path))
        assert report.verdict == "fail"

    async def test_poor_cover_fails(self, tmp_path: Path) -> None:
        core = CriticCore(self._mock_vision_checker(cover_score=30), _MockPrisma())
        report = await core.critique(_draft(3, tmp_path))
        assert report.verdict == "fail"

    async def test_book_id_preserved(self, tmp_path: Path) -> None:
        core = CriticCore(self._mock_vision_checker(), _MockPrisma())
        report = await core.critique(_draft(3, tmp_path))
        assert report.book_id == "book-abc"
