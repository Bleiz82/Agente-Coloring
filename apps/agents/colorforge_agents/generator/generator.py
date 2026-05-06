"""Generator agent — produces a BookDraft from a BookPlan."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.book_plan import BookPlan, CoverBrief, PagePrompt
from colorforge_agents.exceptions import ImageGenerationError
from colorforge_agents.generator.image_gen import GeminiImageClient
from colorforge_agents.generator.pdf_assembler import PDFAssembler
from colorforge_agents.generator.post_processor import ImagePostProcessor

_MAX_CONCURRENT = 3
_MAX_PAGE_RETRIES = 2
_COVER_PROMPT_TEMPLATE = (
    "Black and white coloring book cover illustration. "
    "Subject: {subject}. "
    "Style: {style_fingerprint}, clean bold outlines, NO shading, NO gradients, NO color. "
    "Color palette for print: {palette_hint}. "
    "Background: {background_hint}. "
    "Composition: centered, high-impact thumbnail at 200px width. "
    "Text area: leave 20% blank space at top for title overlay."
)


class GeneratorCore:
    """Orchestrates image generation, post-processing, and PDF assembly."""

    def __init__(
        self,
        image_client: GeminiImageClient,
        post_processor: ImagePostProcessor,
        pdf_assembler: PDFAssembler,
        prisma: Any,
        assets_base: Path,
    ) -> None:
        self._image_client = image_client
        self._post_processor = post_processor
        self._pdf_assembler = pdf_assembler
        self._prisma = prisma
        self._assets_base = assets_base
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def generate(self, plan: BookPlan) -> BookDraft:
        """Generate all pages + cover, assemble PDFs, return BookDraft."""
        book_id = str(uuid.uuid4())
        book_dir = self._assets_base / plan.account_id / book_id
        pages_dir = book_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Generator starting book_id={} keyword='{}' pages={}",
            book_id,
            plan.target_keyword,
            plan.page_count,
        )
        t_start = time.monotonic()

        # Generate all pages concurrently (semaphore-limited)
        tasks = [
            self._generate_page(pp, pages_dir / f"page_{pp.index:03d}.png")
            for pp in plan.page_prompts
        ]
        draft_pages: list[DraftPage] = list(await asyncio.gather(*tasks))

        # Generate cover
        cover_png = book_dir / "cover.png"
        cover_path = await self._generate_cover(plan.cover_brief, cover_png)

        # Assemble PDFs
        page_paths = [pages_dir / f"page_{i:03d}.png" for i in range(plan.page_count)]
        existing_pages = [p for p in page_paths if p.exists()]

        manuscript_pdf = book_dir / "manuscript.pdf"
        cover_pdf = book_dir / "cover.pdf"

        # When all pages failed, skip PDF assembly and use placeholder paths
        if existing_pages:
            manuscript_result = self._pdf_assembler.assemble_manuscript(
                existing_pages, manuscript_pdf
            )
            ms_path = manuscript_result.output_path
        else:
            manuscript_pdf.touch()
            ms_path = str(manuscript_pdf)
            logger.warning("book_id={} — all pages failed, manuscript PDF is empty", book_id)

        cover_result = self._pdf_assembler.assemble_cover(
            cover_path, plan.page_count, cover_pdf
        )

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        pages_generated = sum(1 for p in draft_pages if p.validation_status != "fail")
        pages_regenerated = sum(
            1 for p in draft_pages
            if p.validation_status == "warn"  # warn = generated after retry
        )

        spine_w = self._pdf_assembler.spine_width_inches(plan.page_count)

        draft = BookDraft(
            book_id=book_id,
            manuscript_pdf_path=ms_path,
            cover_pdf_path=cover_result.output_path,
            pages=draft_pages,
            spine_width_inches=spine_w,
            total_pages=plan.page_count,
            generation_metadata=GenerationMetadata(
                generator_model_version=self._image_client._model,
                total_generation_time_ms=elapsed_ms,
                total_cost_usd=0.0,  # cost tracking deferred to M6
                pages_generated=pages_generated,
                pages_regenerated=pages_regenerated,
            ),
        )

        await self._write_to_db(draft, plan)
        logger.info("Generator done book_id={} elapsed_ms={}", book_id, elapsed_ms)
        return draft

    async def _generate_page(self, page_prompt: PagePrompt, output_path: Path) -> DraftPage:
        """Generate a single page with retry. Returns DraftPage (fail if all retries exhausted)."""
        async with self._semaphore:
            status: Literal["pending", "pass", "warn", "fail"] = "pass"
            for attempt in range(1, _MAX_PAGE_RETRIES + 2):
                try:
                    image_bytes = await self._image_client.generate_image(page_prompt.prompt)
                    processed = self._post_processor.process(image_bytes)
                    output_path.write_bytes(processed.data)
                    if attempt > 1:
                        status = "warn"  # generated after retry
                    logger.debug("Page {} generated (attempt {})", page_prompt.index, attempt)
                    return DraftPage(
                        index=page_prompt.index,
                        image_path=str(output_path),
                        prompt_used=page_prompt.prompt,
                        validation_status=status,
                    )
                except (ImageGenerationError, Exception) as exc:
                    if attempt > _MAX_PAGE_RETRIES:
                        logger.error(
                            "Page {} failed after {} attempts: {}",
                            page_prompt.index,
                            _MAX_PAGE_RETRIES + 1,
                            exc,
                        )
                        return DraftPage(
                            index=page_prompt.index,
                            image_path="",
                            prompt_used=page_prompt.prompt,
                            validation_status="fail",
                        )
                    logger.warning(
                        "Page {} attempt {} failed: {}", page_prompt.index, attempt, exc
                    )
        # unreachable — semaphore always released
        return DraftPage(
            index=page_prompt.index,
            image_path="",
            prompt_used=page_prompt.prompt,
            validation_status="fail",
        )

    async def _generate_cover(self, brief: CoverBrief, output_path: Path) -> Path:
        """Generate the cover image and return its path."""
        prompt = _COVER_PROMPT_TEMPLATE.format(
            subject=brief.subject,
            style_fingerprint=brief.style_fingerprint,
            palette_hint=brief.palette_hint,
            background_hint=brief.background_hint,
        )
        try:
            image_bytes = await self._image_client.generate_image(prompt)
            processed = self._post_processor.process(image_bytes)
            output_path.write_bytes(processed.data)
            return output_path
        except Exception as exc:
            logger.error("Cover generation failed: {}", exc)
            # Write a blank white placeholder so PDF assembly doesn't crash
            self._write_blank_cover(output_path)
            return output_path

    def _write_blank_cover(self, output_path: Path) -> None:
        """Write a minimal blank white PNG as cover fallback."""
        try:
            from PIL import Image

            img = Image.new("L", (2550, 3300), color=255)
            img.save(str(output_path), format="PNG", dpi=(300, 300))
        except Exception:
            # Last resort: write empty bytes (PDF assembler will raise cleanly)
            output_path.write_bytes(b"")

    async def _write_to_db(self, draft: BookDraft, plan: BookPlan) -> None:
        try:
            await self._prisma.book_create(
                data={
                    "id": draft.book_id,
                    "nicheBriefId": plan.niche_brief_id,
                    "accountId": plan.account_id,
                    "manuscriptPdfPath": draft.manuscript_pdf_path,
                    "coverPdfPath": draft.cover_pdf_path,
                    "totalPages": draft.total_pages,
                    "spineWidthInches": draft.spine_width_inches,
                    "status": "GENERATING",
                    "createdAt": datetime.now(tz=UTC).isoformat(),
                }
            )
        except Exception as exc:
            logger.error("DB write failed for book {}: {}", draft.book_id, exc)
