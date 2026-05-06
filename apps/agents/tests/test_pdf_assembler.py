"""Tests for PDFAssembler — KDP dimensions and spine formula."""

from __future__ import annotations

from pathlib import Path

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
)


def _make_white_png(tmp_path: Path, name: str = "page.png") -> Path:
    """Write a minimal white 8.5x11 300-DPI PNG to tmp_path."""
    try:
        from PIL import Image

        img = Image.new("L", (2550, 3300), color=255)
        out = tmp_path / name
        img.save(str(out), format="PNG", dpi=(300, 300))
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


class TestManuscriptDimensions:
    def test_correct_page_size_in_result(self, tmp_path: Path) -> None:
        page = _make_white_png(tmp_path)
        out = tmp_path / "ms.pdf"
        result = assembler.assemble_manuscript([page], out)
        expected_w = round((TRIM_W_IN + 2 * BLEED_IN) * PT_PER_IN, 1)
        expected_h = round((TRIM_H_IN + 2 * BLEED_IN) * PT_PER_IN, 1)
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
        assert abs(w - 630.0) < 2.0
        assert abs(h - 810.0) < 2.0

    def test_raises_on_empty_pages(self, tmp_path: Path) -> None:
        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError):
            assembler.assemble_manuscript([], out)

    def test_raises_on_missing_page(self, tmp_path: Path) -> None:
        out = tmp_path / "ms.pdf"
        with pytest.raises(PDFAssemblyError):
            assembler.assemble_manuscript([tmp_path / "nonexistent.png"], out)


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
            page_width_pts=630.0,
            page_height_pts=819.0,
            page_count=1,
        )
        assert r.page_width_pts == 630.0
