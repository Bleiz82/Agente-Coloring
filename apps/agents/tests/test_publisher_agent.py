"""Tests for PublisherAgent — orchestration logic (no real browser)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from colorforge_agents.contracts.book_draft import BookDraft, DraftPage, GenerationMetadata
from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.contracts.validation_report import (
    CoverAssessment,
    ValidationReport,
)
from colorforge_agents.exceptions import (
    ContentGateBlocked,
    ListingGateBlocked,
)
from colorforge_agents.gates.content_gate import ContentGate
from colorforge_agents.gates.listing_gate import ListingGate
from colorforge_agents.publisher.publisher_agent import PublisherAgent, PublisherResult

_NOW = datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class _MockPrisma:
    def __init__(self) -> None:
        self.book = _MockBookTable()
        self.bookevent = _MockEventTable()


class _MockBookTable:
    async def update(self, **_: object) -> None:
        pass

    async def find_many(self, **_: object) -> list[object]:
        return []


class _MockEventTable:
    async def create(self, **_: object) -> None:
        pass


class _MockAccount:
    id = "acc-001"
    label = "Jane Doe"
    daily_quota = 5
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    storage_state_encrypted_path = Path("/fake/state.age")

    @property
    def account_age_days(self) -> int:
        return 10


def _valid_listing(book_id: str = "book-001") -> ListingContract:
    return ListingContract(
        book_id=book_id,
        title="Ocean Mandala Coloring Book for Adults: 75 Designs",
        subtitle="Stress Relief",
        keywords=[
            "ocean coloring adults",
            "mandala coloring relief",
            "sea adult coloring",
            "relaxation pages",
            "intricate mandala",
            "ocean wave coloring",
            "gift coloring adults",
        ],
        description_html="<b>Beautiful designs.</b>",
        bisac_codes=["GAM019000"],
        price_usd=7.99,
        price_eur=7.43,
        price_gbp=6.31,
        ai_disclosure=True,
        publication_target_date=_NOW,
    )


def _valid_draft(book_id: str = "book-001") -> BookDraft:
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
        total_pages=75,
        generation_metadata=GenerationMetadata(
            generator_model_version="gemini-3.1-flash-image-generation",
            total_generation_time_ms=5000,
            total_cost_usd=0.0,
            pages_generated=75,
            pages_regenerated=0,
        ),
    )


def _passing_report() -> ValidationReport:
    return ValidationReport(
        book_id="book-001",
        verdict="pass",
        per_page_flags=[],
        cover_assessment=CoverAssessment(readability_score=80, issues=[]),
        pdf_spec_compliance=True,
        pdf_spec_details=[],
        recommended_action="publish",
        critic_model_version="claude-sonnet-4-6",
    )


def _failing_report() -> ValidationReport:
    from colorforge_agents.contracts.validation_report import PageFlag

    return ValidationReport(
        book_id="book-001",
        verdict="fail",
        per_page_flags=[[
            PageFlag(page_index=0, type="artifact_detected", severity=5, detail="solid block")
        ]],
        cover_assessment=CoverAssessment(readability_score=80, issues=[]),
        pdf_spec_compliance=True,
        pdf_spec_details=[],
        recommended_action="kill",
        critic_model_version="claude-sonnet-4-6",
    )


def _make_agent(
    content_gate: ContentGate | None = None,
    listing_gate: ListingGate | None = None,
    prisma: _MockPrisma | None = None,
) -> PublisherAgent:
    return PublisherAgent(
        content_gate=content_gate or ContentGate(),
        listing_gate=listing_gate or ListingGate(),
        prisma=prisma or _MockPrisma(),
        assets_base=Path("/tmp/colorforge"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthorSplit:
    def test_splits_first_last(self) -> None:
        first, last = PublisherAgent._split_author("Jane Doe")
        assert first == "Jane"
        assert last == "Doe"

    def test_single_name_empty_first(self) -> None:
        first, last = PublisherAgent._split_author("Mononym")
        assert first == ""
        assert last == "Mononym"

    def test_multi_part_last_name(self) -> None:
        first, last = PublisherAgent._split_author("Mary Ann Smith")
        assert first == "Mary"
        assert last == "Ann Smith"


class TestListingMapping:
    def test_map_listing_splits_author(self) -> None:
        agent = _make_agent()
        listing = _valid_listing()

        account = _MockAccount()
        mapped = agent._map_listing(listing, account)
        assert mapped.author_first == "Jane"
        assert mapped.author_last == "Doe"

    def test_map_listing_price_eur_fallback(self) -> None:
        agent = _make_agent()
        listing = _valid_listing()
        listing_no_eur = listing.model_copy(update={"price_eur": None})

        mapped = agent._map_listing(listing_no_eur, _MockAccount())
        assert abs(mapped.price_eur - 7.99 * 0.93) < 0.01

    def test_map_listing_price_gbp_fallback(self) -> None:
        agent = _make_agent()
        listing = _valid_listing()
        listing_no_gbp = listing.model_copy(update={"price_gbp": None})

        mapped = agent._map_listing(listing_no_gbp, _MockAccount())
        assert abs(mapped.price_gbp - 7.99 * 0.79) < 0.01

    def test_map_draft_paths(self) -> None:
        agent = _make_agent()
        draft = _valid_draft()
        mapped = agent._map_draft(draft)
        assert mapped.interior_pdf == Path("/tmp/ms.pdf")
        assert mapped.cover_pdf == Path("/tmp/cover.pdf")


class TestGateChecks:
    async def test_content_gate_blocks_before_publish(self) -> None:
        agent = _make_agent()
        with pytest.raises(ContentGateBlocked):
            await agent.publish(
                _valid_listing(),
                _valid_draft(),
                _MockAccount(),
                _failing_report(),
            )

    async def test_listing_gate_blocks_trademark(self) -> None:
        agent = _make_agent()
        listing = _valid_listing()
        bad_listing = listing.model_copy(update={"title": "Disney Coloring Book"})
        with pytest.raises(ListingGateBlocked):
            await agent.publish(
                bad_listing,
                _valid_draft(),
                _MockAccount(),
                _passing_report(),
            )

    async def test_quota_exceeded_blocks_publish(self) -> None:
        from colorforge_kdp.exceptions import QuotaExceeded

        class _FullQuotaBook:
            async def update(self, **_: object) -> None:
                pass

            async def find_many(self, **_: object) -> list[object]:
                # Return 5 books today → quota exceeded for ramp account
                return [object()] * 5

        class _FullPrisma(_MockPrisma):
            def __init__(self) -> None:
                super().__init__()
                self.book = _FullQuotaBook()

        agent = _make_agent(prisma=_FullPrisma())
        with pytest.raises(QuotaExceeded):
            await agent.publish(
                _valid_listing(),
                _valid_draft(),
                _MockAccount(),
                _passing_report(),
            )


class TestPublisherResult:
    def test_result_dataclass(self) -> None:
        r = PublisherResult(book_id="b1", asin="B001234567", account_id="acc-1")
        assert r.book_id == "b1"
        assert r.asin == "B001234567"
        assert r.account_id == "acc-1"

    def test_result_frozen(self) -> None:
        r = PublisherResult(book_id="b1", asin="B001234567", account_id="acc-1")
        with pytest.raises((AttributeError, TypeError)):
            r.asin = "other"  # type: ignore[misc]
