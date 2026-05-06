"""Tests for SEOListingCore."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.book_plan import BookPlan, CoverBrief, PagePrompt
from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.contracts.niche_brief import (
    Differentiator,
    NicheBrief,
    PainPoint,
    StyleClassification,
)
from colorforge_agents.exceptions import ListingGenerationError
from colorforge_agents.seo.listing_agent import SEOListingCore


def _brief(keyword: str = "ocean mandala coloring book") -> NicheBrief:
    return NicheBrief(
        niche_id="niche-001",
        category_path=["Books", "Art"],
        primary_keyword=keyword,
        profitability_score=72.5,
        pain_points=[
            PainPoint(
                text="pages too small", source_review_ids=[], severity=4, category="size"
            ),
        ],
        style_classifications=[
            StyleClassification(name="Mandala Flow", prevalence=65.0, examples=["B001"]),
        ],
        differentiators=[
            Differentiator(
                description="large print friendly",
                rationale="accessibility gap",
                estimated_impact="high",
            ),
        ],
        vision_analysis_summary="Mandala style dominates.",
        created_at=datetime.now(tz=UTC),
    )


def _draft(book_id: str = "book-001", total_pages: int = 75) -> BookDraft:
    return BookDraft(
        book_id=book_id,
        manuscript_pdf_path="/tmp/ms.pdf",
        cover_pdf_path="/tmp/cover.pdf",
        pages=[
            DraftPage(
                index=0,
                image_path="/tmp/p000.png",
                prompt_used="test",
                validation_status="pass",
            )
        ],
        spine_width_inches=0.169,
        total_pages=total_pages,
        generation_metadata=GenerationMetadata(
            generator_model_version="gemini-3.1-flash-image-generation",
            total_generation_time_ms=5000,
            total_cost_usd=0.0,
            pages_generated=total_pages,
            pages_regenerated=0,
        ),
    )


def _plan(keyword: str = "ocean mandala coloring book") -> BookPlan:
    return BookPlan(
        niche_brief_id="niche-001",
        account_id="acc-001",
        brand_author="Jane Doe",
        target_keyword=keyword,
        style_fingerprint="Mandala Flow",
        page_count=75,
        target_price=7.99,
        page_prompts=[
            PagePrompt(
                index=i,
                prompt=f"Page {i} prompt",
                theme="ocean",
                complexity_tier="medium",
            )
            for i in range(75)
        ],
        cover_brief=CoverBrief(
            subject="ocean mandala",
            style_fingerprint="Mandala Flow",
            palette_hint="black and white",
            background_hint="pure white",
        ),
    )


def _valid_claude_response() -> str:
    return json.dumps(
        {
            "title": "Ocean Mandala Coloring Book for Adults: 75 Relaxing Designs",
            "subtitle": "Stress Relief Coloring with Sea-Themed Patterns",
            "keywords": [
                "ocean coloring book adults",
                "mandala coloring stress relief",
                "sea themed adult coloring",
                "relaxation coloring pages",
                "intricate mandala designs",
                "ocean wave patterns coloring",
                "gift coloring book adults",
            ],
            "description_html": "<b>75 unique ocean designs.</b>",
            "bisac_codes": ["GAM019000", "ART015000"],
            "price_usd": 7.99,
        }
    )


class _MockClient:
    """Mock Anthropic client that returns a fixed response."""

    def __init__(self, response_text: str) -> None:
        self._text = response_text
        self.messages = _MockMessages(response_text)


class _MockMessages:
    def __init__(self, text: str) -> None:
        self._text = text

    async def create(self, **_: object) -> object:
        return _MockResponse(self._text)


class _MockResponse:
    def __init__(self, text: str) -> None:
        self.content = [_MockBlock(text)]


class _MockBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _MockPrisma:
    async def listing_create(self, **_: object) -> None:
        pass


def _core(response: str = "") -> SEOListingCore:
    client = _MockClient(response or _valid_claude_response())
    return SEOListingCore(client=client, prisma=_MockPrisma())


class TestGenerateWithClaude:
    async def test_returns_listing_contract(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert isinstance(result, ListingContract)

    async def test_title_from_claude(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert "Ocean Mandala" in result.title

    async def test_has_seven_keywords(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert len(result.keywords) == 7

    async def test_ai_disclosure_always_true(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert result.ai_disclosure is True

    async def test_price_eur_computed_from_usd(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert result.price_eur is not None
        assert result.price_eur == pytest.approx(7.99 * 0.93, abs=0.01)

    async def test_price_gbp_computed_from_usd(self) -> None:
        core = _core()
        result = await core.generate(_brief(), _draft(), _plan())
        assert result.price_gbp is not None
        assert result.price_gbp == pytest.approx(7.99 * 0.79, abs=0.01)

    async def test_markdown_fences_stripped(self) -> None:
        fenced = "```json\n" + _valid_claude_response() + "\n```"
        core = _core(fenced)
        result = await core.generate(_brief(), _draft(), _plan())
        assert isinstance(result, ListingContract)


class TestFallbackListing:
    async def test_fallback_on_api_error(self) -> None:
        class _ErrorMessages:
            async def create(self, **_: object) -> object:
                raise RuntimeError("API down")

        class _ErrorClient:
            messages = _ErrorMessages()

        core = SEOListingCore(client=_ErrorClient(), prisma=_MockPrisma())
        kw = "cat coloring book"
        result = await core.generate(_brief(kw), _draft(), _plan(kw))
        assert isinstance(result, ListingContract)

    async def test_fallback_has_seven_keywords(self) -> None:
        class _ErrorMessages:
            async def create(self, **_: object) -> object:
                raise RuntimeError("API down")

        class _ErrorClient:
            messages = _ErrorMessages()

        core = SEOListingCore(client=_ErrorClient(), prisma=_MockPrisma())
        result = await core.generate(_brief(), _draft(), _plan())
        assert len(result.keywords) == 7

    async def test_fallback_price_anchor(self) -> None:
        class _ErrorMessages:
            async def create(self, **_: object) -> object:
                raise RuntimeError("API down")

        class _ErrorClient:
            messages = _ErrorMessages()

        core = SEOListingCore(client=_ErrorClient(), prisma=_MockPrisma())
        result = await core.generate(_brief(), _draft(total_pages=50), _plan())
        # 50 pages ≤ 60 threshold → $6.99
        assert result.price_usd == pytest.approx(6.99)


class TestParseErrors:
    def test_invalid_json_raises_listing_error(self) -> None:
        core = _core()
        with pytest.raises(ListingGenerationError):
            core._parse_response("not json at all", "book-001", _plan())

    def test_parse_wrong_keyword_count(self) -> None:
        core = _core()
        bad = json.dumps({"title": "T", "keywords": ["only", "six", "kw", "here", "foo", "bar"],
                          "description_html": "", "bisac_codes": ["GAM019000"], "price_usd": 7.99})
        with pytest.raises(ListingGenerationError):
            core._parse_response(bad, "book-001", _plan())

    def test_parse_missing_title_raises(self) -> None:
        core = _core()
        bad = json.dumps({"keywords": ["a", "b", "c", "d", "e", "f", "g"],
                          "description_html": "", "bisac_codes": ["GAM019000"], "price_usd": 7.99})
        with pytest.raises(ListingGenerationError):
            core._parse_response(bad, "book-001", _plan())
