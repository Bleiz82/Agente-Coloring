"""Tests for PDFAssembler — KDP dimensions and spine formula."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from colorforge_agents.exceptions import PDFAssemblyError
from colorforge_agents.generator.pdf_assembler import (
    BLEED_IN,
    PT_PER_IN,
    SPINE_PER_PAGE,
    TRIM_H_IN,
    TRIM_W_IN,
    PDFAssembler,
    PDFAssemblyResult,
    _compute_gutter_inches,
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


class TestGutterScaling:
    """FIX 2 — _compute_gutter_inches returns correct value per page-count range."""

    def test_gutter_scaling_by_page_count(self) -> None:
        # ≤100 pages → 0.5"
        assert _compute_gutter_inches(1) == 0.5
        assert _compute_gutter_inches(100) == 0.5
        # 101–150 → 0.625"
        assert _compute_gutter_inches(101) == 0.625
        assert _compute_gutter_inches(150) == 0.625
        # 151–300 → 0.75"
        assert _compute_gutter_inches(151) == 0.75
        assert _compute_gutter_inches(300) == 0.75
        # >300 → 0.875"
        assert _compute_gutter_inches(301) == 0.875
        assert _compute_gutter_inches(500) == 0.875


class TestManuscriptDimensions:
    def test_correct_page_size_in_result(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path)
        out = tmp_path / "ms.pdf"
        result = assembler.assemble_manuscript([page], out)
        # FIX 1: bleed only on outside edge → 8.625" wide, not 8.75"
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
        # FIX 1: page width is now 621.0 pt (8.625" × 72), not 630.0
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


class TestDPIValidation:
    """FIX 4 — assemble_manuscript must raise PDFAssemblyError for sub-300 DPI images."""

    def test_assemble_raises_on_low_dpi(self, tmp_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        # Create a 150-DPI image
        img = Image.new("L", (1275, 1650), color=255)
        low_dpi_path = tmp_path / "low_dpi.png"
        img.save(str(low_dpi_path), format="PNG", dpi=(150, 150))

        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError, match="300 DPI"):
            assembler.assemble_manuscript([low_dpi_path], out)


class TestPageBleedAsymmetry:
    """FIX 3 — drawImage x-position must reflect left/right page bleed asymmetry."""

    def _run_assemble_with_mock_canvas(
        self, tmp_path: Path, page_count: int
    ) -> list[tuple]:
        """Run assemble_manuscript with a mocked canvas and return drawImage call args."""
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
        """Page idx=0 (right/recto): x must equal gutter_pt, not bleed_pt."""
        draw_calls = self._run_assemble_with_mock_canvas(tmp_path, page_count=2)
        gutter_pt = _compute_gutter_inches(2) * PT_PER_IN
        bleed_pt = BLEED_IN * PT_PER_IN

        # First call → page 0 → right page
        _args, kwargs = draw_calls[0]
        x_used = _args[1]  # positional: (str(img_path), x, y, ...)
        assert abs(x_used - gutter_pt) < 1e-6, (
            f"Right page (idx=0) expected x={gutter_pt:.2f} (gutter), got {x_used:.2f}"
        )
        assert abs(x_used - bleed_pt) > 1e-6, (
            "Right page must NOT start at bleed_pt"
        )

    def test_left_page_has_bleed_on_left(self, tmp_path: Path) -> None:
        """Page idx=1 (left/verso): x must equal bleed_pt, not gutter_pt."""
        draw_calls = self._run_assemble_with_mock_canvas(tmp_path, page_count=2)
        bleed_pt = BLEED_IN * PT_PER_IN
        gutter_pt = _compute_gutter_inches(2) * PT_PER_IN

        # Second call → page 1 → left page
        _args, kwargs = draw_calls[1]
        x_used = _args[1]
        assert abs(x_used - bleed_pt) < 1e-6, (
            f"Left page (idx=1) expected x={bleed_pt:.2f} (bleed), got {x_used:.2f}"
        )
        assert abs(x_used - gutter_pt) > 1e-6, (
            "Left page must NOT start at gutter_pt"
        )


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


class TestPDFAssemblyResult:
    def test_result_model_valid(self) -> None:
        r = PDFAssemblyResult(
            output_path="/tmp/test.pdf",
            page_width_pts=621.0,   # FIX 1: updated from 630.0 → 621.0
            page_height_pts=810.0,
            page_count=1,
        )
        assert r.page_width_pts == 621.0
