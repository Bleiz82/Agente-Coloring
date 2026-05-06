"""ReportLab PDF assembler — KDP-compliant manuscript and cover PDFs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from colorforge_agents.exceptions import PDFAssemblyError

# KDP dimensions (all in inches)
TRIM_W_IN = 8.5
TRIM_H_IN = 11.0
BLEED_IN = 0.125
GUTTER_IN = 0.375
PT_PER_IN = 72.0
SPINE_PER_PAGE = 0.002252  # KDP white-paper formula

# Full page including bleed (points)
_PAGE_W_PT = (TRIM_W_IN + 2 * BLEED_IN) * PT_PER_IN   # 630.0 pt
_PAGE_H_PT = (TRIM_H_IN + 2 * BLEED_IN) * PT_PER_IN   # 810.0 pt

# Image draw area: trim size (no bleed), shifted right by gutter on left-hand pages
_IMG_W_PT = TRIM_W_IN * PT_PER_IN                      # 612.0 pt
_IMG_H_PT = TRIM_H_IN * PT_PER_IN                      # 792.0 pt
_IMG_X_PT = BLEED_IN * PT_PER_IN                       # 9.0 pt  (left-side bleed offset)
_IMG_Y_PT = BLEED_IN * PT_PER_IN                       # 9.0 pt  (bottom bleed offset)


class PDFAssemblyResult(BaseModel):
    """Result of PDF assembly."""

    output_path: str
    page_width_pts: float = Field(gt=0)
    page_height_pts: float = Field(gt=0)
    page_count: int = Field(gt=0)


class PDFAssembler:
    """Assembles KDP-compliant manuscript and cover PDFs from PNG images."""

    def spine_width_inches(self, page_count: int) -> float:
        """Return spine width in inches using KDP white-paper formula."""
        return SPINE_PER_PAGE * page_count

    def assemble_manuscript(
        self, page_images: list[Path], output_path: Path
    ) -> PDFAssemblyResult:
        """Assemble interior pages into a single PDF with bleed marks.

        Each page is 8.75" × 11.25" (trim + 0.125" bleed on all sides).
        The raster image is drawn inside the trim area.
        """
        try:
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise PDFAssemblyError("reportlab not installed") from exc

        if not page_images:
            raise PDFAssemblyError("No page images provided")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(output_path), pagesize=(_PAGE_W_PT, _PAGE_H_PT))

            for img_path in page_images:
                if not img_path.exists():
                    raise PDFAssemblyError(f"Page image not found: {img_path}")
                c.drawImage(
                    str(img_path),
                    _IMG_X_PT,
                    _IMG_Y_PT,
                    width=_IMG_W_PT,
                    height=_IMG_H_PT,
                    preserveAspectRatio=False,
                )
                c.showPage()

            c.save()
        except PDFAssemblyError:
            raise
        except Exception as exc:
            raise PDFAssemblyError(f"Manuscript assembly failed: {exc}") from exc

        return PDFAssemblyResult(
            output_path=str(output_path),
            page_width_pts=_PAGE_W_PT,
            page_height_pts=_PAGE_H_PT,
            page_count=len(page_images),
        )

    def assemble_cover(
        self, cover_image: Path, page_count: int, output_path: Path
    ) -> PDFAssemblyResult:
        """Assemble the full wrap cover PDF.

        Cover width = 2 * trim_w + spine + 2 * bleed
        Cover height = trim_h + 2 * bleed
        """
        try:
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise PDFAssemblyError("reportlab not installed") from exc

        if not cover_image.exists():
            raise PDFAssemblyError(f"Cover image not found: {cover_image}")

        spine_in = self.spine_width_inches(page_count)
        cover_w_in = 2 * TRIM_W_IN + spine_in + 2 * BLEED_IN
        cover_h_in = TRIM_H_IN + 2 * BLEED_IN

        cover_w_pt = cover_w_in * PT_PER_IN
        cover_h_pt = cover_h_in * PT_PER_IN

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(output_path), pagesize=(cover_w_pt, cover_h_pt))
            c.drawImage(
                str(cover_image),
                0,
                0,
                width=cover_w_pt,
                height=cover_h_pt,
                preserveAspectRatio=False,
            )
            c.showPage()
            c.save()
        except PDFAssemblyError:
            raise
        except Exception as exc:
            raise PDFAssemblyError(f"Cover assembly failed: {exc}") from exc

        return PDFAssemblyResult(
            output_path=str(output_path),
            page_width_pts=cover_w_pt,
            page_height_pts=cover_h_pt,
            page_count=1,
        )
