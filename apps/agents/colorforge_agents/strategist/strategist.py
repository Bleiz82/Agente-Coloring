"""Strategist agent — transforms NicheBrief into a BookPlan."""

from __future__ import annotations

from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

from colorforge_agents.contracts.book_plan import (
    BookPlan,
    CoverBrief,
    PagePrompt,
    PaperType,
    TrimSize,
)
from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import StrategistError


class AccountState(BaseModel):
    """Snapshot of a KDP account relevant for Strategist decisions."""

    account_id: str
    brand_author: str
    publications_last_30d: int = Field(ge=0)
    niche_specializations: list[str] = Field(default_factory=list)


class StrategistConfig(BaseModel):
    """Configuration for a Strategist planning run."""

    page_count: int = Field(default=75, ge=20, le=200)
    target_price: float = Field(default=7.99, gt=0)
    max_weekly_pubs_per_format: int = Field(default=10, ge=1)


_COMPLEXITY: dict[str, Literal["sparse", "medium", "dense"]] = {
    "sparse": "sparse",
    "medium": "medium",
    "dense": "dense",
}

_PAGE_PROMPT_TEMPLATE = (
    "Black and white coloring book line art for adults. "
    "Subject: {theme}. "
    "Style: clean bold outlines, uniform line weight, NO shading, NO gradients, NO color. "
    "Background: pure white. "
    "Composition: centered, fills 80% of frame. "
    "Detail level: {tier}."
)


