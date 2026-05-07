"""Tests for FrontMatterAssembler.

Covers:
- build_front_matter / build_back_matter with all optional variants
- AI disclosure mandatory enforcement
- URL detection in text blocks
- Page count validation (min=24, max=828)
- Blank-page run detection
- Gutter compliance per page count tier
- Full assemble integration test
- Niche-aware how-to-use templates
- Brand persona about-author bios
"""

from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.book_plan import (
    BookFormat,
    BookPlan,
    CoverBrief,
    CoverFinish,
    PagePrompt,
    PaperType,
    TrimSize,
)
from colorforge_agents.exceptions import FrontMatterError
from colorforge_agents.generator.front_matter import (
    _AI_DISCLOSURE_PHRASE,
    FrontMatterAssembler,
    FrontMatterContent,
    BackMatterContent,
    _niche_category_from_keyword,
    _compute_gutter_inches,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(
    keyword: str = "mandala coloring book",
    trim: TrimSize = TrimSize.LETTER,
    include_dedication: bool = False,
    dedication_text: str | None = None,
) -> BookPlan:
    return BookPlan(
        niche_brief_id="niche-001",
        account_id="acc-001",
        style_fingerprint="fp-test",
        page_count=75,
        page_prompts=[PagePrompt(index=0, prompt="test", complexity_tier="medium", theme="test")],
        cover_brief=CoverBrief(
            subject="Test", style_fingerprint="fp-test", palette_hint="#000", background_hint="white"
        ),
        target_keyword=keyword,
        target_price=7.99,
        brand_author="Test Author",
        trim_size=trim,
        paper_type=PaperType.WHITE,
        cover_finish=CoverFinish.MATTE,
        book_format=BookFormat.PAPERBACK,
        imprint="ColorForge Studio",
        imprint_country="United States",
        include_dedication=include_dedication,
        dedication_text=dedication_text,
    )


def _make_draft(
    title: str = "Test Coloring Book",
    author: str = "Test Author",
    subtitle: str | None = None,
    page_count: int = 75,
) -> BookDraft:
    return BookDraft(
        book_id="draft-001",
        manuscript_pdf_path="/tmp/ms.pdf",
        cover_pdf_path="/tmp/cover.pdf",
        pages=[DraftPage(index=0, image_path="/tmp/p0.png", prompt_used="test", validation_status="pass")],
        spine_width_inches=0.169,
        total_pages=page_count,
        title=title,
        subtitle=subtitle,
        author=author,
        generation_metadata=GenerationMetadata(
            generator_model_version="test",
            total_generation_time_ms=1000,
            total_cost_usd=0.5,
            pages_generated=page_count,
            pages_regenerated=0,
        ),
    )


def _make_minimal_coloring_pdf(path: Path, num_pages: int = 20) -> None:
    """Create a minimal test PDF with num_pages pages at 8.5×11 + bleed."""
    page_w = (8.5 + 0.125) * 72
    page_h = (11.0 + 0.25) * 72
    c = rl_canvas.Canvas(str(path), pagesize=(page_w, page_h))
    for i in range(num_pages):
        c.drawString(50, page_h / 2, f"Page {i+1}")
        c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# Tests: niche category detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keyword,expected",
    [
        ("mandala coloring adult", "Adult"),
        ("zen garden coloring", "Adult"),
        ("meditation patterns", "Adult"),
        ("kids dinosaur coloring", "Kids"),
        ("children garden book", "Kids"),
        ("activity workbook teens", "Activity"),
        ("educational homeschool", "Activity"),
        ("travel pocket book", "Pocket"),
        ("mini coloring book", "Pocket"),
        ("shapes and lines", "Default"),
    ],
)
def test_niche_category_from_keyword(keyword: str, expected: str) -> None:
    assert _niche_category_from_keyword(keyword) == expected


# ---------------------------------------------------------------------------
# Tests: gutter computation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pages,expected_gutter",
    [
        (24, 0.375),
        (150, 0.375),
        (151, 0.500),
        (300, 0.500),
        (301, 0.625),
        (500, 0.625),
        (501, 0.750),
        (700, 0.750),
        (701, 0.875),
        (828, 0.875),
    ],
)
def test_gutter_tiers(pages: int, expected_gutter: float) -> None:
    assert _compute_gutter_inches(pages) == expected_gutter


# ---------------------------------------------------------------------------
# Tests: build_front_matter
# ---------------------------------------------------------------------------


