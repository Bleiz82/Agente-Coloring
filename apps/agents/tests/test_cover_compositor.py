"""Tests for CoverCompositor and CoverComplianceValidator.

Tests cover:
- Geometry computation for all 5 trim sizes
- Spine eligibility boundary (78, 79, 80 pages)
- Font category mapping
- Barcode area whiteness
- DPI validation
- Full compose pipeline (mocked fonts + ICC)
- CoverComplianceValidator PDF checks
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.book_plan import (
    BookPlan,
    BookFormat,
    CoverBrief,
    CoverFinish,
    PagePrompt,
    PaperType,
    TrimSize,
)
from colorforge_agents.generator.cover_compositor import (
    _BLEED_IN,
    _MIN_PAGES_FOR_SPINE_TEXT,
    NICHE_FONT_MAP,
    CoverComplianceValidator,
    CoverCompositor,
    CoverValidationCheck,
    CoverValidationReport,
    _sanitize_filename,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(
    trim_size: TrimSize = TrimSize.LETTER,
    paper_type: PaperType = PaperType.WHITE,
    keyword: str = "mandala coloring book",
) -> BookPlan:
    return BookPlan(
        niche_brief_id="test-niche-001",
        account_id="test-account-001",
        style_fingerprint="test-fp",
        page_count=75,
        page_prompts=[PagePrompt(index=0, prompt="test", complexity_tier="medium", theme="test")],
        cover_brief=CoverBrief(
            subject="Test",
            style_fingerprint="test-fp",
            palette_hint="#000",
            background_hint="white",
        ),
        target_keyword=keyword,
        target_price=7.99,
        brand_author="Test Author",
        trim_size=trim_size,
        paper_type=paper_type,
        cover_finish=CoverFinish.MATTE,
        book_format=BookFormat.PAPERBACK,
    )


def _make_draft(page_count: int = 75, title: str = "Test Book") -> BookDraft:
    return BookDraft(
        book_id="draft-001",
        manuscript_pdf_path="/tmp/ms.pdf",
        cover_pdf_path="/tmp/cover.pdf",
        pages=[
            DraftPage(index=0, image_path="/tmp/p0.png", prompt_used="test", validation_status="pass")
        ],
        spine_width_inches=0.169,
        total_pages=page_count,
        title=title,
        author="Test Author",
        generation_metadata=GenerationMetadata(
            generator_model_version="test",
            total_generation_time_ms=1000,
            total_cost_usd=0.5,
            pages_generated=page_count,
            pages_regenerated=0,
        ),
    )


def _make_cover_png(path: Path, width: int, height: int, dpi: int = 300) -> None:
    """Create a minimal PNG test fixture at given path."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    img.save(str(path), format="PNG", dpi=(dpi, dpi))


def _make_stub_icc(path: Path) -> None:
    """Create a minimal stub ICC profile for testing."""
    profile_size = 128
    header = bytearray(profile_size)
    struct.pack_into(">I", header, 0, profile_size)
    header[4:8] = b"lcms"
    header[8:12] = b"\x02\x10\x00\x00"
    header[12:16] = b"prtr"
    header[16:20] = b"CMYK"
    header[20:24] = b"Lab "
    header[36:40] = b"acsp"
    path.write_bytes(bytes(header))


# ---------------------------------------------------------------------------
# Tests: geometry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "trim_size,expected_cover_w,expected_cover_h",
    [
        # 75 pages white paper, multiplier=0.002252
        # spine = 75 * 0.002252 = 0.1689
        # cover_w = 0.125 + 8.5 + 0.1689 + 8.5 + 0.125 = 17.4189
        # cover_h = 0.125 + 11 + 0.125 = 11.25
        (TrimSize.LETTER, 17.419, 11.25),
        # spine = 0.1689, cover_w = 0.125+8.5+0.1689+8.5+0.125 = 17.419, h=8.75
        (TrimSize.SQUARE_LARGE, 17.419, 8.75),
        # cover_w = 0.125+8+0.1689+8+0.125 = 16.419, h=10.25
        (TrimSize.KIDS, 16.419, 10.25),
        # cover_w = 0.125+7+0.1689+7+0.125 = 14.419, h=10.25
        (TrimSize.INTERMEDIATE, 14.419, 10.25),
        # cover_w = 0.125+6+0.1689+6+0.125 = 12.419, h=9.25
        (TrimSize.POCKET, 12.419, 9.25),
    ],
)
def test_geometry_all_5_trim_sizes(
    trim_size: TrimSize,
    expected_cover_w: float,
    expected_cover_h: float,
) -> None:
    plan = _make_plan(trim_size=trim_size)
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    assert abs(geom.cover_width_in - expected_cover_w) < 0.01, (
        f"{trim_size}: cover_width {geom.cover_width_in:.4f} != {expected_cover_w}"
    )
    assert abs(geom.cover_height_in - expected_cover_h) < 0.01, (
        f"{trim_size}: cover_height {geom.cover_height_in:.4f} != {expected_cover_h}"
    )


