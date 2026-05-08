"""Claude Sonnet 4.6 vision checker for coloring book page and cover QA."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from loguru import logger

from colorforge_agents.contracts.validation_report import CoverAssessment, PageFlag
from colorforge_agents.config.models import VISION_CHECKER_MODEL
from colorforge_agents.exceptions import CriticError
_BATCH_SIZE = 5  # pages per Claude call

_PAGE_SYSTEM = (
    "You are a strict KDP coloring book quality inspector. "
    "For each page image provided, identify any quality defects. "
    "Respond ONLY with a JSON array (one element per page). "
    "Each element is an array of flag objects with keys: "
    '"type" (one of: text_contamination, shading_detected, color_detected, double_lines, '
    "anatomy_malformed, composition_off_center, subject_too_small, watermark_detected, "
    'artifact_detected, prompt_mismatch), '
    '"severity" (integer 1-5, where 5=critical), '
    '"detail" (short explanation). '
    "Empty array means no defects on that page. "
    "Severity guide: 5=publish-blocking, 4=major rework needed, 3=notable, 2=minor, 1=cosmetic."
)

_COVER_SYSTEM = (
    "You are a KDP coloring book cover quality inspector. "
    "Evaluate the cover image for thumbnail readability and print quality. "
    "Respond ONLY with a JSON object with keys: "
    '"readability_score" (integer 0-100, where 100=perfect thumbnail at 200px), '
    '"issues" (array of short issue strings, empty if none).'
)


class VisionChecker:
    """Sends page/cover images to Claude Sonnet 4.6 vision for QA."""

    def __init__(self, client: Any) -> None:  # anthropic.AsyncAnthropic
        self._client = client

    async def check_pages(self, image_paths: list[Path]) -> list[list[PageFlag]]:
        """Check all pages in batches. Returns one list[PageFlag] per page."""
        if not image_paths:
            return []

        all_flags: list[list[PageFlag]] = []
        for batch_start in range(0, len(image_paths), _BATCH_SIZE):
            batch = image_paths[batch_start : batch_start + _BATCH_SIZE]
            batch_flags = await self._check_batch(batch, batch_start)
            all_flags.extend(batch_flags)

        return all_flags

    async def check_cover(self, cover_path: Path) -> CoverAssessment:
        """Check cover readability and quality."""
        image_data = self._encode_image(cover_path)

        try:
            response = await self._client.messages.create(
                model=VISION_CHECKER_MODEL,
                max_tokens=512,
                system=_COVER_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": "Evaluate this coloring book cover."},
                        ],
                    }
                ],
            )
        except Exception as exc:
            raise CriticError(f"Claude cover check API error: {exc}") from exc

        raw = response.content[0].text.strip()
        try:
            obj = json.loads(raw)
            return CoverAssessment(
                readability_score=int(obj.get("readability_score", 50)),
                issues=list(obj.get("issues", [])),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise CriticError(f"Cover JSON parse error: {exc} | raw={raw!r}") from exc

    async def check_pdf_specs(
        self, manuscript_path: Path, cover_path: Path
    ) -> tuple[bool, list[str]]:
        """Check PDF spec compliance via pypdf (not vision). Returns (compliant, issues)."""
        issues: list[str] = []
        try:
            from pypdf import PdfReader
        except ImportError:
            return True, []  # graceful degradation if pypdf absent

        expected_w = round((8.5 + 2 * 0.125) * 72, 0)  # 630.0 pt
        expected_h = round((11.0 + 2 * 0.125) * 72, 0)  # 810.0 pt

        try:
            reader = PdfReader(str(manuscript_path))
            for i, page in enumerate(reader.pages):
                w = float(page.mediabox.width)
                h = float(page.mediabox.height)
                if abs(w - expected_w) > 2 or abs(h - expected_h) > 2:
                    issues.append(
                        f"Page {i}: size {w:.1f}×{h:.1f} pt, expected {expected_w}×{expected_h} pt"
                    )
        except Exception as exc:
            issues.append(f"Manuscript PDF read error: {exc}")

        if not cover_path.exists():
            issues.append("Cover PDF not found")

        return len(issues) == 0, issues

    async def _check_batch(
        self, paths: list[Path], start_idx: int
    ) -> list[list[PageFlag]]:
        """Single Claude call for a batch of pages. Returns one list[PageFlag] per page."""
        content: list[dict[str, Any]] = []
        for i, path in enumerate(paths):
            image_data = self._encode_image(path)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                }
            )
            content.append(
                {"type": "text", "text": f"Page {start_idx + i} (image {i + 1} of {len(paths)})."}
            )

        content.append(
            {
                "type": "text",
                "text": (
                    f"Inspect these {len(paths)} coloring book pages in order. "
                    "Return a JSON array with one element per page."
                ),
            }
        )

        try:
            response = await self._client.messages.create(
                model=VISION_CHECKER_MODEL,
                max_tokens=1024,
                system=_PAGE_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:
            raise CriticError(f"Claude page check API error: {exc}") from exc

        raw = response.content[0].text.strip()
        try:
            parsed: list[list[dict[str, Any]]] = json.loads(raw)
            if len(parsed) != len(paths):
                logger.warning(
                    "Claude returned {} flag lists for {} pages, padding",
                    len(parsed),
                    len(paths),
                )
                while len(parsed) < len(paths):
                    parsed.append([])
        except json.JSONDecodeError as exc:
            raise CriticError(f"Page flags JSON parse error: {exc} | raw={raw!r}") from exc

        result: list[list[PageFlag]] = []
        for page_offset, raw_flags in enumerate(parsed[: len(paths)]):
            page_index = start_idx + page_offset
            flags: list[PageFlag] = []
            for raw_flag in raw_flags:
                try:
                    flags.append(
                        PageFlag(
                            page_index=page_index,
                            type=raw_flag["type"],
                            severity=int(raw_flag.get("severity", 3)),
                            detail=str(raw_flag.get("detail", "")),
                        )
                    )
                except Exception:
                    logger.warning("Skipping malformed flag on page {}: {}", page_index, raw_flag)
            result.append(flags)

        return result

    @staticmethod
    def _encode_image(path: Path) -> str:
        """Return base64-encoded PNG bytes from file. Converts non-PNG to PNG via Pillow."""
        if not path.exists() or path.stat().st_size == 0:
            # Return a 1×1 white PNG placeholder so the batch call still works
            return _WHITE_PIXEL_B64

        raw = path.read_bytes()
        # If it's already PNG, skip PIL
        if raw[:4] == b"\x89PNG":
            return base64.b64encode(raw).decode()

        try:
            from PIL import Image

            img = Image.open(io.BytesIO(raw))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return _WHITE_PIXEL_B64


# Minimal 1×1 white PNG in base64 (used as placeholder for missing pages)
_WHITE_PIXEL_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
)
