"""Tests for GeneratorCore."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookPlan, CoverBrief, PagePrompt
from colorforge_agents.generator.generator import GeneratorCore
from colorforge_agents.generator.pdf_assembler import PDFAssemblyResult
from colorforge_agents.generator.post_processor import ProcessedImage


def _minimal_png() -> bytes:
    """Return a valid 1×1 white PNG."""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108000000003a"
        "7e9b550000000a49444154789c6260000000020001e221bc330000000049454e44ae426082"
    )


def _plan(page_count: int = 20) -> BookPlan:
    return BookPlan(
        niche_brief_id="niche-001",
        account_id="acc-001",
        style_fingerprint="mandala-ocean",
        page_count=page_count,
        page_prompts=[
            PagePrompt(
                index=i,
                prompt=f"Test prompt for page {i}",
                complexity_tier="medium",
                theme="ocean",
            )
            for i in range(page_count)
        ],
        cover_brief=CoverBrief(
            subject="Ocean mandala cover",
            style_fingerprint="mandala-ocean",
            palette_hint="#000033",
            background_hint="white",
        ),
        target_keyword="ocean mandala",
        target_price=7.99,
        brand_author="Test Author",
    )


class _MockImageClient:
    _model = "gemini-test"

    async def generate_image(self, _prompt: str) -> bytes:
        return _minimal_png()


class _FailingImageClient:
    _model = "gemini-test"

    async def generate_image(self, _prompt: str) -> bytes:
        raise Exception("Gemini API down")


class _MockPostProcessor:
    def process(self, image_bytes: bytes) -> ProcessedImage:
        return ProcessedImage(
            data=image_bytes, artifact_detected=False, width_px=2550, height_px=3300
        )


class _MockPDFAssembler:
    def spine_width_inches(self, _page_count: int) -> float:
        return 0.169

    def assemble_manuscript(self, pages: list[Path], output_path: Path) -> PDFAssemblyResult:
        output_path.write_bytes(b"%PDF-1.4 mock")
        return PDFAssemblyResult(
            output_path=str(output_path),
            page_width_pts=630.0,
            page_height_pts=819.0,
            page_count=len(pages),
        )

    def assemble_cover(self, _cover: Path, _pc: int, output_path: Path) -> PDFAssemblyResult:
        output_path.write_bytes(b"%PDF-1.4 mock cover")
        return PDFAssemblyResult(
            output_path=str(output_path),
            page_width_pts=1278.0,
            page_height_pts=819.0,
            page_count=1,
        )


class _MockPrisma:
    async def book_create(self, **_: Any) -> None:
        pass


def _make_core(tmp_path: Path, image_client: Any = None) -> GeneratorCore:
    return GeneratorCore(
        image_client=image_client or _MockImageClient(),
        post_processor=_MockPostProcessor(),
        pdf_assembler=_MockPDFAssembler(),
        prisma=_MockPrisma(),
        assets_base=tmp_path,
    )


class TestBookDraftStructure:
    async def test_returns_book_draft(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert isinstance(draft, BookDraft)

    async def test_book_id_is_uuid(self, tmp_path: Path) -> None:
        import uuid
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        uuid.UUID(draft.book_id)  # raises if invalid

    async def test_page_count_matches_plan(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert len(draft.pages) == 20
        assert draft.total_pages == 20

    async def test_page_indices_sequential(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert [p.index for p in draft.pages] == list(range(20))

    async def test_metadata_model_version(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert draft.generation_metadata.generator_model_version == "gemini-test"

    async def test_pdf_paths_set(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert draft.manuscript_pdf_path.endswith("manuscript.pdf")
        assert draft.cover_pdf_path.endswith("cover.pdf")

    async def test_spine_width_positive(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(75))
        assert draft.spine_width_inches > 0


class TestPageGeneration:
    async def test_successful_pages_have_pass_status(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        for page in draft.pages:
            assert page.validation_status in ("pass", "warn")

    async def test_prompt_preserved_in_draft_page(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert "Test prompt for page 0" in draft.pages[0].prompt_used

    async def test_failed_page_on_api_error(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path, image_client=_FailingImageClient())
        draft = await core.generate(_plan(20))
        for page in draft.pages:
            assert page.validation_status == "fail"
            assert page.image_path == ""

    async def test_generation_time_recorded(self, tmp_path: Path) -> None:
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(20))
        assert draft.generation_metadata.total_generation_time_ms >= 0


class TestConcurrency:
    async def test_large_plan_completes(self, tmp_path: Path) -> None:
        # 25 pages — exercises semaphore with > _MAX_CONCURRENT pages
        core = _make_core(tmp_path)
        draft = await core.generate(_plan(25))
        assert len(draft.pages) == 25
