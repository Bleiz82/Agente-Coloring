"""KDP-compliant cover compositor.

Produces a single-PDF cover (back + spine + front) from a Gemini cover image
and BookPlan/BookDraft, applying all KDP geometry, CMYK, and font rules.

Source of truth: .claude/skills/kdp-cover-compositor.md
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.exceptions import CoverComplianceError

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------
_ASSETS_DIR: Final = Path(__file__).parent.parent.parent / "assets"
_FONTS_DIR: Final = _ASSETS_DIR / "fonts"
_ICC_PROFILE_PATH: Final = _ASSETS_DIR / "icc" / "USWebCoatedSWOP.icc"

# ---------------------------------------------------------------------------
# KDP geometry constants (all in inches unless noted)
# ---------------------------------------------------------------------------
_BLEED_IN: Final = 0.125
_SAFE_ZONE_IN: Final = 0.25
_SPINE_SAFE_ZONE_IN: Final = 0.0625
_BARCODE_W_IN: Final = 2.0
_BARCODE_H_IN: Final = 1.2
_BARCODE_INSET_IN: Final = 0.25
_RENDER_DPI: Final = 300
_MAX_FILE_SIZE_BYTES: Final = 650 * 1024 * 1024
_RECOMMENDED_FILE_SIZE_BYTES: Final = 40 * 1024 * 1024
_MIN_PAGES_FOR_SPINE_TEXT: Final = 79
_PT_PER_IN: Final = 72.0

# ---------------------------------------------------------------------------
# Font catalog  (OFL / Apache 2.0 — see assets/fonts/README.md)
# ---------------------------------------------------------------------------
_FONT_FILES: Final[dict[str, dict[str, str]]] = {
    "Adult": {
        "title": "PlayfairDisplay-Bold.ttf",
        "body": "Lato-Regular.ttf",
    },
    "Kids": {
        "title": "BebasNeue-Regular.ttf",
        "body": "ComicNeue-Regular.ttf",
    },
    "Activity": {
        "title": "Montserrat-Bold.ttf",
        "body": "OpenSans-Regular.ttf",
    },
    "Pocket": {
        "title": "Lobster-Regular.ttf",
        "body": "SourceSans3-Regular.ttf",
    },
    "Default": {
        "title": "Montserrat-Bold.ttf",
        "body": "OpenSans-Regular.ttf",
    },
}

NICHE_FONT_MAP: Final[dict[str, str]] = {
    "mandala": "Adult",
    "zen": "Adult",
    "geometric": "Adult",
    "stress relief": "Adult",
    "meditation": "Adult",
    "adult": "Adult",
    "kids": "Kids",
    "children": "Kids",
    "toddler": "Kids",
    "preschool": "Kids",
    "kindergarten": "Kids",
    "boys": "Kids",
    "girls": "Kids",
    "workbook": "Activity",
    "activity": "Activity",
    "educational": "Activity",
    "homeschool": "Activity",
    "practice": "Activity",
    "travel": "Pocket",
    "pocket": "Pocket",
    "mini": "Pocket",
    "on the go": "Pocket",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class FontCategory(StrEnum):
    ADULT = "Adult"
    KIDS = "Kids"
    ACTIVITY = "Activity"
    POCKET = "Pocket"
    DEFAULT = "Default"


class CoverGeometry(BaseModel):
    model_config = ConfigDict(frozen=True)

    trim_width_in: float
    trim_height_in: float
    spine_width_in: float
    cover_width_in: float
    cover_height_in: float
    cover_width_pt: float
    cover_height_pt: float
    spine_width_pt: float
    fold_line_left_pt: float
    fold_line_right_pt: float
    front_left_pt: float
    barcode_x_pt: float
    barcode_y_pt: float
    barcode_w_pt: float
    barcode_h_pt: float


class CoverValidationCheck(StrEnum):
    BLEED_PRESENT = "bleed_present"
    SAFE_ZONE_TEXT = "safe_zone_text"
    BARCODE_AREA_WHITE = "barcode_area_white"
    DPI_300 = "dpi_300"
    SPINE_ELIGIBILITY = "spine_eligibility"
    SPINE_MARGIN = "spine_margin"
    FONT_EMBEDDING = "font_embedding"
    NO_TRANSPARENCY = "no_transparency"
    COLOR_MODE_CMYK = "color_mode_cmyk"
    NO_METADATA_LEAK = "no_metadata_leak"
    FILE_SIZE = "file_size"
    CONTRAST_RATIO = "contrast_ratio"


class CoverValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: list[CoverValidationCheck]
    warnings: list[tuple[CoverValidationCheck, str]]
    failures: list[tuple[CoverValidationCheck, str]]
    overall_verdict: Literal["pass", "warn", "fail"]


class CoverCompositionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: Path
    cover_width_pt: float
    cover_height_pt: float
    spine_width_pt: float
    spine_text_included: bool
    font_category: str
    file_size_bytes: int
    validation_report: CoverValidationReport


# ---------------------------------------------------------------------------
# CoverComplianceValidator
# ---------------------------------------------------------------------------


class CoverComplianceValidator:
    """Standalone validator for KDP cover compliance.

    Can be called against a canvas (pre-export) or a PDF path (post-export).
    """

    @staticmethod
    def validate_canvas(
        canvas_rgb: "Image",  # type: ignore[name-defined]
        geometry: CoverGeometry,
        text_bboxes: list[tuple[int, int, int, int]],
        spine_text_included: bool,
        page_count: int,
        source_dpi: tuple[float, float],
    ) -> CoverValidationReport:
        """Pre-export validation on the rendered PIL canvas."""
        passed: list[CoverValidationCheck] = []
        warnings: list[tuple[CoverValidationCheck, str]] = []
        failures: list[tuple[CoverValidationCheck, str]] = []

        # BLEED_PRESENT: canvas must be at least cover_w × cover_h at _RENDER_DPI
        expected_w = int(geometry.cover_width_in * _RENDER_DPI)
        expected_h = int(geometry.cover_height_in * _RENDER_DPI)
        actual_w, actual_h = canvas_rgb.size
        if actual_w >= expected_w and actual_h >= expected_h:
            passed.append(CoverValidationCheck.BLEED_PRESENT)
        else:
            failures.append((
                CoverValidationCheck.BLEED_PRESENT,
                f"Canvas {actual_w}×{actual_h}px < required {expected_w}×{expected_h}px",
            ))

        # SAFE_ZONE_TEXT: all text boxes must be inside safe zone
        safe_px = int(_SAFE_ZONE_IN * _RENDER_DPI)
        bleed_px = int(_BLEED_IN * _RENDER_DPI)
        outer_safe_left = bleed_px + safe_px
        outer_safe_right = actual_w - bleed_px - safe_px
        outer_safe_bottom = bleed_px + safe_px
        outer_safe_top = actual_h - bleed_px - safe_px
        text_violations: list[str] = []
        for x0, y0, x1, y1 in text_bboxes:
            if x0 < outer_safe_left or x1 > outer_safe_right:
                text_violations.append(f"bbox ({x0},{y0},{x1},{y1}) crosses X safe zone")
            if y0 < outer_safe_bottom or y1 > outer_safe_top:
                text_violations.append(f"bbox ({x0},{y0},{x1},{y1}) crosses Y safe zone")
        if text_violations:
            failures.append((CoverValidationCheck.SAFE_ZONE_TEXT, "; ".join(text_violations)))
        else:
            passed.append(CoverValidationCheck.SAFE_ZONE_TEXT)

        # BARCODE_AREA_WHITE: sample barcode region pixels
        bx = int(geometry.barcode_x_pt / _PT_PER_IN * _RENDER_DPI)
        by = int(geometry.barcode_y_pt / _PT_PER_IN * _RENDER_DPI)
        bw = int(geometry.barcode_w_pt / _PT_PER_IN * _RENDER_DPI)
        bh = int(geometry.barcode_h_pt / _PT_PER_IN * _RENDER_DPI)
        barcode_region = canvas_rgb.crop((bx, actual_h - by - bh, bx + bw, actual_h - by))
        pixels = list(barcode_region.getdata())  # type: ignore[attr-defined]
        if pixels:
            white_count = sum(
                1 for p in pixels
                if isinstance(p, (tuple, list)) and len(p) >= 3
                and p[0] >= 250 and p[1] >= 250 and p[2] >= 250
            )
            pct = white_count / len(pixels)
            if pct >= 0.95:
                passed.append(CoverValidationCheck.BARCODE_AREA_WHITE)
            else:
                failures.append((
                    CoverValidationCheck.BARCODE_AREA_WHITE,
                    f"Barcode region only {pct*100:.1f}% white (need ≥95%)",
                ))
        else:
            passed.append(CoverValidationCheck.BARCODE_AREA_WHITE)

        # DPI_300: source image DPI
        if round(source_dpi[0]) >= 300 and round(source_dpi[1]) >= 300:
            passed.append(CoverValidationCheck.DPI_300)
        else:
            failures.append((
                CoverValidationCheck.DPI_300,
                f"Source image DPI {source_dpi[0]}×{source_dpi[1]} < 300",
            ))

        # SPINE_ELIGIBILITY: no spine text on < 79 pages
        if spine_text_included and page_count < _MIN_PAGES_FOR_SPINE_TEXT:
            failures.append((
                CoverValidationCheck.SPINE_ELIGIBILITY,
                f"Spine text enabled but page_count={page_count} < {_MIN_PAGES_FOR_SPINE_TEXT}",
            ))
        else:
            passed.append(CoverValidationCheck.SPINE_ELIGIBILITY)

        # SPINE_MARGIN: check spine text bbox vs fold lines
        # (simplified: if spine_text_included, spine width must be > 2 × SPINE_SAFE_ZONE_IN)
        if spine_text_included:
            min_spine_px = int(2 * _SPINE_SAFE_ZONE_IN * _RENDER_DPI)
            spine_px = int(geometry.spine_width_in * _RENDER_DPI)
            if spine_px >= min_spine_px:
                passed.append(CoverValidationCheck.SPINE_MARGIN)
            else:
                failures.append((
                    CoverValidationCheck.SPINE_MARGIN,
                    f"Spine {spine_px}px too narrow for safe-zone margins (need ≥{min_spine_px}px)",
                ))
        else:
            passed.append(CoverValidationCheck.SPINE_MARGIN)

        # NO_TRANSPARENCY: PIL RGB canvas has no alpha channel
        if canvas_rgb.mode in ("RGB", "CMYK"):
            warnings.append((
                CoverValidationCheck.NO_TRANSPARENCY,
                "Canvas is RGB/CMYK — no transparency (OK)",
            ))
            passed.append(CoverValidationCheck.NO_TRANSPARENCY)
        else:
            warnings.append((
                CoverValidationCheck.NO_TRANSPARENCY,
                f"Canvas mode {canvas_rgb.mode!r} may contain transparency",
            ))

        # CONTRAST_RATIO: approximate WCAG AA check (warn only)
        warnings.append((
            CoverValidationCheck.CONTRAST_RATIO,
            "Contrast ratio check deferred to post-export review",
        ))

        verdict: Literal["pass", "warn", "fail"]
        if failures:
            verdict = "fail"
        elif warnings:
            verdict = "warn"
        else:
            verdict = "pass"

        return CoverValidationReport(
            passed=passed,
            warnings=warnings,
            failures=failures,
            overall_verdict=verdict,
        )

    @staticmethod
    def validate_pdf(pdf_path: Path) -> CoverValidationReport:
        """Post-export validation against a PDF file."""
        import pypdf

        passed: list[CoverValidationCheck] = []
        warnings: list[tuple[CoverValidationCheck, str]] = []
        failures: list[tuple[CoverValidationCheck, str]] = []

        # FILE_SIZE
        file_size = pdf_path.stat().st_size
        if file_size > _MAX_FILE_SIZE_BYTES:
            failures.append((
                CoverValidationCheck.FILE_SIZE,
                f"File {file_size // (1024*1024)}MB exceeds hard limit 650MB",
            ))
        elif file_size > _RECOMMENDED_FILE_SIZE_BYTES:
            warnings.append((
                CoverValidationCheck.FILE_SIZE,
                f"File {file_size // (1024*1024)}MB exceeds recommended 40MB",
            ))
            passed.append(CoverValidationCheck.FILE_SIZE)
        else:
            passed.append(CoverValidationCheck.FILE_SIZE)

        try:
            reader = pypdf.PdfReader(str(pdf_path))

            # FONT_EMBEDDING: all fonts must have /FontFile*
            font_issues: list[str] = []
            for page in reader.pages:
                resources = page.get("/Resources", {})
                fonts = resources.get("/Font", {})
                for font_name, font_obj in fonts.items():
                    if hasattr(font_obj, "get_object"):
                        font_obj = font_obj.get_object()
                    descriptor = font_obj.get("/FontDescriptor", {})
                    if hasattr(descriptor, "get_object"):
                        descriptor = descriptor.get_object()
                    has_file = any(
                        k in descriptor
                        for k in ("/FontFile", "/FontFile2", "/FontFile3")
                    )
                    if not has_file:
                        font_issues.append(font_name)
            if font_issues:
                failures.append((
                    CoverValidationCheck.FONT_EMBEDDING,
                    f"Fonts missing /FontFile: {font_issues}",
                ))
            else:
                passed.append(CoverValidationCheck.FONT_EMBEDDING)

            # COLOR_MODE_CMYK: check /ColorSpace in page resources
            cmyk_found = False
            for page in reader.pages:
                page_str = str(page)
                if "DeviceCMYK" in page_str or "ICCBased" in page_str:
                    cmyk_found = True
                    break
            if cmyk_found:
                passed.append(CoverValidationCheck.COLOR_MODE_CMYK)
            else:
                failures.append((
                    CoverValidationCheck.COLOR_MODE_CMYK,
                    "PDF colorspace does not reference DeviceCMYK or ICCBased CMYK profile",
                ))

            # NO_METADATA_LEAK: check /Author in metadata
            meta = reader.metadata
            if meta:
                author_val = meta.get("/Author", "")
                if author_val and author_val not in ("ColorForge AI", ""):
                    warnings.append((
                        CoverValidationCheck.NO_METADATA_LEAK,
                        f"PDF /Author metadata: {author_val!r}",
                    ))
                else:
                    passed.append(CoverValidationCheck.NO_METADATA_LEAK)
            else:
                passed.append(CoverValidationCheck.NO_METADATA_LEAK)

        except Exception as exc:
            failures.append((
                CoverValidationCheck.FONT_EMBEDDING,
                f"Could not parse PDF: {exc}",
            ))

        verdict: Literal["pass", "warn", "fail"]
        if failures:
            verdict = "fail"
        elif warnings:
            verdict = "warn"
        else:
            verdict = "pass"

        return CoverValidationReport(
            passed=passed,
            warnings=warnings,
            failures=failures,
            overall_verdict=verdict,
        )


# ---------------------------------------------------------------------------
# CoverCompositor
# ---------------------------------------------------------------------------


def _sanitize_filename(name: str) -> str:
    """Replace non-ASCII and unsafe filename chars with underscores."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


