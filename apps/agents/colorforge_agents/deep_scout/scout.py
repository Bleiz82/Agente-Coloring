"""Deep Scout orchestration — enriches NicheCandidate into NicheBrief."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.contracts.niche_candidate import NicheCandidate
from colorforge_agents.deep_scout.embedder import NicheEmbedder
from colorforge_agents.deep_scout.llm_analyzer import LLMAnalyzer
from colorforge_agents.deep_scout.review_scraper import scrape_low_rated_reviews


class DeepScoutCore:
    """Orchestrates review scraping, LLM analysis, and Qdrant embedding."""

    def __init__(
        self,
        llm_analyzer: LLMAnalyzer,
        embedder: NicheEmbedder,
        prisma: Any,
        playwright_browser: Any | None = None,
    ) -> None:
        self._llm = llm_analyzer
        self._embedder = embedder
        self._prisma = prisma
        self._browser = playwright_browser

    async def enrich(self, candidate: NicheCandidate) -> NicheBrief:
        """Enrich a NicheCandidate with pain points, styles, differentiators."""
        niche_id = str(uuid.uuid4())
        logger.info("Deep Scout enriching niche: {}", candidate.primary_keyword)

        # 1. Scrape low-rated reviews for top competitors
        reviews: list[dict[str, Any]] = []
        if self._browser is not None:
            page = await self._browser.new_page()
            try:
                for competitor in candidate.top_competitors[:5]:
                    batch = await scrape_low_rated_reviews(competitor.asin, page, max_reviews=20)
                    reviews.extend(batch)
            finally:
                await page.close()

        # 2. LLM analysis
        pain_points = await self._llm.extract_pain_points(reviews)

        cover_urls = [
            f"https://images-na.ssl-images-amazon.com/images/I/{c.asin}.jpg"
            for c in candidate.top_competitors[:10]
        ]
        styles = await self._llm.classify_cover_styles(cover_urls)
        differentiators = await self._llm.suggest_differentiators(pain_points, styles)
        summary = await self._llm.summarize_vision_analysis(pain_points, styles)

        # 3. Build brief
        brief = NicheBrief(
            niche_id=niche_id,
            category_path=candidate.category_path,
            primary_keyword=candidate.primary_keyword,
            profitability_score=candidate.profitability.weighted_total,
            pain_points=pain_points,
            style_classifications=styles,
            differentiators=differentiators,
            vision_analysis_summary=summary,
            created_at=datetime.now(tz=UTC),
        )

        # 4. Embed and store
        try:
            await self._embedder.ensure_collection()
            vector_id = await self._embedder.embed_and_store(brief)
            brief = brief.model_copy(update={"qdrant_vector_id": vector_id})
        except Exception as exc:
            logger.warning("Qdrant embedding failed, continuing without: {}", exc)

        # 5. Persist to DB
        await self._write_to_db(brief)

        return brief

    async def _write_to_db(self, brief: NicheBrief) -> None:
        try:
            await self._prisma.niche_brief_create(
                data={
                    "id": brief.niche_id,
                    "primaryKeyword": brief.primary_keyword,
                    "categoryPath": brief.category_path,
                    "profitabilityScore": brief.profitability_score,
                    "painPoints": [p.model_dump() for p in brief.pain_points],
                    "styleClassifications": [s.model_dump() for s in brief.style_classifications],
                    "differentiators": [d.model_dump() for d in brief.differentiators],
                    "visionSummary": brief.vision_analysis_summary,
                    "qdrantVectorId": brief.qdrant_vector_id,
                    "createdAt": brief.created_at.isoformat(),
                }
            )
        except Exception as exc:
            logger.error("DB write failed for NicheBrief {}: {}", brief.niche_id, exc)


class DeepScoutAgent:
    """Thin CrewAI wrapper around DeepScoutCore."""

    def __init__(self, core: DeepScoutCore) -> None:
        self._core = core

    def as_crewai_agent(self) -> Any:
        try:
            from crewai import Agent
        except ImportError as exc:
            raise ImportError("crewai is required for DeepScoutAgent.as_crewai_agent()") from exc
        return Agent(
            role="Deep Scout",
            goal=(
                "Enrich each NicheCandidate with competitor review pain points, visual style "
                "classification, and strategic differentiators. Output NicheBrief records."
            ),
            backstory=(
                "Expert in qualitative competitor analysis, buyer psychology, and visual "
                "trend identification in the Amazon KDP coloring book market."
            ),
            allow_delegation=False,
            verbose=True,
        )
