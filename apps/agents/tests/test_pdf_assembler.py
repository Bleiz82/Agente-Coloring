"""Tests for PDFAssembler — KDP dimensions, gutter, outside margin, spine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from colorforge_agents.contracts.book_plan import PaperType, TrimSize
from colorforge_agents.exceptions import PDFAssemblyError
from colorforge_agents.generator.pdf_assembler import (
    _OUTSIDE_MARGIN_MIN_BLEED_IN,
    _OUTSIDE_MARGIN_MIN_NO_BLEED_IN,
    BLEED_IN,
    PT_PER_IN,
    SPINE_PER_PAGE,
    TRIM_H_IN,
    TRIM_W_IN,
    PDFAssembler,
    PDFAssemblyResult,
    _compute_gutter_inches,
    _validate_outside_margin,
)


def _make_white_png(tmp_path: Path, name: str = "page.png", dpi: int = 300) -> Path:
    """Write a minimal white 8.5x11 PNG to tmp_path at the given DPI."""
    try:
        from PIL import Image

        img = Image.new("L", (2550, 3300), color=255)
        out = tmp_path / name
        img.save(str(out), format="PNG", dpi=(dpi, dpi))
        return out
    except ImportError:
        # Pillow not available in this env — write a valid 1×1 PNG
        png_bytes = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001"
            "0806000000 1f15c489000000 0a49444154789c62600000000200"
            "01e221bc33000000 0049454e44ae426082".replace(" ", "")
        )
        out = tmp_path / name
        out.write_bytes(png_bytes)
        return out


assembler = PDFAssembler()


class TestSpineFormula:
    def test_spine_75_pages(self) -> None:
        assert abs(assembler.spine_width_inches(75) - 75 * SPINE_PER_PAGE) < 1e-9

    def test_spine_100_pages(self) -> None:
        assert abs(assembler.spine_width_inches(100) - 100 * SPINE_PER_PAGE) < 1e-9

    def test_spine_proportional(self) -> None:
        assert assembler.spine_width_inches(200) == pytest.approx(
            assembler.spine_width_inches(100) * 2, abs=1e-9
        )

    def test_spine_20_pages_min(self) -> None:
        assert assembler.spine_width_inches(20) > 0

    def test_spine_uses_paper_type_multiplier(self) -> None:
        cream = PDFAssembler(paper_type=PaperType.CREAM)
        white = PDFAssembler(paper_type=PaperType.WHITE)
        assert cream.spine_width_inches(100) == pytest.approx(100 * 0.0025)
        assert white.spine_width_inches(100) == pytest.approx(100 * 0.002252)
        assert cream.spine_width_inches(100) > white.spine_width_inches(100)


class TestGutterScaling:
    """K02 — _compute_gutter_inches must follow KDP official table (§4)."""

    @pytest.mark.parametrize(
        ("page_count", "expected"),
        [
            # ≤ 150 → 0.375"
            (1, 0.375),
            (24, 0.375),
            (100, 0.375),
            (150, 0.375),
            # 151–300 → 0.500"
            (151, 0.500),
            (200, 0.500),
            (300, 0.500),
            # 301–500 → 0.625"
            (301, 0.625),
            (400, 0.625),
            (500, 0.625),
            # 501–700 → 0.750"
            (501, 0.750),
            (600, 0.750),
            (700, 0.750),
            # 701–828 → 0.875"
            (701, 0.875),
            (800, 0.875),
            (828, 0.875),
        ],
    )
    def test_gutter_correct_per_kdp_spec(self, page_count: int, expected: float) -> None:
        assert _compute_gutter_inches(page_count) == pytest.approx(expected)


class TestOutsideMargin:
    """K03 — _validate_outside_margin raises when outside margin < 0.375"."""

    def test_exact_minimum_passes(self) -> None:
        # outside_margin = trim_w - gutter - img_w = 8.5 - 0.375 - 7.75 = 0.375"
        _validate_outside_margin(7.75, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=True)

    def test_margin_above_minimum_passes(self) -> None:
        _validate_outside_margin(7.0, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=True)

    def test_outside_margin_too_small_raises(self) -> None:
        # img_w = 8.5 - 0.375 - 0.001 = 8.124" → outside_margin = 0.001" < 0.375"
        with pytest.raises(PDFAssemblyError, match="outside margin"):
            _validate_outside_margin(8.124, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=True)

    def test_error_includes_page_index(self) -> None:
        with pytest.raises(PDFAssemblyError, match="Page 5"):
            _validate_outside_margin(
                8.0, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=True, page_index=5
            )

    def test_no_bleed_uses_lower_minimum(self) -> None:
        # outside_margin = 8.5 - 0.375 - 7.875 = 0.25" — exact no-bleed minimum
        _validate_outside_margin(
            7.875, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=False
        )

    def test_no_bleed_too_small_raises(self) -> None:
        # margin = 8.5 - 0.375 - 7.876 = 0.249" < 0.25"
        with pytest.raises(PDFAssemblyError):
            _validate_outside_margin(
                7.876, 11.0, 8.5, 11.0, gutter_in=0.375, has_bleed=False
            )

    def test_module_constants_correct(self) -> None:
        assert _OUTSIDE_MARGIN_MIN_BLEED_IN == 0.375
        assert _OUTSIDE_MARGIN_MIN_NO_BLEED_IN == 0.25


