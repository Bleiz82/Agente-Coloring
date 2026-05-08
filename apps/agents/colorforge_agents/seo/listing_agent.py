"""SEO Listing agent — NicheBrief + BookDraft → ListingContract via Claude Sonnet 4.6."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.config.models import LISTING_AGENT_MODEL
from colorforge_agents.exceptions import ListingGenerationError

_SYSTEM = (
    "You are a KDP coloring book SEO specialist with deep knowledge of Amazon search "
    "algorithms and buyer psychology. Generate listing metadata that maximizes discoverability "
    "and conversion for adult coloring books. "
    "Respond ONLY with a JSON object with keys: "
    '"title" (string, ≤200 chars, include page count and primary keyword), '
    '"subtitle" (string, ≤200 chars, emphasize emotional benefit and style), '
    '"keywords" (array of exactly 7 strings, each ≤50 chars, long-tail Amazon search phrases), '
    '"description_html" (string, ≤4000 chars, valid HTML using only <b><i><br><ul><li> tags), '
    '"bisac_codes" (array of 1-3 strings, format like ART015000), '
    '"price_usd" (float, $2.99-$24.99 appropriate for page count and niche).'
)

# KDP BISAC codes for coloring books (most common ones)
_BISAC_COLORING = "GAM019000"   # GAMES & ACTIVITIES / Coloring Books
_BISAC_ART = "ART015000"        # ART / Techniques / Drawing
_BISAC_CRAFTS = "CRA019000"     # CRAFTS & HOBBIES / General

# Price anchors by page count
_PRICE_ANCHORS = [
    (40, 5.99),
    (60, 6.99),
    (80, 7.99),
    (100, 8.99),
    (150, 9.99),
]


class SEOListingCore:
    """Generates a KDP listing from NicheBrief + BookDraft using Claude Sonnet 4.6."""

    def __init__(self, client: Any, prisma: Any) -> None:
        self._client = client
        self._prisma = prisma

    async def generate(
        self, brief: NicheBrief, draft: BookDraft, plan: BookPlan
    ) -> ListingContract:
        """Generate a ListingContract for the book. Falls back to template on Claude failure."""
        prompt = self._build_prompt(brief, draft, plan)
        try:
            raw = await self._call_claude(prompt)
            listing = self._parse_response(raw, draft.book_id, plan)
            logger.info(
                "SEO listing generated via Claude for book_id={} title={!r}",
                draft.book_id,
                listing.title,
            )
        except ListingGenerationError:
            logger.warning(
                "Claude listing failed for book_id={}, using fallback template",
                draft.book_id,
            )
            listing = self._fallback_listing(_brief=brief, draft=draft, plan=plan)

        return listing

    async def _call_claude(self, prompt: str) -> str:
        try:
            response = await self._client.messages.create(
                model=LISTING_AGENT_MODEL,
                max_tokens=1024,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise ListingGenerationError(f"Claude API error: {exc}") from exc

        return response.content[0].text.strip()  # type: ignore[no-any-return]

    def _build_prompt(self, brief: NicheBrief, draft: BookDraft, plan: BookPlan) -> str:
        pain_points = "; ".join(p.text for p in brief.pain_points[:3]) or "none identified"
        differentiators = "; ".join(
            d.description for d in brief.differentiators[:2]
        ) or "standard quality"
        styles = ", ".join(s.name for s in brief.style_classifications[:2]) or "line art"

        return (
            f"Target keyword: {plan.target_keyword}\n"
            f"Page count: {draft.total_pages}\n"
            f"Style: {plan.style_fingerprint} ({styles})\n"
            f"Top buyer pain points: {pain_points}\n"
            f"Our differentiators: {differentiators}\n"
            f"Price target: ${plan.target_price:.2f}\n"
            f"Generate listing metadata as JSON."
        )

    def _parse_response(self, raw: str, book_id: str, plan: BookPlan) -> ListingContract:
        # Strip markdown code fences if present
        text = raw
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )

        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ListingGenerationError(
                f"Claude listing JSON parse error: {exc} | raw={raw!r}"
            ) from exc

        try:
            keywords = list(obj.get("keywords", []))
            if len(keywords) != 7:
                raise ListingGenerationError(
                    f"Expected 7 keywords, got {len(keywords)}"
                )
            bisac = list(obj.get("bisac_codes", [_BISAC_COLORING]))
            if not bisac:
                bisac = [_BISAC_COLORING]

            price_usd = float(obj.get("price_usd", plan.target_price))
            price_eur = round(price_usd * 0.93, 2)
            price_gbp = round(price_usd * 0.79, 2)

            return ListingContract(
                book_id=book_id,
                title=str(obj["title"])[:200],
                subtitle=str(obj.get("subtitle", ""))[:200] or None,
                keywords=keywords,
                description_html=str(obj.get("description_html", ""))[:4000],
                bisac_codes=bisac[:3],
                price_usd=price_usd,
                price_eur=price_eur,
                price_gbp=price_gbp,
                ai_disclosure=True,
                publication_target_date=datetime.now(tz=UTC),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ListingGenerationError(
                f"Claude listing field error: {exc} | obj={obj!r}"
            ) from exc

    def _fallback_listing(
        self, _brief: NicheBrief, draft: BookDraft, plan: BookPlan
    ) -> ListingContract:
        """Template-based fallback when Claude is unavailable."""
        keyword = plan.target_keyword.title()
        title = f"{keyword}: {draft.total_pages} Relaxing Designs for Adults"[:200]
        subtitle = (
            f"Stress Relief Coloring with {plan.style_fingerprint} — Perfect Gift for Relaxation"
        )[:200]

        # Generate 7 generic long-tail keywords from target keyword
        base = plan.target_keyword.lower()
        keywords = [
            f"{base} adults",
            f"{base} stress relief",
            f"adult {base}",
            f"{base} relaxation",
            f"{base} gift women",
            f"{base} beginners",
            f"{base} patterns",
        ]

        description = (
            f"<b>Discover {draft.total_pages} Unique {keyword} Designs</b>"
            f"<br><br>This coloring book features {plan.style_fingerprint} artwork "
            f"created for adult colorists who appreciate quality and detail."
            f"<br><br><b>Inside you'll find:</b>"
            f"<ul><li>{draft.total_pages} original designs across difficulty levels</li>"
            f"<li>Single-sided pages to prevent bleed-through</li>"
            f"<li>Professional quality line art at 300 DPI</li></ul>"
        )

        price_usd = self._anchor_price(draft.total_pages, plan.target_price)
        return ListingContract(
            book_id=draft.book_id,
            title=title,
            subtitle=subtitle,
            keywords=keywords,
            description_html=description[:4000],
            bisac_codes=[_BISAC_COLORING, _BISAC_ART],
            price_usd=price_usd,
            price_eur=round(price_usd * 0.93, 2),
            price_gbp=round(price_usd * 0.79, 2),
            ai_disclosure=True,
            publication_target_date=datetime.now(tz=UTC),
        )

    @staticmethod
    def _anchor_price(page_count: int, target_price: float) -> float:
        for threshold, price in _PRICE_ANCHORS:
            if page_count <= threshold:
                return price
        return max(target_price, _PRICE_ANCHORS[-1][1])
