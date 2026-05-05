"""Claude-based LLM analysis for pain points, styles, and differentiators."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
from loguru import logger

from colorforge_agents.contracts.niche_brief import (
    Differentiator,
    PainPoint,
    StyleClassification,
)
from colorforge_agents.exceptions import LLMAnalysisError

_PAIN_POINT_SYSTEM = """
You are a product analyst for Amazon KDP coloring books. Given 1-2 star reviews, extract
the recurring pain points buyers complain about. Return a JSON array. Each element must have:
  - "text": concise description of the pain point
  - "source_review_ids": list of review IDs mentioning it
  - "severity": integer 1-5 (5 = most severe, most frequently mentioned)
  - "category": one of [line_quality, subject_variety, page_count, paper_quality,
                        image_quality, printing_defect, price_value, other]
Return only valid JSON, no commentary.
""".strip()

_STYLE_SYSTEM = """
You are a visual style analyst for Amazon KDP coloring books. Given cover images of the
top-selling books in a niche, classify the dominant visual styles. Return a JSON array.
Each element must have:
  - "name": short style label (e.g. "geometric-mandala", "whimsical-animals")
  - "prevalence": percentage (0-100) of covers matching this style
  - "examples": list of ASIN strings for representative covers
Return only valid JSON, no commentary.
""".strip()

_DIFFERENTIATOR_SYSTEM = """
You are a product strategy expert for Amazon KDP coloring books. Given a list of competitor
pain points and the dominant visual styles, suggest specific differentiators that would make
a new book stand out. Return a JSON array. Each element must have:
  - "description": actionable differentiator
  - "rationale": why this addresses a real buyer need
  - "estimated_impact": one of ["low", "medium", "high"]
Return only valid JSON, no commentary.
""".strip()


class LLMAnalyzer:
    """Wraps Claude Sonnet 4.6 for structured extraction tasks."""

    _MODEL = "claude-sonnet-4-6"

    def __init__(self, client: Any) -> None:  # anthropic.AsyncAnthropic
        self._client = client

    async def extract_pain_points(
        self, reviews: list[dict[str, Any]]
    ) -> list[PainPoint]:
        if not reviews:
            return []

        review_blob = "\n\n".join(
            f"[{r['review_id']}] (rating: {r['rating']})\n{r['text']}"
            for r in reviews
        )
        user_msg = f"Reviews to analyze:\n\n{review_blob}"

        raw = await self._call_claude(_PAIN_POINT_SYSTEM, user_msg)
        try:
            data: list[dict[str, Any]] = json.loads(raw)
            return [PainPoint(**item) for item in data]
        except Exception as exc:
            raise LLMAnalysisError(f"Pain point parse failed: {exc}") from exc

    async def classify_cover_styles(
        self, cover_urls: list[str]
    ) -> list[StyleClassification]:
        if not cover_urls:
            return []

        image_blocks = await self._build_image_blocks(cover_urls)
        if not image_blocks:
            return []

        messages = [
            {
                "role": "user",
                "content": image_blocks
                + [{"type": "text", "text": "Classify the visual styles of these covers."}],
            }
        ]
        raw = await self._call_claude_messages(_STYLE_SYSTEM, messages)
        try:
            data: list[dict[str, Any]] = json.loads(raw)
            return [StyleClassification(**item) for item in data]
        except Exception as exc:
            raise LLMAnalysisError(f"Style parse failed: {exc}") from exc

    async def suggest_differentiators(
        self,
        pain_points: list[PainPoint],
        styles: list[StyleClassification],
    ) -> list[Differentiator]:
        user_msg = (
            "Pain points:\n"
            + json.dumps([p.model_dump() for p in pain_points], indent=2)
            + "\n\nDominant styles:\n"
            + json.dumps([s.model_dump() for s in styles], indent=2)
        )
        raw = await self._call_claude(_DIFFERENTIATOR_SYSTEM, user_msg)
        try:
            data: list[dict[str, Any]] = json.loads(raw)
            return [Differentiator(**item) for item in data]
        except Exception as exc:
            raise LLMAnalysisError(f"Differentiator parse failed: {exc}") from exc

    async def _call_claude(self, system: str, user: str) -> str:
        messages = [{"role": "user", "content": user}]
        return await self._call_claude_messages(system, messages)

    async def _call_claude_messages(
        self, system: str, messages: list[dict[str, Any]]
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._MODEL,
                max_tokens=2048,
                system=system,
                messages=messages,
            )
            return str(response.content[0].text)
        except Exception as exc:
            raise LLMAnalysisError(f"Claude API error: {exc}") from exc

    @staticmethod
    async def _build_image_blocks(urls: list[str]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for url in urls[:10]:  # cap at 10 images to manage token budget
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
                        b64 = base64.b64encode(resp.content).decode()
                        blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": b64,
                            },
                        })
                except Exception as exc:
                    logger.debug("Image fetch failed for {}: {}", url, exc)
        return blocks

    async def summarize_vision_analysis(
        self,
        pain_points: list[PainPoint],
        styles: list[StyleClassification],
    ) -> str:
        if not pain_points and not styles:
            return "No data available for vision analysis."

        top_pains = sorted(pain_points, key=lambda p: p.severity, reverse=True)[:3]
        top_styles = sorted(styles, key=lambda s: s.prevalence, reverse=True)[:2]

        parts: list[str] = []
        if top_styles:
            style_names = ", ".join(s.name for s in top_styles)
            parts.append(f"Dominant styles: {style_names}.")
        if top_pains:
            pain_texts = "; ".join(p.text for p in top_pains)
            parts.append(f"Top complaints: {pain_texts}.")
        return " ".join(parts)
