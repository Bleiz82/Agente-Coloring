"""ReportLab PDF assembler — KDP-compliant manuscript and cover PDFs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from colorforge_agents.contracts.book_plan import PaperType, TrimSize
from colorforge_agents.exceptions import PDFAssemblyError

# Module-level constants (LETTER defaults — kept for backward compatibility)
TRIM_W_IN = 8.5
TRIM_H_IN = 11.0
BLEED_IN = 0.125
PT_PER_IN = 72.0
SPINE_PER_PAGE = 0.002252  # white paper formula — use PaperType.spine_multiplier for others

# Outside margin minimums per KDP_OFFICIAL_SPECS.md §4
_OUTSIDE_MARGIN_MIN_BLEED_IN: float = 0.375
_OUTSIDE_MARGIN_MIN_NO_BLEED_IN: float = 0.25


def _compute_gutter_inches(page_count: int) -> float:
    """Return KDP minimum inside (gutter) margin in inches for the given page count.

    Source: KDP_OFFICIAL_SPECS.md §4 (official table).

    Raises:
        Nothing — all positive page counts are handled.
    """
    if page_count <= 150:
        return 0.375
    if page_count <= 300:
        return 0.500
    if page_count <= 500:
        return 0.625
    if page_count <= 700:
        return 0.750
    return 0.875  # 701–828


def _validate_outside_margin(
    image_w_in: float,
    image_h_in: float,
    trim_w_in: float,
    trim_h_in: float,
    gutter_in: float,
    has_bleed: bool = True,
    page_index: int = 0,
) -> None:
    """Validate that image placement leaves the required outside margin.

    The outside margin is trim_w_in − gutter_in − image_w_in.

    Args:
        image_w_in: Width of the image in inches.
        image_h_in: Height of the image in inches (reserved for future checks).
        trim_w_in: Trim width in inches.
        trim_h_in: Trim height in inches (reserved for future checks).
        gutter_in: Inside (gutter) margin in inches.
        has_bleed: True if the file uses bleed (stricter margin applies).
        page_index: Zero-based page index, included in the error message.

    Raises:
        PDFAssemblyError: If outside margin < required minimum.
    """
    min_margin = _OUTSIDE_MARGIN_MIN_BLEED_IN if has_bleed else _OUTSIDE_MARGIN_MIN_NO_BLEED_IN
    outside_margin = trim_w_in - gutter_in - image_w_in
    if outside_margin < min_margin - 1e-9:
        raise PDFAssemblyError(
            f"Page {page_index}: outside margin {outside_margin:.4f}\" < required"
            f" {min_margin}\" (trim={trim_w_in}\", gutter={gutter_in}\","
            f" image_w={image_w_in}\")"
        )


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

    def __init__(
        self,
        trim_size: TrimSize = TrimSize.LETTER,
        paper_type: PaperType = PaperType.WHITE,
    ) -> None:
        """Initialise the assembler with KDP trim and paper settings.

        Args:
            trim_size: KDP trim size (default: LETTER = 8.5×11").
            paper_type: Paper stock that controls spine width multiplier.
        """
        self.trim_size = trim_size
        self.paper_type = paper_type
        self.trim_w_in: float = trim_size.width_inches
        self.trim_h_in: float = trim_size.height_inches

    def spine_width_inches(self, page_count: int) -> float:
        """Return spine width in inches using the KDP formula for this paper type.

        Args:
            page_count: Number of interior pages.

        Returns:
            Spine width in inches.
        """
        return self.paper_type.spine_multiplier * page_count

    def assemble_manuscript(
        self, page_images: list[Path], output_path: Path
    ) -> PDFAssemblyResult:
        """Assemble interior pages into a single PDF with bleed marks.

        Page size = trim + bleed on 3 sides (outside, top, bottom).
        Gutter scales with page count per KDP spec. Outside margin is
        validated to be ≥ 0.375" per KDP_OFFICIAL_SPECS.md §4.

        Args:
            page_images: Ordered list of 300 DPI PNG paths.
            output_path: Destination PDF path.

        Returns:
            PDFAssemblyResult with page dimensions and count.

        Raises:
            PDFAssemblyError: If images are missing, DPI < 300, or margins violated.
        """
        try:
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise PDFAssemblyError("reportlab not installed") from exc

        if not page_images:
            raise PDFAssemblyError("No page images provided")

        page_w_pt = (self.trim_w_in + BLEED_IN) * PT_PER_IN
        page_h_pt = (self.trim_h_in + 2 * BLEED_IN) * PT_PER_IN

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(output_path), pagesize=(page_w_pt, page_h_pt))

            gutter_in = _compute_gutter_inches(len(page_images))
            gutter_pt = gutter_in * PT_PER_IN

            # Image width respects outside margin ≥ 0.375"
            img_w_in = self.trim_w_in - gutter_in - _OUTSIDE_MARGIN_MIN_BLEED_IN
            img_h_in = self.trim_h_in
            img_w = img_w_in * PT_PER_IN
            img_h = img_h_in * PT_PER_IN

            # Validate once — geometry is constant for all pages in this book
            _validate_outside_margin(
                img_w_in, img_h_in,
                self.trim_w_in, self.trim_h_in,
                gutter_in, has_bleed=True, page_index=0,
            )

            for page_idx, img_path in enumerate(page_images):
                if not img_path.exists():
                    raise PDFAssemblyError(f"Page image not found: {img_path}")

                _validate_image_dpi(img_path)

                # Right page (recto, even idx): gutter on left; bleed on right
                # Left page (verso, odd idx): bleed on left; gutter on right
                is_right_page = page_idx % 2 == 0
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
            page_width_pts=page_w_pt,
            page_height_pts=page_h_pt,
            page_count=len(page_images),
        )

    def assemble_cover(
        self, cover_image: Path, page_count: int, output_path: Path
    ) -> PDFAssemblyResult:
        """Assemble the full wrap cover PDF.

        Cover width = 2 × trim_w + spine + 2 × bleed
        Cover height = trim_h + 2 × bleed

        Args:
            cover_image: Path to the full-wrap cover PNG.
            page_count: Number of interior pages (determines spine width).
            output_path: Destination PDF path.

        Returns:
            PDFAssemblyResult with cover dimensions.

        Raises:
            PDFAssemblyError: If cover image is missing or assembly fails.
        """
        try:
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise PDFAssemblyError("reportlab not installed") from exc

        if not cover_image.exists():
            raise PDFAssemblyError(f"Cover image not found: {cover_image}")

        spine_in = self.spine_width_inches(page_count)
        cover_w_in = 2 * self.trim_w_in + spine_in + 2 * BLEED_IN
        cover_h_in = self.trim_h_in + 2 * BLEED_IN

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
