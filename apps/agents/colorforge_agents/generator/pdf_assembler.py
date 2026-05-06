"""ReportLab PDF assembler — KDP-compliant manuscript and cover PDFs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from colorforge_agents.exceptions import PDFAssemblyError

# KDP dimensions (all in inches)
TRIM_W_IN = 8.5
TRIM_H_IN = 11.0
BLEED_IN = 0.125
PT_PER_IN = 72.0
SPINE_PER_PAGE = 0.002252  # KDP white-paper formula

# Full page including bleed (points)
# FIX 1: bleed only on outside edge (right) for width → 8.625" × 11.25"
_PAGE_W_PT = (TRIM_W_IN + BLEED_IN) * PT_PER_IN   # 621.0 pt  (bleed solo outside edge)
_PAGE_H_PT = (TRIM_H_IN + 2 * BLEED_IN) * PT_PER_IN  # 810.0 pt  (bleed top + bottom)


def _compute_gutter_inches(page_count: int) -> float:
    """KDP gutter requirements scaled to page count.

    SPEC.md sezione 5.
    """
    if page_count <= 100:
        return 0.5
    if page_count <= 150:
        return 0.625
    if page_count <= 300:
        return 0.75
    return 0.875  # >300 pages


def _validate_image_dpi(img_path: Path, min_dpi: int = 300) -> None:
    """Raise PDFAssemblyError if image is not at least 300 DPI on both axes."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise PDFAssemblyError("Pillow not installed") from exc

    with Image.open(img_path) as img:
        dpi = img.info.get("dpi", (0, 0))

    if not isinstance(dpi, tuple) or len(dpi) < 2:
        raise PDFAssemblyError(f"Image {img_path} has no DPI metadata")

    if round(dpi[0]) < min_dpi or round(dpi[1]) < min_dpi:
        raise PDFAssemblyError(
            f"Image {img_path} not 300 DPI: got {dpi[0]}×{dpi[1]}"
        )


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

        Each page is 8.625" × 11.25" (trim + bleed on 3 sides: outside, top, bottom).
        Gutter is applied on the inside edge and scales with page count per KDP spec.
        Right pages (recto, even index): gutter on left, bleed on right.
        Left pages (verso, odd index): bleed on left, gutter on right.
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

            for page_idx, img_path in enumerate(page_images):
                if not img_path.exists():
                    raise PDFAssemblyError(f"Page image not found: {img_path}")

                # FIX 3a: validate DPI before drawing
                _validate_image_dpi(img_path)

                # FIX 3b: gutter scaling + left/right page bleed asymmetry
                is_right_page = page_idx % 2 == 0  # page 0 = right (recto), page 1 = left (verso)
                gutter_pt = _compute_gutter_inches(len(page_images)) * PT_PER_IN

                # Drawable area inside trim, accounting for gutter on inside edge
                img_w = (TRIM_W_IN * PT_PER_IN) - gutter_pt
                img_h = TRIM_H_IN * PT_PER_IN

                # Right page: gutter on left; left page: bleed on left
                img_x = gutter_pt if is_right_page else BLEED_IN * PT_PER_IN

                img_y = BLEED_IN * PT_PER_IN

                c.drawImage(
                    str(img_path),
                    img_x,
                    img_y,
                    width=img_w,
                    height=img_h,
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
