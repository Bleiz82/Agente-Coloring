"""Tests for StrategistCore."""

from __future__ import annotations

import pytest

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import StrategistError
from colorforge_agents.strategist.strategist import (
    AccountState,
    StrategistConfig,
    StrategistCore,
)


def _brief(
    keyword: str = "ocean mandala coloring book",
    niche_id: str = "niche-001",
) -> NicheBrief:
    from datetime import UTC, datetime

    from colorforge_agents.contracts.niche_brief import Differentiator, StyleClassification

    return NicheBrief(
        niche_id=niche_id,
        category_path=["Books", "Crafts & Hobbies", "Art"],
        primary_keyword=keyword,
        profitability_score=72.5,
        pain_points=[],
        style_classifications=[
            StyleClassification(
                name="Mandala Flow",
                prevalence=65.0,
                examples=["B001", "B002"],
            )
        ],
        differentiators=[
            Differentiator(
                description="unique ocean wave patterns",
                rationale="top pain point",
                estimated_impact="high",
            ),
            Differentiator(
                description="large print friendly design",
                rationale="accessibility gap",
                estimated_impact="medium",
            ),
        ],
        vision_analysis_summary="Ocean-themed mandala style dominates top sellers.",
        created_at=datetime.now(tz=UTC),
    )


def _accounts(n: int = 2) -> list[AccountState]:
    return [
        AccountState(
            account_id=f"acc-{i}",
            brand_author=f"Author {i}",
            publications_last_30d=i * 3,
            niche_specializations=["art"],
        )
        for i in range(n)
    ]


class _MockPrisma:
    async def book_plan_create(self, **_: object) -> None:
        pass


@pytest.fixture()
def core() -> StrategistCore:
    return StrategistCore(prisma=_MockPrisma())


class TestAccountSelection:
    async def test_selects_least_busy_account(self, core: StrategistCore) -> None:
        accounts = _accounts(3)
        plan = await core.plan(_brief(), accounts, StrategistConfig())
        # acc-0 has 0 pubs, should be selected
        assert plan.account_id == "acc-0"

    async def test_tiebreak_by_account_id(self, core: StrategistCore) -> None:
        accounts = [
            AccountState(account_id="z-acc", brand_author="Z", publications_last_30d=0),
            AccountState(account_id="a-acc", brand_author="A", publications_last_30d=0),
        ]
        plan = await core.plan(_brief(), accounts, StrategistConfig())
        assert plan.account_id == "a-acc"

    async def test_single_account_used(self, core: StrategistCore) -> None:
        accounts = [AccountState(account_id="only", brand_author="Solo", publications_last_30d=10)]
        plan = await core.plan(_brief(), accounts, StrategistConfig())
        assert plan.account_id == "only"

    async def test_raises_on_empty_accounts(self, core: StrategistCore) -> None:
        with pytest.raises(StrategistError):
            await core.plan(_brief(), [], StrategistConfig())


class TestPagePrompts:
    async def test_correct_page_count(self, core: StrategistCore) -> None:
        cfg = StrategistConfig(page_count=30)
        plan = await core.plan(_brief(), _accounts(), cfg)
        assert len(plan.page_prompts) == 30

    async def test_page_indices_sequential(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief(), _accounts(), StrategistConfig(page_count=20))
        indices = [p.index for p in plan.page_prompts]
        assert indices == list(range(20))

    async def test_complexity_progression(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief(), _accounts(), StrategistConfig(page_count=20))
        # First ~20% should be sparse
        assert plan.page_prompts[0].complexity_tier == "sparse"
        # Last ~20% should be dense
        assert plan.page_prompts[-1].complexity_tier == "dense"
        # Middle should be medium
        assert plan.page_prompts[10].complexity_tier == "medium"

    async def test_prompts_contain_keyword(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief("dragon coloring book"), _accounts(), StrategistConfig())
        for p in plan.page_prompts:
            assert "dragon coloring book" in p.prompt.lower() or "dragon" in p.prompt.lower()

    async def test_prompts_contain_no_color_instruction(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief(), _accounts(), StrategistConfig())
        for p in plan.page_prompts:
            assert "NO color" in p.prompt or "NO shading" in p.prompt


