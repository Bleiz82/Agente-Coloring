"""Niche Gate: profitability threshold check."""

from __future__ import annotations

import statistics
from typing import Any

from loguru import logger

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import NicheGateBlocked

_MIN_HISTORY_POINTS = 5


class NicheGate:
    """Blocks NicheBriefs whose profitability score is below the dynamic threshold.

    Threshold = median score of niches linked to historically winning books.
    Falls back to FALLBACK_THRESHOLD if fewer than 5 data points exist.
    """

    FALLBACK_THRESHOLD: float = 50.0

    async def compute_threshold(self, prisma: Any) -> float:
        """Query DB for winner niche scores and return their median."""
        try:
            records = await prisma.niche_brief_find_many(
                where={
                    "books": {
                        "some": {
                            "successScores": {
                                "some": {"classification": "winner"}
                            }
                        }
                    }
                },
                select={"profitabilityScore": True},
            )
            scores = [
                float(r["profitabilityScore"])
                for r in records
                if r.get("profitabilityScore") is not None
            ]
        except Exception as exc:
            logger.warning("NicheGate DB query failed, using fallback threshold: {}", exc)
            return self.FALLBACK_THRESHOLD

        if len(scores) < _MIN_HISTORY_POINTS:
            logger.info(
                "NicheGate: only {} historical data points, using fallback threshold {:.1f}",
                len(scores),
                self.FALLBACK_THRESHOLD,
            )
            return self.FALLBACK_THRESHOLD

        threshold = statistics.median(scores)
        logger.info("NicheGate threshold computed from {} winners: {:.1f}", len(scores), threshold)
        return threshold

    async def passes(self, brief: NicheBrief, prisma: Any) -> tuple[bool, float]:
        """Return (passes, threshold). Raises NicheGateBlocked if blocked."""
        threshold = await self.compute_threshold(prisma)
        if brief.profitability_score >= threshold:
            logger.info(
                "NicheGate PASS: '{}' score={:.1f} >= threshold={:.1f}",
                brief.primary_keyword,
                brief.profitability_score,
                threshold,
            )
            return True, threshold

        logger.info(
            "NicheGate BLOCK: '{}' score={:.1f} < threshold={:.1f}",
            brief.primary_keyword,
            brief.profitability_score,
            threshold,
        )
        raise NicheGateBlocked(brief.niche_id, brief.profitability_score, threshold)