class StrategistCore:
    """Pure business logic — no CrewAI. Injected prisma for policy lookup."""

    def __init__(self, prisma: Any) -> None:
        self._prisma = prisma

    async def plan(
        self,
        brief: NicheBrief,
        accounts: list[AccountState],
        config: StrategistConfig,
    ) -> BookPlan:
        """Produce a BookPlan from a NicheBrief and available accounts."""
        if not accounts:
            raise StrategistError("No accounts available for planning")

        account = self._select_account(accounts, config)
        style_fp = self._derive_style_fingerprint(brief)
        page_prompts = self._build_page_prompts(brief, config.page_count, style_fp)
        cover = self._cover_brief_from_niche(brief, style_fp)

        plan = BookPlan(
            niche_brief_id=brief.niche_id,
            account_id=account.account_id,
            style_fingerprint=style_fp,
            page_count=config.page_count,
            page_prompts=page_prompts,
            cover_brief=cover,
            target_keyword=brief.primary_keyword,
            target_price=config.target_price,
            brand_author=account.brand_author,
            trim_size=self._choose_trim_size(brief),
            paper_type=self._choose_paper_type(brief),
        )
        logger.info(
            "Strategist planned book: keyword='{}' account='{}' pages={}",
            brief.primary_keyword,
            account.account_id,
            config.page_count,
        )
        return plan

    def _select_account(
        self, accounts: list[AccountState], config: StrategistConfig
    ) -> AccountState:
        """Return account with fewest recent publications; tiebreak by account_id."""
        # ~4.3 weeks/month × weekly limit gives rough 30-day ceiling
        monthly_ceiling = config.max_weekly_pubs_per_format * 4
        eligible = [
            a for a in accounts if a.publications_last_30d < monthly_ceiling
        ]
        if not eligible:
            eligible = accounts
        return min(eligible, key=lambda a: (a.publications_last_30d, a.account_id))

    def _derive_style_fingerprint(self, brief: NicheBrief) -> str:
        """Derive a style fingerprint from the dominant style classification."""
        if brief.style_classifications:
            top = brief.style_classifications[0]
            slug = top.name.lower().replace(" ", "-")
            return f"{slug}-{brief.primary_keyword.split()[0].lower()}"
        keyword_slug = brief.primary_keyword.lower().replace(" ", "-")
        return f"standard-{keyword_slug}"

    def _build_page_prompts(
        self, brief: NicheBrief, page_count: int, style_fp: str
    ) -> list[PagePrompt]:
        """Generate page prompts with complexity progression."""
        keyword = brief.primary_keyword
        themes = self._derive_themes(brief, page_count)

        sparse_end = max(1, int(page_count * 0.20))
        dense_start = page_count - max(1, int(page_count * 0.20))

        prompts: list[PagePrompt] = []
        for i in range(page_count):
            if i < sparse_end:
                tier: Literal["sparse", "medium", "dense"] = "sparse"
            elif i >= dense_start:
                tier = "dense"
            else:
                tier = "medium"

            theme = themes[i % len(themes)]
            full_theme = f"{keyword} — {theme}"
            prompt = _PAGE_PROMPT_TEMPLATE.format(theme=full_theme, tier=tier)

            prompts.append(
                PagePrompt(
                    index=i,
                    prompt=prompt,
                    complexity_tier=tier,
                    theme=theme,
                )
            )
        return prompts

    def _derive_themes(self, brief: NicheBrief, page_count: int) -> list[str]:
        """Derive a list of thematic variations from the niche brief."""
        base_themes: list[str] = []

        if brief.differentiators:
            for d in brief.differentiators[:5]:
                base_themes.append(d.description)

        if brief.style_classifications:
            for s in brief.style_classifications[:3]:
                base_themes.append(f"{s.name} composition")

        if not base_themes:
            base_themes = [
                "intricate pattern",
                "flowing design",
                "geometric arrangement",
                "nature-inspired motif",
                "abstract composition",
            ]

        # Ensure at least 10 unique themes via cycling with variation suffixes
        suffixes = [
            "", " with fine details", " centered composition", " with border elements",
            " full-page spread", " with symmetry", " minimal style", " ornate variant",
        ]
        expanded: list[str] = []
        for suffix in suffixes:
            for theme in base_themes:
                expanded.append(f"{theme}{suffix}".strip())
                if len(expanded) >= page_count:
                    break
            if len(expanded) >= page_count:
                break

        return expanded[:page_count] if expanded else base_themes

    def _choose_trim_size(self, brief: NicheBrief) -> TrimSize:
        """Select the most appropriate KDP trim size based on niche keywords.

        Uses substring matching so "children's" matches "children" etc.
        Priority order: SQUARE_LARGE > KIDS > INTERMEDIATE > POCKET > LETTER (default).

        Args:
            brief: NicheBrief with primary_keyword.

        Returns:
            TrimSize enum value (defaults to LETTER = 8.5×11").
        """
        keyword = brief.primary_keyword.lower()
        _SQUARE_KEYWORDS = ("mandala", "geometric", "zen")
        _KIDS_KEYWORDS = ("kids", "children", "toddler", "preschool")
        _INTERMEDIATE_KEYWORDS = ("workbook", "activity", "educational")
        _POCKET_KEYWORDS = ("travel", "pocket", "mini")

        if any(kw in keyword for kw in _SQUARE_KEYWORDS):
            return TrimSize.SQUARE_LARGE
        if any(kw in keyword for kw in _KIDS_KEYWORDS):
            return TrimSize.KIDS
        if any(kw in keyword for kw in _INTERMEDIATE_KEYWORDS):
            return TrimSize.INTERMEDIATE
        if any(kw in keyword for kw in _POCKET_KEYWORDS):
            return TrimSize.POCKET
        return TrimSize.LETTER

    def _choose_paper_type(self, brief: NicheBrief) -> PaperType:
        """Return paper type for the niche. Always WHITE for B/W coloring books.

        Args:
            brief: NicheBrief (reserved for future color-book logic).

        Returns:
            PaperType.WHITE.
        """
        return PaperType.WHITE

    def _cover_brief_from_niche(self, brief: NicheBrief, style_fp: str) -> CoverBrief:
        """Build a cover brief from the niche brief."""
        subject = (
            f"Stunning {brief.primary_keyword} illustration "
            "with intricate details, suitable for a coloring book cover"
        )
        palette = "#1A0033, #003366, #FFD700"
        # StyleClassification has no palette_hint field; use default palette

        return CoverBrief(
            subject=subject,
            style_fingerprint=style_fp,
            palette_hint=palette,
            background_hint="Clean white background with subtle decorative border",
        )