class TestStyleFingerprint:
    async def test_fingerprint_from_style_classification(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief(), _accounts(), StrategistConfig())
        assert "mandala" in plan.style_fingerprint.lower()

    async def test_fingerprint_fallback_without_styles(self, core: StrategistCore) -> None:
        from datetime import UTC, datetime

        brief = NicheBrief(
            niche_id="n1",
            category_path=["Books"],
            primary_keyword="cat coloring book",
            profitability_score=60.0,
            pain_points=[],
            style_classifications=[],
            differentiators=[],
            vision_analysis_summary="",
            created_at=datetime.now(tz=UTC),
        )
        plan = await core.plan(brief, _accounts(), StrategistConfig())
        assert "cat" in plan.style_fingerprint.lower()


class TestTrimSizeSelection:
    """Strategist auto-selects TrimSize based on niche keywords."""

    @pytest.mark.parametrize(
        ("keyword", "expected_trim"),
        [
            ("mandala coloring book", "8.5x8.5"),
            ("geometric patterns for adults", "8.5x8.5"),
            ("zen garden coloring", "8.5x8.5"),
            ("kids coloring book animals", "8x10"),
            ("children's coloring pages", "8x10"),
            ("toddler activity book", "8x10"),
            ("preschool coloring fun", "8x10"),
            ("workbook for adults", "7x10"),
            ("activity pages educational", "7x10"),
            ("educational coloring book", "7x10"),
            ("travel coloring book", "6x9"),
            ("pocket coloring mini art", "6x9"),
            ("mini coloring book", "6x9"),
            ("ocean coloring book adults", "8.5x11"),  # default
            ("floral patterns coloring", "8.5x11"),    # default
        ],
    )
    async def test_strategist_trim_size_selection(
        self,
        core: StrategistCore,
        keyword: str,
        expected_trim: str,
    ) -> None:
        plan = await core.plan(_brief(keyword), _accounts(), StrategistConfig())
        assert plan.trim_size.value == expected_trim, (
            f"keyword={keyword!r}: expected {expected_trim}, got {plan.trim_size.value}"
        )

    async def test_plan_has_paper_type_white(self, core: StrategistCore) -> None:
        from colorforge_agents.contracts.book_plan import PaperType

        plan = await core.plan(_brief(), _accounts(), StrategistConfig())
        assert plan.paper_type == PaperType.WHITE

    async def test_plan_has_default_cover_finish_matte(self, core: StrategistCore) -> None:
        from colorforge_agents.contracts.book_plan import CoverFinish

        plan = await core.plan(_brief(), _accounts(), StrategistConfig())
        assert plan.cover_finish == CoverFinish.MATTE


class TestPlanStructure:
    async def test_book_plan_has_cover_brief(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief(), _accounts(), StrategistConfig())
        assert plan.cover_brief.subject
        assert plan.cover_brief.style_fingerprint

    async def test_book_plan_keyword_matches_brief(self, core: StrategistCore) -> None:
        plan = await core.plan(_brief("cat patterns"), _accounts(), StrategistConfig())
        assert plan.target_keyword == "cat patterns"

    async def test_book_plan_price_from_config(self, core: StrategistCore) -> None:
        cfg = StrategistConfig(target_price=9.99)
        plan = await core.plan(_brief(), _accounts(), cfg)
        assert plan.target_price == pytest.approx(9.99)

    async def test_brand_author_matches_account(self, core: StrategistCore) -> None:
        accounts = [
            AccountState(account_id="acc-0", brand_author="Jane Doe", publications_last_30d=0)
        ]
        plan = await core.plan(_brief(), accounts, StrategistConfig())
        assert plan.brand_author == "Jane Doe"
