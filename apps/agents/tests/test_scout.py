"""Tests for deep_scout/scout.py and llm_analyzer.py."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from colorforge_agents.contracts.niche_brief import (
    Differentiator,
    NicheBrief,
    PainPoint,
    StyleClassification,
)
from colorforge_agents.contracts.niche_candidate import (
    CompetitorSnap,
    NicheCandidate,
    ProfitabilityBreakdown,
    TrendSignal,
)
from colorforge_agents.deep_scout.llm_analyzer import LLMAnalyzer
from colorforge_agents.deep_scout.scout import DeepScoutCore
from colorforge_agents.exceptions import LLMAnalysisError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_candidate() -> NicheCandidate:
    return NicheCandidate(
        category_path=["Books", "Coloring Books"],
        primary_keyword="mandala coloring",
        top_competitors=[
            CompetitorSnap(
                asin="B0TEST0001",
                title="Test Mandala Book",
                author="Artist",
                bsr=5_000,
                price=9.99,
                review_count=15,
                rating=3.2,
            )
        ],
        profitability=ProfitabilityBreakdown(
            demand=0.8,
            price=1.0,
            competition=0.7,
            quality_gap=0.5,
            trend=0.6,
            seasonality=1.0,
            catalog_fit=0.5,
            saturation=0.1,
            weighted_total=72.0,
        ),
        trend_signals=TrendSignal(google_trends_90d_slope=0.4),
        scan_timestamp=datetime.now(tz=UTC),
    )


def _pain_point_json() -> str:
    return json.dumps([
        {
            "text": "Lines bleed through paper",
            "source_review_ids": ["r1", "r2"],
            "severity": 4,
            "category": "line_quality",
        }
    ])


def _style_json() -> str:
    return json.dumps([
        {
            "name": "geometric-mandala",
            "prevalence": 70.0,
            "examples": ["B0TEST0001"],
        }
    ])


def _diff_json() -> str:
    return json.dumps([
        {
            "description": "Use bold 3px lines",
            "rationale": "Solves top pain point",
            "estimated_impact": "high",
        }
    ])


# ---------------------------------------------------------------------------
# LLMAnalyzer tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_pain_points_returns_list() -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text=_pain_point_json())])
    )
    analyzer = LLMAnalyzer(mock_client)
    reviews = [{"text": "Lines bleed", "rating": 1.0, "review_id": "r1"}]
    result = await analyzer.extract_pain_points(reviews)
    assert len(result) == 1
    assert isinstance(result[0], PainPoint)
    assert result[0].severity == 4


@pytest.mark.asyncio
async def test_extract_pain_points_empty_reviews() -> None:
    mock_client = MagicMock()
    analyzer = LLMAnalyzer(mock_client)
    result = await analyzer.extract_pain_points([])
    assert result == []
    mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_extract_pain_points_raises_on_bad_json() -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text="not valid json")])
    )
    analyzer = LLMAnalyzer(mock_client)
    reviews = [{"text": "bad", "rating": 1.0, "review_id": "r1"}]
    with pytest.raises(LLMAnalysisError):
        await analyzer.extract_pain_points(reviews)


@pytest.mark.asyncio
async def test_suggest_differentiators_returns_list() -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text=_diff_json())])
    )
    analyzer = LLMAnalyzer(mock_client)
    pain_points = [PainPoint(text="p", source_review_ids=["r1"], severity=3, category="other")]
    styles = [StyleClassification(name="geo", prevalence=60.0, examples=["B01"])]
    result = await analyzer.suggest_differentiators(pain_points, styles)
    assert len(result) == 1
    assert isinstance(result[0], Differentiator)
    assert result[0].estimated_impact == "high"


@pytest.mark.asyncio
async def test_classify_cover_styles_empty_urls() -> None:
    mock_client = MagicMock()
    analyzer = LLMAnalyzer(mock_client)
    result = await analyzer.classify_cover_styles([])
    assert result == []


# ---------------------------------------------------------------------------
# DeepScoutCore tests
# ---------------------------------------------------------------------------


class _MockEmbedder:
    async def ensure_collection(self) -> None:
        pass

    async def embed_and_store(self, _brief: NicheBrief) -> str:
        return "vec-test-001"


class _MockPrisma:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def niche_brief_create(self, *, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(data)
        return data


def _make_analyzer_mock() -> MagicMock:
    mock = MagicMock()
    mock.extract_pain_points = AsyncMock(return_value=[
        PainPoint(text="thin lines", source_review_ids=["r1"], severity=4, category="line_quality")
    ])
    mock.classify_cover_styles = AsyncMock(return_value=[
        StyleClassification(name="geometric", prevalence=70.0, examples=["B0T"])
    ])
    mock.suggest_differentiators = AsyncMock(return_value=[
        Differentiator(description="bold lines", rationale="top pain", estimated_impact="high")
    ])
    mock.summarize_vision_analysis = AsyncMock(return_value="Geometric dominant.")
    return mock


@pytest.mark.asyncio
async def test_scout_enrich_returns_niche_brief() -> None:
    prisma = _MockPrisma()
    core = DeepScoutCore(
        llm_analyzer=_make_analyzer_mock(),
        embedder=_MockEmbedder(),  # type: ignore[arg-type]
        prisma=prisma,
        playwright_browser=None,
    )
    candidate = _make_candidate()
    brief = await core.enrich(candidate)
    assert isinstance(brief, NicheBrief)
    assert brief.primary_keyword == "mandala coloring"


@pytest.mark.asyncio
async def test_scout_enrich_writes_to_db() -> None:
    prisma = _MockPrisma()
    core = DeepScoutCore(
        llm_analyzer=_make_analyzer_mock(),
        embedder=_MockEmbedder(),  # type: ignore[arg-type]
        prisma=prisma,
        playwright_browser=None,
    )
    await core.enrich(_make_candidate())
    assert len(prisma.created) == 1
    assert "primaryKeyword" in prisma.created[0]


@pytest.mark.asyncio
async def test_scout_enrich_stores_vector_id() -> None:
    prisma = _MockPrisma()
    core = DeepScoutCore(
        llm_analyzer=_make_analyzer_mock(),
        embedder=_MockEmbedder(),  # type: ignore[arg-type]
        prisma=prisma,
        playwright_browser=None,
    )
    brief = await core.enrich(_make_candidate())
    assert brief.qdrant_vector_id == "vec-test-001"


@pytest.mark.asyncio
async def test_scout_enrich_has_at_least_one_pain_point() -> None:
    prisma = _MockPrisma()
    core = DeepScoutCore(
        llm_analyzer=_make_analyzer_mock(),
        embedder=_MockEmbedder(),  # type: ignore[arg-type]
        prisma=prisma,
        playwright_browser=None,
    )
    brief = await core.enrich(_make_candidate())
    assert len(brief.pain_points) >= 1


@pytest.mark.asyncio
async def test_scout_continues_when_qdrant_fails() -> None:
    class _FailingEmbedder:
        async def ensure_collection(self) -> None:
            raise RuntimeError("Qdrant down")

        async def embed_and_store(self, _brief: NicheBrief) -> str:
            raise RuntimeError("Qdrant down")

    prisma = _MockPrisma()
    core = DeepScoutCore(
        llm_analyzer=_make_analyzer_mock(),
        embedder=_FailingEmbedder(),  # type: ignore[arg-type]
        prisma=prisma,
        playwright_browser=None,
    )
    brief = await core.enrich(_make_candidate())
    # Brief still returned, just without vector ID
    assert brief.qdrant_vector_id is None