class TestManuscriptDimensions:
    def test_correct_page_size_in_result(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path)
        out = tmp_path / "ms.pdf"
        result = assembler.assemble_manuscript([page], out)
        expected_w = round((TRIM_W_IN + BLEED_IN) * PT_PER_IN, 1)   # 621.0 pt
        expected_h = round((TRIM_H_IN + 2 * BLEED_IN) * PT_PER_IN, 1)  # 810.0 pt
        assert abs(result.page_width_pts - expected_w) < 1.0
        assert abs(result.page_height_pts - expected_h) < 1.0

    def test_page_count_matches_input(self, tmp_path: Path) -> None:
        pages = [_make_white_png(tmp_path, f"p{i}.png") for i in range(3)]
        out = tmp_path / "ms.pdf"
        result = assembler.assemble_manuscript(pages, out)
        assert result.page_count == 3

    def test_output_path_in_result(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path)
        out = tmp_path / "ms.pdf"
        result = assembler.assemble_manuscript([page], out)
        assert result.output_path == str(out)
        assert Path(result.output_path).exists()

    def test_pdf_readable_by_pypdf(self, tmp_path: Path) -> None:
        try:
            from pypdf import PdfReader
        except ImportError:
            pytest.skip("pypdf not installed")
        page = _make_white_png(tmp_path)
        out = tmp_path / "ms.pdf"
        assembler.assemble_manuscript([page], out)
        reader = PdfReader(str(out))
        assert len(reader.pages) == 1
        w = float(reader.pages[0].mediabox.width)
        h = float(reader.pages[0].mediabox.height)
        assert abs(w - 621.0) < 2.0
        assert abs(h - 810.0) < 2.0

    def test_raises_on_empty_pages(self, tmp_path: Path) -> None:
        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError):
            assembler.assemble_manuscript([], out)

    def test_raises_on_missing_page(self, tmp_path: Path) -> None:
        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError):
            assembler.assemble_manuscript([tmp_path / "nonexistent.png"], out)

    @pytest.mark.parametrize("trim", list(TrimSize))
    def test_trim_size_sets_correct_page_dimensions(
        self, tmp_path: Path, trim: TrimSize
    ) -> None:
        asm = PDFAssembler(trim_size=trim)
        page = _make_white_png(tmp_path, f"page_{trim.value}.png")
        out = tmp_path / f"ms_{trim.value}.pdf"
        result = asm.assemble_manuscript([page], out)
        expected_w = (trim.width_inches + BLEED_IN) * PT_PER_IN
        expected_h = (trim.height_inches + 2 * BLEED_IN) * PT_PER_IN
        assert abs(result.page_width_pts - expected_w) < 1.0
        assert abs(result.page_height_pts - expected_h) < 1.0


class TestDPIValidation:
    """assemble_manuscript must raise PDFAssemblyError for sub-300 DPI images."""

    def test_assemble_raises_on_low_dpi(self, tmp_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("L", (1275, 1650), color=255)
        low_dpi_path = tmp_path / "low_dpi.png"
        img.save(str(low_dpi_path), format="PNG", dpi=(150, 150))

        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError, match="300 DPI"):
            assembler.assemble_manuscript([low_dpi_path], out)