def test_geometry_letter_75_pages_spine() -> None:
    plan = _make_plan(TrimSize.LETTER, PaperType.WHITE)
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    expected_spine = 75 * 0.002252  # = 0.1689"
    assert abs(geom.spine_width_in - expected_spine) < 0.001


def test_geometry_cream_paper_spine_calculation() -> None:
    plan = _make_plan(paper_type=PaperType.CREAM)
    draft = _make_draft(page_count=100)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    expected_spine = 100 * 0.0025  # = 0.25"
    assert abs(geom.spine_width_in - expected_spine) < 0.001


def test_geometry_fold_lines_consistent() -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    expected_fold_left = (_BLEED_IN + plan.trim_size.width_inches) * 72
    expected_fold_right = expected_fold_left + geom.spine_width_pt
    assert abs(geom.fold_line_left_pt - expected_fold_left) < 0.1
    assert abs(geom.fold_line_right_pt - expected_fold_right) < 0.1
    assert abs(geom.front_left_pt - geom.fold_line_right_pt) < 0.1


def test_geometry_barcode_position_inset() -> None:
    plan = _make_plan()
    draft = _make_draft()
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    # Barcode right edge must be ≥ 0.25" from back cover right edge (fold line)
    barcode_right_in = (geom.barcode_x_pt + geom.barcode_w_pt) / 72
    back_right_in = geom.fold_line_left_pt / 72
    assert back_right_in - barcode_right_in >= 0.24  # 0.25" inset


# ---------------------------------------------------------------------------
# Tests: spine eligibility
# ---------------------------------------------------------------------------


def test_spine_text_disabled_at_78_pages() -> None:
    assert _MIN_PAGES_FOR_SPINE_TEXT == 79
    draft = _make_draft(page_count=78)
    assert draft.page_count < _MIN_PAGES_FOR_SPINE_TEXT


def test_spine_text_enabled_at_79_pages() -> None:
    draft = _make_draft(page_count=79)
    assert draft.page_count >= _MIN_PAGES_FOR_SPINE_TEXT


def test_spine_text_enabled_at_80_pages() -> None:
    draft = _make_draft(page_count=80)
    assert draft.page_count >= _MIN_PAGES_FOR_SPINE_TEXT


def test_spine_eligibility_validator_check() -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=50)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    canvas = Image.new("RGB", (100, 100), color=(255, 255, 255))
    canvas.info["dpi"] = (300, 300)

    report = CoverComplianceValidator.validate_canvas(
        canvas_rgb=canvas,
        geometry=geom,
        text_bboxes=[],
        spine_text_included=True,  # invalid: 50 pages < 79
        page_count=50,
        source_dpi=(300.0, 300.0),
    )
    failed_checks = [f[0] for f in report.failures]
    assert CoverValidationCheck.SPINE_ELIGIBILITY in failed_checks


# ---------------------------------------------------------------------------
# Tests: font category mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keyword,expected_category",
    [
        ("ocean mandala coloring book", "Adult"),
        ("zen garden coloring", "Adult"),
        ("geometric patterns adult", "Adult"),
        ("kids dinosaurs coloring", "Kids"),
        ("children garden coloring", "Kids"),
        ("activity workbook for teens", "Activity"),
        ("educational homeschool coloring", "Activity"),
        ("travel pocket coloring book", "Pocket"),
        ("mini coloring on the go", "Pocket"),
        ("abstract shapes coloring book", "Default"),
    ],
)
def test_font_category_mapping(keyword: str, expected_category: str) -> None:
    plan = _make_plan(keyword=keyword)
    draft = _make_draft()
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    category = compositor._select_font_category()
    assert category == expected_category, f"'{keyword}' → got '{category}', expected '{expected_category}'"