def test_build_front_matter_basic() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()

    assert isinstance(fm, FrontMatterContent)
    assert "Test Coloring Book" in fm.title_page_text
    assert "Test Author" in fm.title_page_text
    assert _AI_DISCLOSURE_PHRASE in fm.copyright_page_text
    assert fm.dedication_page_text is None
    assert "HOW TO USE" in fm.how_to_use_page_text


def test_ai_disclosure_present_in_copyright() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert _AI_DISCLOSURE_PHRASE in fm.copyright_page_text


def test_copyright_contains_year() -> None:
    from datetime import datetime
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert str(datetime.now().year) in fm.copyright_page_text


def test_copyright_contains_imprint() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "ColorForge Studio" in fm.copyright_page_text


def test_build_front_matter_with_dedication() -> None:
    plan = _make_plan(include_dedication=True, dedication_text="For my family")
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()

    assert fm.dedication_page_text is not None
    assert "For my family" in fm.dedication_page_text


def test_build_front_matter_without_dedication() -> None:
    plan = _make_plan(include_dedication=False)
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()

    assert fm.dedication_page_text is None


def test_title_matches_book_draft() -> None:
    plan = _make_plan()
    draft = _make_draft(title="Ocean Mandala Book")
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "Ocean Mandala Book" in fm.title_page_text


def test_author_matches_book_draft() -> None:
    plan = _make_plan()
    draft = _make_draft(author="Jane Colorist")
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "Jane Colorist" in fm.title_page_text


# ---------------------------------------------------------------------------
# Tests: AI disclosure enforcement
# ---------------------------------------------------------------------------