class TestPageBleedAsymmetry:
    """drawImage x-position must reflect left/right page bleed asymmetry."""

    def _run_assemble_with_mock_canvas(
        self, tmp_path: Path, page_count: int
    ) -> list[tuple]:
        pages = [_make_white_png(tmp_path, f"p{i}.png") for i in range(page_count)]
        out = tmp_path / "ms.pdf"

        draw_calls: list[tuple] = []

        mock_canvas_instance = MagicMock()
        mock_canvas_instance.drawImage.side_effect = lambda *a, **kw: draw_calls.append(
            (a, kw)
        )

        mock_canvas_cls = MagicMock(return_value=mock_canvas_instance)

        with (
            patch("reportlab.pdfgen.canvas.Canvas", mock_canvas_cls),
            patch("colorforge_agents.generator.pdf_assembler._validate_image_dpi"),
        ):
            assembler.assemble_manuscript(pages, out)

        return draw_calls

    def test_right_page_has_gutter_on_left(self, tmp_path: Path) -> None:
        draw_calls = self._run_assemble_with_mock_canvas(tmp_path, page_count=2)
        gutter_pt = _compute_gutter_inches(2) * PT_PER_IN
        bleed_pt = BLEED_IN * PT_PER_IN

        _args, kwargs = draw_calls[0]
        x_used = _args[1]
        assert abs(x_used - gutter_pt) < 1e-6, (
            f"Right page (idx=0) expected x={gutter_pt:.2f} (gutter), got {x_used:.2f}"
        )
        assert abs(x_used - bleed_pt) > 1e-6

    def test_left_page_has_bleed_on_left(self, tmp_path: Path) -> None:
        draw_calls = self._run_assemble_with_mock_canvas(tmp_path, page_count=2)
        bleed_pt = BLEED_IN * PT_PER_IN
        gutter_pt = _compute_gutter_inches(2) * PT_PER_IN

        _args, kwargs = draw_calls[1]
        x_used = _args[1]
        assert abs(x_used - bleed_pt) < 1e-6, (
            f"Left page (idx=1) expected x={bleed_pt:.2f} (bleed), got {x_used:.2f}"
        )
        assert abs(x_used - gutter_pt) > 1e-6


class TestCoverDimensions:
    def test_cover_width_formula(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path, "cover.png")
        out = tmp_path / "cover.pdf"
        page_count = 75
        result = assembler.assemble_cover(page, page_count, out)
        spine = assembler.spine_width_inches(page_count)
        expected_w = (2 * TRIM_W_IN + spine + 2 * BLEED_IN) * PT_PER_IN
        expected_h = (TRIM_H_IN + 2 * BLEED_IN) * PT_PER_IN
        assert abs(result.page_width_pts - expected_w) < 1.0
        assert abs(result.page_height_pts - expected_h) < 1.0

    def test_cover_page_count_is_one(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path, "cover.png")
        out = tmp_path / "cover.pdf"
        result = assembler.assemble_cover(page, 75, out)
        assert result.page_count == 1

    def test_cover_wider_for_more_pages(self, tmp_path: Path) -> None:
        cover = _make_white_png(tmp_path, "cover.png")
        r100 = assembler.assemble_cover(cover, 100, tmp_path / "c100.pdf")
        r50 = assembler.assemble_cover(cover, 50, tmp_path / "c50.pdf")
        assert r100.page_width_pts > r50.page_width_pts

    def test_raises_on_missing_cover(self, tmp_path: Path) -> None:
        with pytest.raises(PDFAssemblyError):
            assembler.assemble_cover(tmp_path / "missing.png", 75, tmp_path / "cover.pdf")

    @pytest.mark.parametrize("trim", list(TrimSize))
    def test_cover_height_follows_trim_size(self, tmp_path: Path, trim: TrimSize) -> None:
        asm = PDFAssembler(trim_size=trim)
        cover = _make_white_png(tmp_path, f"cover_{trim.value}.png")
        result = asm.assemble_cover(cover, 75, tmp_path / f"cover_{trim.value}.pdf")
        expected_h = (trim.height_inches + 2 * BLEED_IN) * PT_PER_IN
        assert abs(result.page_height_pts - expected_h) < 1.0


class TestPDFAssemblyResult:
    def test_result_model_valid(self) -> None:
        r = PDFAssemblyResult(
            output_path="/tmp/test.pdf",
            page_width_pts=621.0,
            page_height_pts=810.0,
            page_count=1,
        )
        assert r.page_width_pts == 621.0
