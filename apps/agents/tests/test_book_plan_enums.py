"""Tests for BookPlan enums — TrimSize, PaperType, CoverFinish, BookFormat."""

from __future__ import annotations

import pytest

from colorforge_agents.contracts.book_plan import (
    BOOK_PLAN_EXAMPLE,
    BookFormat,
    BookPlan,
    CoverFinish,
    PaperType,
    TrimSize,
)


class TestTrimSize:
    @pytest.mark.parametrize(
        ("trim", "expected_w", "expected_h"),
        [
            (TrimSize.LETTER, 8.5, 11.0),
            (TrimSize.SQUARE_LARGE, 8.5, 8.5),
            (TrimSize.KIDS, 8.0, 10.0),
            (TrimSize.INTERMEDIATE, 7.0, 10.0),
            (TrimSize.POCKET, 6.0, 9.0),
        ],
    )
    def test_trim_size_dimensions(
        self, trim: TrimSize, expected_w: float, expected_h: float
    ) -> None:
        assert trim.width_inches == pytest.approx(expected_w)
        assert trim.height_inches == pytest.approx(expected_h)

    def test_trim_size_values_are_strings(self) -> None:
        for trim in TrimSize:
            assert isinstance(trim.value, str)

    def test_trim_size_default_is_letter(self) -> None:
        # BOOK_PLAN_EXAMPLE is constructed without explicit trim_size → must default to LETTER
        assert BOOK_PLAN_EXAMPLE.trim_size == TrimSize.LETTER

    def test_trim_size_round_trip(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"trim_size": TrimSize.KIDS})
        json_str = plan.model_dump_json()
        restored = BookPlan.model_validate_json(json_str)
        assert restored.trim_size == TrimSize.KIDS
        assert restored.trim_size.width_inches == 8.0
        assert restored.trim_size.height_inches == 10.0

    def test_all_trim_sizes_have_positive_dimensions(self) -> None:
        for trim in TrimSize:
            assert trim.width_inches > 0
            assert trim.height_inches > 0


class TestPaperType:
    @pytest.mark.parametrize(
        ("paper", "expected_multiplier"),
        [
            (PaperType.WHITE, 0.002252),
            (PaperType.CREAM, 0.0025),
            (PaperType.PREMIUM_COLOR, 0.002347),
            (PaperType.STANDARD_COLOR, 0.002252),
        ],
    )
    def test_paper_type_spine_multipliers(
        self, paper: PaperType, expected_multiplier: float
    ) -> None:
        assert paper.spine_multiplier == pytest.approx(expected_multiplier)

    def test_cream_has_largest_multiplier(self) -> None:
        multipliers = [p.spine_multiplier for p in PaperType]
        assert PaperType.CREAM.spine_multiplier == max(multipliers)

    def test_paper_type_default_is_white(self) -> None:
        assert BOOK_PLAN_EXAMPLE.paper_type == PaperType.WHITE

    def test_paper_type_round_trip(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"paper_type": PaperType.CREAM})
        restored = BookPlan.model_validate_json(plan.model_dump_json())
        assert restored.paper_type == PaperType.CREAM
        assert restored.paper_type.spine_multiplier == pytest.approx(0.0025)


class TestCoverFinish:
    def test_cover_finish_default(self) -> None:
        assert BOOK_PLAN_EXAMPLE.cover_finish == CoverFinish.MATTE

    def test_cover_finish_glossy(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"cover_finish": CoverFinish.GLOSSY})
        assert plan.cover_finish == CoverFinish.GLOSSY

    def test_cover_finish_round_trip(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"cover_finish": CoverFinish.GLOSSY})
        restored = BookPlan.model_validate_json(plan.model_dump_json())
        assert restored.cover_finish == CoverFinish.GLOSSY

    def test_cover_finish_values(self) -> None:
        assert CoverFinish.GLOSSY.value == "GLOSSY"
        assert CoverFinish.MATTE.value == "MATTE"


class TestBookFormat:
    def test_book_format_default_is_paperback(self) -> None:
        assert BOOK_PLAN_EXAMPLE.book_format == BookFormat.PAPERBACK

    def test_book_format_hardcover(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"book_format": BookFormat.HARDCOVER})
        assert plan.book_format == BookFormat.HARDCOVER

    def test_book_format_round_trip(self) -> None:
        plan = BOOK_PLAN_EXAMPLE.model_copy(update={"book_format": BookFormat.HARDCOVER})
        restored = BookPlan.model_validate_json(plan.model_dump_json())
        assert restored.book_format == BookFormat.HARDCOVER

    def test_book_format_values(self) -> None:
        assert BookFormat.PAPERBACK.value == "PAPERBACK"
        assert BookFormat.HARDCOVER.value == "HARDCOVER"