def test_font_category_niche_map_coverage() -> None:
    """NICHE_FONT_MAP must cover the 4 non-default categories."""
    categories = set(NICHE_FONT_MAP.values())
    assert "Adult" in categories
    assert "Kids" in categories
    assert "Activity" in categories
    assert "Pocket" in categories


# ---------------------------------------------------------------------------
# Tests: barcode area
# ---------------------------------------------------------------------------


def test_barcode_area_is_white_in_rendered_canvas() -> None:
    """After _render_canvas the barcode zone must be white."""
    with tempfile.TemporaryDirectory() as tmpdir:
        front_path = Path(tmpdir) / "front.png"
        icc_path = Path(tmpdir) / "USWebCoatedSWOP.icc"
        _make_cover_png(front_path, 2550, 3300, dpi=300)
        _make_stub_icc(icc_path)

        plan = _make_plan(TrimSize.LETTER)
        draft = _make_draft(page_count=75)
        compositor = CoverCompositor(plan, draft, front_path)
        geom = compositor._compute_geometry()

        # Mock fonts dir to avoid font file requirement
        with patch(
            "colorforge_agents.generator.cover_compositor._FONTS_DIR",
            Path(tmpdir),
        ):
            canvas, _, source_dpi = compositor._render_canvas(geom, "Default", spine_eligible=False)

        # Sample barcode region pixels — must be (nearly) all white
        bx = int(geom.barcode_x_pt / 72 * 300)
        by_pt = geom.barcode_y_pt / 72
        canvas_h = canvas.size[1]
        by_px = canvas_h - int(by_pt * 300) - int(1.2 * 300)
        bw = int(2.0 * 300)
        bh = int(1.2 * 300)
        region = canvas.crop((bx, by_px, bx + bw, by_px + bh))
        pixels = list(region.getdata())
        white_pct = sum(
            1 for p in pixels if p[0] >= 250 and p[1] >= 250 and p[2] >= 250
        ) / len(pixels)
        assert white_pct >= 0.95, f"Barcode area only {white_pct*100:.1f}% white"


# ---------------------------------------------------------------------------
# Tests: DPI validation
# ---------------------------------------------------------------------------


def test_low_dpi_image_raises_compliance_error() -> None:
    """A 150 DPI source image must trigger FAIL on DPI_300 check."""
    plan = _make_plan()
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    canvas = Image.new("RGB", (
        int(geom.cover_width_in * 300),
        int(geom.cover_height_in * 300),
    ), color=(255, 255, 255))

    report = CoverComplianceValidator.validate_canvas(
        canvas_rgb=canvas,
        geometry=geom,
        text_bboxes=[],
        spine_text_included=False,
        page_count=75,
        source_dpi=(150.0, 150.0),  # low DPI
    )
    failed_checks = [f[0] for f in report.failures]
    assert CoverValidationCheck.DPI_300 in failed_checks


def test_300_dpi_source_passes() -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/fake.png"))
    geom = compositor._compute_geometry()

    canvas = Image.new("RGB", (
        int(geom.cover_width_in * 300),
        int(geom.cover_height_in * 300),
    ), color=(255, 255, 255))

    report = CoverComplianceValidator.validate_canvas(
        canvas_rgb=canvas,
        geometry=geom,
        text_bboxes=[],
        spine_text_included=False,
        page_count=75,
        source_dpi=(300.0, 300.0),
    )
    passed = [c for c in report.passed]
    assert CoverValidationCheck.DPI_300 in passed


# ---------------------------------------------------------------------------
# Tests: filename sanitization
# ---------------------------------------------------------------------------


def test_filename_sanitization_removes_emoji() -> None:
    name = "🌊 Ocean Mandala: Book #1"
    safe = _sanitize_filename(name)
    assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in safe)
    assert len(safe) > 0


def test_filename_sanitization_ascii_unchanged() -> None:
    name = "Ocean-Mandala_v2.3"
    assert _sanitize_filename(name) == name