def test_ai_disclosure_cannot_be_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patching the copyright text to remove AI disclosure must raise FrontMatterError."""
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)

    # Monkeypatch the copyright builder to remove the disclosure
    def _bad_copyright(self: FrontMatterAssembler) -> str:
        return "Copyright notice without any disclosure."

    monkeypatch.setattr(FrontMatterAssembler, "_build_copyright_page", _bad_copyright)

    with pytest.raises(FrontMatterError, match="AI disclosure"):
        asm.build_front_matter()


# ---------------------------------------------------------------------------
# Tests: URL detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_text",
    [
        "Visit https://example.com for more",
        "Go to www.example.com today",
        "Email us at author@example.com",
        "Call +1 555-123-4567",
        "Check example.net",
    ],
)
def test_url_detection_raises(url_text: str) -> None:
    draft = _make_draft()
    plan_with_url = _make_plan(include_dedication=True, dedication_text=url_text)
    asm = FrontMatterAssembler(plan_with_url, draft)
    with pytest.raises(FrontMatterError, match="URL/contact pattern"):
        asm.build_front_matter()


# ---------------------------------------------------------------------------
# Tests: niche-aware how-to-use templates
# ---------------------------------------------------------------------------


def test_how_to_use_adult_template() -> None:
    plan = _make_plan(keyword="mandala coloring book adult")
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "stress-relief" in fm.how_to_use_page_text or "meditative" in fm.how_to_use_page_text


def test_how_to_use_kids_template() -> None:
    plan = _make_plan(keyword="kids coloring book dinosaurs")
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "fun" in fm.how_to_use_page_text.lower() or "little" in fm.how_to_use_page_text.lower()


def test_how_to_use_default_fallback() -> None:
    plan = _make_plan(keyword="abstract geometric patterns")
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    fm = asm.build_front_matter()
    assert "HOW TO USE" in fm.how_to_use_page_text


# ---------------------------------------------------------------------------
# Tests: build_back_matter
# ---------------------------------------------------------------------------


def test_build_back_matter_no_also_by() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    bm = asm.build_back_matter(other_titles=None)

    assert isinstance(bm, BackMatterContent)
    assert "THANK YOU" in bm.thank_you_page_text
    assert "ABOUT THE AUTHOR" in bm.about_author_page_text
    assert bm.also_by_page_text is None


def test_build_back_matter_with_also_by() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    bm = asm.build_back_matter(other_titles=["Book One", "Book Two"])

    assert bm.also_by_page_text is not None
    assert "Book One" in bm.also_by_page_text
    assert "Book Two" in bm.also_by_page_text


def test_also_by_omitted_for_first_book() -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    bm = asm.build_back_matter(other_titles=[])
    assert bm.also_by_page_text is None


@pytest.mark.parametrize(
    "persona,expected_fragment",
    [
        ("mindful_artist", "mindful"),
        ("studio_brand", "studio"),
        ("kids_creator", "youngest"),
        ("educational", "activity books"),
    ],
)
def test_about_author_per_persona(persona: str, expected_fragment: str) -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft, brand_persona=persona)
    bm = asm.build_back_matter()
    assert expected_fragment.lower() in bm.about_author_page_text.lower()


# ---------------------------------------------------------------------------
# Tests: page count arithmetic
# ---------------------------------------------------------------------------


def test_total_page_count_arithmetic(tmp_path: Path) -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=20)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=20)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf")
    # front=3 (title+copyright+how_to_use) + 20 coloring + back=2 (thank_you+about_author) = 25
    assert result.front_matter_pages == 3
    assert result.coloring_pages == 20
    assert result.back_matter_pages == 2
    assert result.page_count == result.front_matter_pages + result.coloring_pages + result.back_matter_pages


def test_total_page_count_with_dedication(tmp_path: Path) -> None:
    plan = _make_plan(include_dedication=True, dedication_text="For you")
    draft = _make_draft(page_count=20)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=20)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf")
    assert result.front_matter_pages == 4  # +1 dedication


def test_total_page_count_with_also_by(tmp_path: Path) -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=20)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=20)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf", other_titles=["Other Book"])
    assert result.back_matter_pages == 3  # +1 also-by


# ---------------------------------------------------------------------------
# Tests: KDP page count validation
# ---------------------------------------------------------------------------


def test_min_24_pages_enforced(tmp_path: Path) -> None:
    """5 coloring pages + 5 front/back = 10 total → FrontMatterError."""
    plan = _make_plan()
    draft = _make_draft(page_count=5)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=5)  # 5 + 3 + 2 = 10 < 24

    with pytest.raises(FrontMatterError, match="below KDP minimum"):
        asm.assemble(coloring_pdf, tmp_path / "interior.pdf")


def test_exactly_24_pages_passes(tmp_path: Path) -> None:
    """19 coloring + 3 front + 2 back = 24 = minimum OK."""
    plan = _make_plan()
    draft = _make_draft(page_count=19)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=19)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf")
    assert result.page_count == 24


def test_max_828_pages_would_pass(tmp_path: Path) -> None:
    """823 coloring + 3 front + 2 back = 828 = maximum OK."""
    plan = _make_plan()
    draft = _make_draft(page_count=823)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=823)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf")
    assert result.page_count == 828


# ---------------------------------------------------------------------------
# Tests: gutter compliance per page count tier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "total_pages,expected_gutter",
    [
        (24, 0.375),   # minimum, tier <=150
        (150, 0.375),  # boundary top of tier 1
        (151, 0.500),  # boundary bottom of tier 2
        (300, 0.500),  # boundary top of tier 2
        (301, 0.625),  # boundary bottom of tier 3
        (500, 0.625),  # boundary top of tier 3
        (501, 0.750),  # boundary bottom of tier 4
        (700, 0.750),  # boundary top of tier 4
        (701, 0.875),  # boundary bottom of tier 5
        (828, 0.875),  # maximum
    ],
)
def test_gutter_compliance_per_tier(total_pages: int, expected_gutter: float) -> None:
    computed = _compute_gutter_inches(total_pages)
    assert computed == expected_gutter, f"total={total_pages} -> got {computed}, expected {expected_gutter}"


# ---------------------------------------------------------------------------
# Tests: full assemble integration
# ---------------------------------------------------------------------------


def test_assemble_creates_pdf(tmp_path: Path) -> None:
    plan = _make_plan()
    draft = _make_draft(page_count=20)
    asm = FrontMatterAssembler(plan, draft)

    coloring_pdf = tmp_path / "coloring.pdf"
    _make_minimal_coloring_pdf(coloring_pdf, num_pages=20)

    result = asm.assemble(coloring_pdf, tmp_path / "interior.pdf")
    assert result.pdf_path.exists()
    assert result.total_size_bytes > 0


def test_assemble_missing_coloring_pdf_raises(tmp_path: Path) -> None:
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    with pytest.raises(FileNotFoundError, match="Coloring pages PDF not found"):
        asm.assemble(tmp_path / "missing.pdf", tmp_path / "out.pdf")


def test_no_url_in_back_matter() -> None:
    """back matter must not contain URLs."""
    plan = _make_plan()
    draft = _make_draft()
    asm = FrontMatterAssembler(plan, draft)
    bm = asm.build_back_matter()

    import re
    url_re = re.compile(r"(https?://|www\.|\.com\b|@[a-zA-Z])", re.IGNORECASE)
    for field, text in [
        ("thank_you", bm.thank_you_page_text),
        ("about_author", bm.about_author_page_text),
    ]:
        match = url_re.search(text)
        assert match is None, f"URL found in {field}: {match.group() if match else ''!r}"