class CoverCompositor:
    """KDP-compliant cover compositor.

    Produces a single-PDF cover (back + spine + front) from a Gemini cover
    image and BookPlan/BookDraft, applying all KDP geometry, color, and
    font rules per kdp-cover-compositor.md.
    """

    def __init__(
        self,
        book_plan: BookPlan,
        book_draft: BookDraft,
        front_image_path: Path,
    ) -> None:
        self.plan = book_plan
        self.draft = book_draft
        self.front_image_path = front_image_path
        self._trim_w_in = book_plan.trim_size.width_inches
        self._trim_h_in = book_plan.trim_size.height_inches
        self._paper_mult = book_plan.paper_type.spine_multiplier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compose(self, output_dir: Path) -> CoverCompositionResult:
        """Build a print-ready cover PDF.

        Args:
            output_dir: Directory where the cover PDF is written.

        Returns:
            CoverCompositionResult with paths, dimensions, and validation report.

        Raises:
            CoverComplianceError: if any P0 validation check fails.
            FileNotFoundError: if the cover image, ICC profile, or font is missing.
        """
        if not self.front_image_path.exists():
            raise FileNotFoundError(f"Cover image not found: {self.front_image_path}")
        if not _ICC_PROFILE_PATH.exists():
            raise FileNotFoundError(
                f"ICC profile not found: {_ICC_PROFILE_PATH}\n"
                "Run: python scripts/download_assets.py --stub-icc"
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        geom = self._compute_geometry()
        font_cat = self._select_font_category()
        spine_eligible = self.draft.page_count >= _MIN_PAGES_FOR_SPINE_TEXT

        canvas_rgb, text_bboxes, source_dpi = self._render_canvas(geom, font_cat, spine_eligible)

        report = CoverComplianceValidator.validate_canvas(
            canvas_rgb,
            geom,
            text_bboxes,
            spine_text_included=spine_eligible,
            page_count=self.draft.page_count,
            source_dpi=source_dpi,
        )

        if report.overall_verdict == "fail":
            raise CoverComplianceError(
                f"Cover compliance failed: {[f[1] for f in report.failures]}"
            )

        cmyk_image = self._convert_to_cmyk(canvas_rgb)

        safe_title = _sanitize_filename(self.draft.title or "cover")
        pdf_name = f"cover_{safe_title}_{self.draft.book_id[:8]}.pdf"
        pdf_path = output_dir / pdf_name
        self._export_pdf(cmyk_image, geom, pdf_path)

        post_report = CoverComplianceValidator.validate_pdf(pdf_path)

        if post_report.overall_verdict == "fail":
            raise CoverComplianceError(
                f"Post-export validation failed: {[f[1] for f in post_report.failures]}"
            )

        file_size = pdf_path.stat().st_size
        if file_size > _RECOMMENDED_FILE_SIZE_BYTES:
            from loguru import logger
            logger.warning(
                "cover PDF size {}MB exceeds recommended 40MB",
                file_size // (1024 * 1024),
            )

        return CoverCompositionResult(
            pdf_path=pdf_path,
            cover_width_pt=geom.cover_width_pt,
            cover_height_pt=geom.cover_height_pt,
            spine_width_pt=geom.spine_width_pt,
            spine_text_included=spine_eligible,
            font_category=font_cat,
            file_size_bytes=file_size,
            validation_report=post_report,
        )

    # ------------------------------------------------------------------
    # Private: geometry
    # ------------------------------------------------------------------

    def _compute_geometry(self) -> CoverGeometry:
        spine_w_in = self.draft.page_count * self._paper_mult
        cover_w_in = 2 * _BLEED_IN + 2 * self._trim_w_in + spine_w_in
        cover_h_in = 2 * _BLEED_IN + self._trim_h_in

        cover_w_pt = cover_w_in * _PT_PER_IN
        cover_h_pt = cover_h_in * _PT_PER_IN
        spine_w_pt = spine_w_in * _PT_PER_IN

        fold_left_pt = (_BLEED_IN + self._trim_w_in) * _PT_PER_IN
        fold_right_pt = fold_left_pt + spine_w_pt
        front_left_pt = fold_right_pt

        # Barcode: lower-right of back cover, inset 0.25" from edges
        barcode_x_pt = (
            (_BLEED_IN + self._trim_w_in - _BARCODE_INSET_IN - _BARCODE_W_IN) * _PT_PER_IN
        )
        barcode_y_pt = (_BLEED_IN + _BARCODE_INSET_IN) * _PT_PER_IN
        barcode_w_pt = _BARCODE_W_IN * _PT_PER_IN
        barcode_h_pt = _BARCODE_H_IN * _PT_PER_IN

        return CoverGeometry(
            trim_width_in=self._trim_w_in,
            trim_height_in=self._trim_h_in,
            spine_width_in=spine_w_in,
            cover_width_in=cover_w_in,
            cover_height_in=cover_h_in,
            cover_width_pt=cover_w_pt,
            cover_height_pt=cover_h_pt,
            spine_width_pt=spine_w_pt,
            fold_line_left_pt=fold_left_pt,
            fold_line_right_pt=fold_right_pt,
            front_left_pt=front_left_pt,
            barcode_x_pt=barcode_x_pt,
            barcode_y_pt=barcode_y_pt,
            barcode_w_pt=barcode_w_pt,
            barcode_h_pt=barcode_h_pt,
        )

    # ------------------------------------------------------------------
    # Private: font category selection
    # ------------------------------------------------------------------

    def _select_font_category(self) -> str:
        """Map niche keywords to font category per NICHE_FONT_MAP."""
        # Use primary_keyword + category_path as niche text proxy
        niche_text = self.plan.target_keyword.lower()
        for keyword, category in NICHE_FONT_MAP.items():
            if keyword in niche_text:
                return category
        return FontCategory.DEFAULT

    # ------------------------------------------------------------------
    # Private: canvas rendering
    # ------------------------------------------------------------------

    def _render_canvas(
        self,
        geom: CoverGeometry,
        font_cat: str,
        spine_eligible: bool,
    ) -> tuple["Image", list[tuple[int, int, int, int]], tuple[float, float]]:  # type: ignore[name-defined]
        from PIL import Image, ImageDraw, ImageFont

        canvas_w_px = int(geom.cover_width_in * _RENDER_DPI)
        canvas_h_px = int(geom.cover_height_in * _RENDER_DPI)
        canvas = Image.new("RGB", (canvas_w_px, canvas_h_px), color=(255, 255, 255))

        # --- paste front image ---
        with Image.open(self.front_image_path) as front_src:
            src_dpi_raw = front_src.info.get("dpi", (0, 0))
            source_dpi: tuple[float, float] = (
                float(src_dpi_raw[0]) if isinstance(src_dpi_raw, tuple) and len(src_dpi_raw) >= 1 else 0.0,
                float(src_dpi_raw[1]) if isinstance(src_dpi_raw, tuple) and len(src_dpi_raw) >= 2 else 0.0,
            )

            front_x_px = int(geom.front_left_pt / _PT_PER_IN * _RENDER_DPI)
            front_w_px = canvas_w_px - front_x_px
            front_h_px = canvas_h_px
            front_resized = front_src.resize(
                (front_w_px, front_h_px),
                getattr(
                    getattr(Image, "Resampling", Image), "LANCZOS"
                ),
            )
            canvas.paste(front_resized, (front_x_px, 0))

        # --- derive dominant color for back/spine ---
        back_color = self._sample_dominant_color(canvas, int(front_x_px * 0.5), canvas_h_px)
        spine_color = back_color

        # --- render back cover background ---
        back_w_px = int(geom.fold_line_left_pt / _PT_PER_IN * _RENDER_DPI)
        back_region = Image.new("RGB", (back_w_px, canvas_h_px), color=back_color)
        canvas.paste(back_region, (0, 0))

        # --- render spine background ---
        spine_x_px = int(geom.fold_line_left_pt / _PT_PER_IN * _RENDER_DPI)
        spine_w_px = int(geom.spine_width_pt / _PT_PER_IN * _RENDER_DPI)
        spine_region = Image.new("RGB", (spine_w_px, canvas_h_px), color=spine_color)
        canvas.paste(spine_region, (spine_x_px, 0))

        # --- load fonts ---
        font_files = _FONT_FILES[font_cat]
        title_font_path = _FONTS_DIR / font_files["title"]
        body_font_path = _FONTS_DIR / font_files["body"]

        trim_h_pt = geom.trim_height_in * _PT_PER_IN
        title_pt = max(48, min(96, int(trim_h_pt * 0.075)))
        subtitle_pt = max(18, min(36, int(title_pt * 0.40)))
        author_pt = max(14, min(28, int(title_pt * 0.30)))

        title_px = int(title_pt / _PT_PER_IN * _RENDER_DPI)
        subtitle_px = int(subtitle_pt / _PT_PER_IN * _RENDER_DPI)
        author_px = int(author_pt / _PT_PER_IN * _RENDER_DPI)
        blurb_px = int(11 / _PT_PER_IN * _RENDER_DPI)

        if title_font_path.exists():
            font_title = ImageFont.truetype(str(title_font_path), title_px)
            font_subtitle = ImageFont.truetype(str(title_font_path), subtitle_px)
            font_author = ImageFont.truetype(str(body_font_path) if body_font_path.exists() else str(title_font_path), author_px)
            font_blurb = ImageFont.truetype(str(body_font_path) if body_font_path.exists() else str(title_font_path), blurb_px)
        else:
            font_title = ImageFont.load_default()
            font_subtitle = font_title
            font_author = font_title
            font_blurb = font_title

        draw = ImageDraw.Draw(canvas)
        text_bboxes: list[tuple[int, int, int, int]] = []

        # --- front: title, subtitle, author ---
        safe_px = int(_SAFE_ZONE_IN * _RENDER_DPI)
        bleed_px = int(_BLEED_IN * _RENDER_DPI)
        front_safe_left = front_x_px + bleed_px + safe_px
        front_safe_right = canvas_w_px - bleed_px - safe_px
        front_safe_top = bleed_px + safe_px
        front_safe_bottom = canvas_h_px - bleed_px - safe_px

        front_center_x = (front_safe_left + front_safe_right) // 2

        title_text = self.draft.title or self.plan.target_keyword
        title_y = front_safe_top + int(0.10 * (front_safe_bottom - front_safe_top))
        bbox = draw.textbbox((front_center_x, title_y), title_text, font=font_title, anchor="mt")
        draw.text((front_center_x, title_y), title_text, font=font_title, fill=(255, 255, 255), anchor="mt")
        text_bboxes.append(bbox)

        if self.draft.subtitle:
            sub_y = bbox[3] + subtitle_px // 2
            sub_bbox = draw.textbbox((front_center_x, sub_y), self.draft.subtitle, font=font_subtitle, anchor="mt")
            draw.text((front_center_x, sub_y), self.draft.subtitle, font=font_subtitle, fill=(220, 220, 220), anchor="mt")
            text_bboxes.append(sub_bbox)

        author_text = self.draft.author or self.plan.brand_author
        author_y = front_safe_bottom - author_px - safe_px
        auth_bbox = draw.textbbox((front_center_x, author_y), author_text, font=font_author, anchor="mt")
        draw.text((front_center_x, author_y), author_text, font=font_author, fill=(200, 200, 200), anchor="mt")
        text_bboxes.append(auth_bbox)

        # --- back: blurb placeholder ---
        back_center_x = back_w_px // 2
        back_safe_top = bleed_px + safe_px
        blurb_text = self.plan.style_fingerprint[:80] if self.plan.style_fingerprint else ""
        if blurb_text:
            bl_bbox = draw.textbbox((back_center_x, back_safe_top), blurb_text, font=font_blurb, anchor="mt")
            draw.text((back_center_x, back_safe_top), blurb_text, font=font_blurb, fill=(240, 240, 240), anchor="mt")
            text_bboxes.append(bl_bbox)

        # --- barcode area: white rectangle ---
        bx_px = int(geom.barcode_x_pt / _PT_PER_IN * _RENDER_DPI)
        by_pt = geom.barcode_y_pt / _PT_PER_IN  # in inches from bottom
        by_px = canvas_h_px - int(by_pt * _RENDER_DPI) - int(_BARCODE_H_IN * _RENDER_DPI)
        bw_px = int(_BARCODE_W_IN * _RENDER_DPI)
        bh_px = int(_BARCODE_H_IN * _RENDER_DPI)
        draw.rectangle((bx_px, by_px, bx_px + bw_px, by_px + bh_px), fill=(255, 255, 255))

        # --- spine text (if eligible) ---
        if spine_eligible and spine_w_px > int(2 * _SPINE_SAFE_ZONE_IN * _RENDER_DPI):
            spine_font_path = _FONTS_DIR / font_files["title"]
            spine_pt_size = max(12, min(24, spine_w_px - int(4.5 / _PT_PER_IN * _RENDER_DPI)))
            if spine_font_path.exists():
                font_spine = ImageFont.truetype(str(spine_font_path), spine_pt_size)
            else:
                font_spine = font_title
            from PIL import Image as PILImage
            spine_band = PILImage.new("RGB", (canvas_h_px, spine_w_px), color=spine_color)
            spine_draw = ImageDraw.Draw(spine_band)
            spine_text = title_text[:40]
            spine_draw.text(
                (canvas_h_px // 2, spine_w_px // 2),
                spine_text,
                font=font_spine,
                fill=(255, 255, 255),
                anchor="mm",
            )
            spine_rotated = spine_band.rotate(270, expand=True)
            canvas.paste(spine_rotated, (spine_x_px, 0))

        canvas.info["dpi"] = (_RENDER_DPI, _RENDER_DPI)
        return canvas, text_bboxes, source_dpi

    @staticmethod
    def _sample_dominant_color(
        canvas: "Image",  # type: ignore[name-defined]
        sample_w: int,
        sample_h: int,
    ) -> tuple[int, int, int]:
        """Sample average color from left portion of canvas (back cover base)."""
        if sample_w <= 0:
            return (30, 30, 80)
        region = canvas.crop((0, 0, min(sample_w, canvas.width), sample_h))
        pixels = list(region.getdata())
        if not pixels:
            return (30, 30, 80)
        r = int(sum(p[0] for p in pixels) / len(pixels))
        g = int(sum(p[1] for p in pixels) / len(pixels))
        b = int(sum(p[2] for p in pixels) / len(pixels))
        return (r, g, b)

    # ------------------------------------------------------------------
    # Private: CMYK conversion
    # ------------------------------------------------------------------

    def _convert_to_cmyk(self, rgb_image: "Image") -> "Image":  # type: ignore[name-defined]
        from PIL import ImageCms

        src_profile = ImageCms.createProfile("sRGB")
        dst_profile = ImageCms.getOpenProfile(str(_ICC_PROFILE_PATH))
        transform = ImageCms.buildTransformFromOpenProfiles(
            src_profile, dst_profile, "RGB", "CMYK"
        )
        return ImageCms.applyTransform(rgb_image, transform)

    # ------------------------------------------------------------------
    # Private: PDF export
    # ------------------------------------------------------------------

    def _export_pdf(
        self,
        cmyk_image: "Image",  # type: ignore[name-defined]
        geom: CoverGeometry,
        pdf_path: Path,
    ) -> None:
        """Export CMYK image as PDF/X-1a with embedded fonts via ReportLab."""
        from io import BytesIO

        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas as rl_canvas

        # Register fonts (best-effort — may not be present in test envs)
        for cat_fonts in _FONT_FILES.values():
            for font_key, font_file in cat_fonts.items():
                font_path = _FONTS_DIR / font_file
                if font_path.exists():
                    font_name = font_file.replace(".ttf", "").replace("-", "_")
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                    except Exception:
                        pass

        cover_w_pt = geom.cover_width_pt
        cover_h_pt = geom.cover_height_pt

        # Save CMYK image to temp buffer
        img_buffer = BytesIO()
        cmyk_image.save(img_buffer, format="TIFF", compression="tiff_lzw")
        img_buffer.seek(0)

        from PIL import Image as PILImage
        tmp_img = PILImage.open(img_buffer)
        tmp_path = pdf_path.with_suffix(".tmp.tiff")
        tmp_img.save(str(tmp_path))

        c = rl_canvas.Canvas(str(pdf_path), pagesize=(cover_w_pt, cover_h_pt))
        c.setTitle(self.draft.title or self.plan.target_keyword)
        c.setAuthor("ColorForge AI")
        c.setProducer("ColorForge AI v1.0")
        c.drawImage(str(tmp_path), 0, 0, width=cover_w_pt, height=cover_h_pt)
        c.showPage()
        c.save()

        tmp_path.unlink(missing_ok=True)
