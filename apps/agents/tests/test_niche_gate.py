"""Tests for gates/niche_gate.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import NicheGateBlocked
from colorforge_agents.gates.niche_gate import NicheGate


def _make_brief(score: float, niche_id: str = "test-niche-001") -> NicheBrief:
    return NicheBrief(
        niche_id=niche_id,
        category_path=["Books", "Coloring"],
        primary_keyword="test niche",
        profitability_score=score,
        pain_points=[],
        style_classifications=[],
        differentiators=[],
        vision_analysis_summary="test",
        created_at=datetime.now(tz=UTC),
    )


class _MockPrisma:
    def __init__(self, records: list[dict[str, float]]) -> None:
        self._records = records

    async def niche_brief_find_many(self, **_: object) -> list[dict[str, float]]:
        return self._records


# ---------------------------------------------------------------------------
# compute_threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_threshold_uses_median_of_winner_scores() -> None:
    prisma = _MockPrisma([
        {"profitabilityScore": 60.0},
        {"profitabilityScore": 70.0},
        {"profitabilityScore": 80.0},
        {"profitabilityScore": 50.0},
        {"profitabilityScore": 65.0},
    ])
    gate = NicheGate()
    threshold = await gate.compute_threshold(prisma)
    assert threshold == 65.0  # median of [50, 60, 65, 70, 80]


@pytest.mark.asyncio
async def test_threshold_fallback_when_too_few_data_points() -> None:
    prisma = _MockPrisma([
        {"profitabilityScore": 80.0},
        {"profitabilityScore": 90.0},
    ])
    gate = NicheGate()
    threshold = await gate.compute_threshold(prisma)
    assert threshold == NicheGate.FALLBACK_THRESHOLD


@pytest.mark.asyncio
async def test_threshold_fallback_when_no_data() -> None:
    prisma = _MockPrisma([])
    gate = NicheGate()
    threshold = await gate.compute_threshold(prisma)
    assert threshold == NicheGate.FALLBACK_THRESHOLD


@pytest.mark.asyncio
async def test_threshold_fallback_on_db_error() -> None:
    class _BrokenPrisma:
        async def niche_brief_find_many(self, **_: object) -> list[object]:
            raise RuntimeError("DB connection failed")

    gate = NicheGate()
    threshold = await gate.compute_threshold(_BrokenPrisma())
    assert threshold == NicheGate.FALLBACK_THRESHOLD


# ---------------------------------------------------------------------------
# passes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_passes_when_score_above_threshold() -> None:
    prisma = _MockPrisma([])  # triggers fallback threshold = 50.0
    gate = NicheGate()
    brief = _make_brief(score=75.0)
    passed, threshold = await gate.passes(brief, prisma)
    assert passed is True
    assert threshold == 50.0


@pytest.mark.asyncio
async def test_passes_when_score_equals_threshold() -> None:
    prisma = _MockPrisma([])
    gate = NicheGate()
    brief = _make_brief(score=50.0)
    passed, _ = await gate.passes(brief, prisma)
    assert passed is True


@pytest.mark.asyncio
async def test_raises_blocked_when_score_below_threshold() -> None:
    prisma = _MockPrisma([])  # fallback = 50.0
    gate = NicheGate()
    brief = _make_brief(score=35.0, niche_id="low-score-niche")
    with pytest.raises(NicheGateBlocked) as exc_info:
        await gate.passes(brief, prisma)
    err = exc_info.value
    assert err.niche_id == "low-score-niche"
    assert err.score == 35.0
    assert err.threshold == 50.0


@pytest.mark.asyncio
async def test_dynamic_threshold_from_five_winners() -> None:
    scores = [55.0, 60.0, 65.0, 70.0, 75.0]
    prisma = _MockPrisma([{"profitabilityScore": s} for s in scores])
    gate = NicheGate()

    brief_pass = _make_brief(score=65.0)
    passed, threshold = await gate.passes(brief_pass, prisma)
    assert passed is True
    assert threshold == 65.0


@pytest.mark.asyncio
async def test_dynamic_threshold_blocks_below_median() -> None:
    scores = [55.0, 60.0, 65.0, 70.0, 75.0]
    prisma = _MockPrisma([{"profitabilityScore": s} for s in scores])
    gate = NicheGate()
    brief_fail = _make_brief(score=64.9, niche_id="just-below")
    with pytest.raises(NicheGateBlocked):
        await gate.passes(brief_fail, prisma)