def test_filename_sanitization_unicode_replaced() -> None:
    name = "Mándalà Colöring"
    safe = _sanitize_filename(name)
    assert "á" not in safe
    assert "à" not in safe
    assert "ö" not in safe


# ---------------------------------------------------------------------------
# Tests: full compose pipeline (mocked ICC + fonts)
# ---------------------------------------------------------------------------


def _passing_validation_report() -> CoverValidationReport:
    return CoverValidationReport(
        passed=list(CoverValidationCheck),
        warnings=[],
        failures=[],
        overall_verdict="pass",
    )


def test_compose_full_pipeline_pocket_mandala(tmp_path: Path) -> None:
    """Full compose on POCKET trim, 75 pages, mandala niche — mocked ICC + fonts."""
    front_path = tmp_path / "front.png"
    _make_cover_png(front_path, 1800, 2700, dpi=300)

    stub_icc = tmp_path / "USWebCoatedSWOP.icc"
    _make_stub_icc(stub_icc)

    plan = _make_plan(trim_size=TrimSize.POCKET, keyword="mandala coloring book")
    draft = _make_draft(page_count=75, title="Pocket Mandala")
    compositor = CoverCompositor(plan, draft, front_path)

    def _fake_cmyk(img: Image.Image) -> Image.Image:
        return img.convert("CMYK")

    with (
        patch("colorforge_agents.generator.cover_compositor._ICC_PROFILE_PATH", stub_icc),
        patch("colorforge_agents.generator.cover_compositor._FONTS_DIR", tmp_path),
        patch.object(compositor, "_convert_to_cmyk", side_effect=_fake_cmyk),
        patch.object(CoverComplianceValidator, "validate_pdf", return_value=_passing_validation_report()),
    ):
        result = compositor.compose(tmp_path / "output")

    assert result.pdf_path.exists()
    assert result.font_category == "Adult"
    assert result.cover_width_pt > 0
    assert result.spine_text_included is False  # 75 < 79


def test_compose_spine_included_at_80_pages(tmp_path: Path) -> None:
    front_path = tmp_path / "front.png"
    _make_cover_png(front_path, 2550, 3300, dpi=300)

    stub_icc = tmp_path / "USWebCoatedSWOP.icc"
    _make_stub_icc(stub_icc)

    plan = _make_plan(TrimSize.LETTER, keyword="mandala coloring book")
    draft = _make_draft(page_count=80, title="Spine Test Book")
    compositor = CoverCompositor(plan, draft, front_path)

    def _fake_cmyk(img: Image.Image) -> Image.Image:
        return img.convert("CMYK")

    with (
        patch("colorforge_agents.generator.cover_compositor._ICC_PROFILE_PATH", stub_icc),
        patch("colorforge_agents.generator.cover_compositor._FONTS_DIR", tmp_path),
        patch.object(compositor, "_convert_to_cmyk", side_effect=_fake_cmyk),
        patch.object(CoverComplianceValidator, "validate_pdf", return_value=_passing_validation_report()),
    ):
        result = compositor.compose(tmp_path / "output")

    assert result.spine_text_included is True
    assert result.pdf_path.exists()


def test_compose_missing_front_image_raises(tmp_path: Path) -> None:
    plan = _make_plan()
    draft = _make_draft()
    compositor = CoverCompositor(plan, draft, tmp_path / "nonexistent.png")
    with pytest.raises(FileNotFoundError, match="Cover image not found"):
        compositor.compose(tmp_path / "out")


def test_compose_missing_icc_raises(tmp_path: Path) -> None:
    front_path = tmp_path / "front.png"
    _make_cover_png(front_path, 800, 1200, dpi=300)

    plan = _make_plan()
    draft = _make_draft()
    compositor = CoverCompositor(plan, draft, front_path)

    with patch(
        "colorforge_agents.generator.cover_compositor._ICC_PROFILE_PATH",
        tmp_path / "missing.icc",
    ):
        with pytest.raises(FileNotFoundError, match="ICC profile not found"):
            compositor.compose(tmp_path / "out")


def test_compose_kids_niche_font_category(tmp_path: Path) -> None:
    front_path = tmp_path / "front.png"
    _make_cover_png(front_path, 2400, 3000, dpi=300)
    stub_icc = tmp_path / "USWebCoatedSWOP.icc"
    _make_stub_icc(stub_icc)

    plan = _make_plan(TrimSize.KIDS, keyword="kids dinosaur coloring book")
    draft = _make_draft(page_count=60, title="Dino Coloring")
    compositor = CoverCompositor(plan, draft, front_path)

    def _fake_cmyk(img: Image.Image) -> Image.Image:
        return img.convert("CMYK")

    with (
        patch("colorforge_agents.generator.cover_compositor._ICC_PROFILE_PATH", stub_icc),
        patch("colorforge_agents.generator.cover_compositor._FONTS_DIR", tmp_path),
        patch.object(compositor, "_convert_to_cmyk", side_effect=_fake_cmyk),
        patch.object(CoverComplianceValidator, "validate_pdf", return_value=_passing_validation_report()),
    ):
        result = compositor.compose(tmp_path / "output")

    assert result.font_category == "Kids"


# ---------------------------------------------------------------------------
# Tests: CoverComplianceValidator
# ---------------------------------------------------------------------------


def test_validator_bleed_present_fails_if_canvas_too_small() -> None:
    plan = _make_plan()
    draft = _make_draft()
    compositor = CoverCompositor(plan, draft, Path("/tmp/f.png"))
    geom = compositor._compute_geometry()

    tiny_canvas = Image.new("RGB", (10, 10))
    report = CoverComplianceValidator.validate_canvas(
        canvas_rgb=tiny_canvas,
        geometry=geom,
        text_bboxes=[],
        spine_text_included=False,
        page_count=75,
        source_dpi=(300.0, 300.0),
    )
    assert CoverValidationCheck.BLEED_PRESENT in [f[0] for f in report.failures]
    assert report.overall_verdict == "fail"


def test_validator_safe_zone_text_fails_on_violation() -> None:
    plan = _make_plan(TrimSize.LETTER)
    draft = _make_draft(page_count=75)
    compositor = CoverCompositor(plan, draft, Path("/tmp/f.png"))
    geom = compositor._compute_geometry()

    canvas = Image.new("RGB", (
        int(geom.cover_width_in * 300),
        int(geom.cover_height_in * 300),
    ))

    # Place text at (0, 0) — outside safe zone
    bad_bbox = (0, 0, 100, 50)
    report = CoverComplianceValidator.validate_canvas(
        canvas_rgb=canvas,
        geometry=geom,
        text_bboxes=[bad_bbox],
        spine_text_included=False,
        page_count=75,
        source_dpi=(300.0, 300.0),
    )
    assert CoverValidationCheck.SAFE_ZONE_TEXT in [f[0] for f in report.failures]


def test_validator_pdf_file_size_warn(tmp_path: Path) -> None:
    """A PDF over 40MB but under 650MB triggers FILE_SIZE warn."""
    from reportlab.pdfgen import canvas as rl_canvas

    pdf_path = tmp_path / "big.pdf"
    c = rl_canvas.Canvas(str(pdf_path), pagesize=(100, 100))
    c.showPage()
    c.save()

    # Patch file size to simulate >40MB
    with patch.object(Path, "stat") as mock_stat:
        mock_stat.return_value.st_size = 45 * 1024 * 1024
        report = CoverComplianceValidator.validate_pdf(pdf_path)

    warns = [w[0] for w in report.warnings]
    assert CoverValidationCheck.FILE_SIZE in warns


def test_validator_pdf_file_size_fail(tmp_path: Path) -> None:
    """A PDF over 650MB triggers FILE_SIZE fail."""
    from reportlab.pdfgen import canvas as rl_canvas

    pdf_path = tmp_path / "huge.pdf"
    c = rl_canvas.Canvas(str(pdf_path), pagesize=(100, 100))
    c.showPage()
    c.save()

    with patch.object(Path, "stat") as mock_stat:
        mock_stat.return_value.st_size = 700 * 1024 * 1024
        report = CoverComplianceValidator.validate_pdf(pdf_path)

    fails = [f[0] for f in report.failures]
    assert CoverValidationCheck.FILE_SIZE in fails
    assert report.overall_verdict == "fail"
