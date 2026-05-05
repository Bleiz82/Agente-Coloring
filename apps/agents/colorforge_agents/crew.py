"""CrewAI crew definitions for the Niche Hunt pipeline."""

from __future__ import annotations

from typing import Any

from loguru import logger

from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.deep_scout.scout import DeepScoutCore
from colorforge_agents.gates.niche_gate import NicheGate
from colorforge_agents.niche_hunter.hunter import NicheHunterConfig, NicheHunterCore


class NicheHuntCrew:
    """Orchestrates NicheHunter → DeepScout → NicheGate pipeline."""

    def __init__(
        self,
        hunter_core: NicheHunterCore,
        scout_core: DeepScoutCore,
        gate: NicheGate,
        prisma: Any,
    ) -> None:
        self._hunter = hunter_core
        self._scout = scout_core
        self._gate = gate
        self._prisma = prisma

    async def run(self, config: NicheHunterConfig) -> list[NicheBrief]:
        """Run the full pipeline: hunt → enrich → gate → return passing briefs."""
        logger.info("NicheHuntCrew starting — {} categories", len(config.categories))

        candidates = await self._hunter.run(config)
        logger.info("Hunter found {} candidates", len(candidates))

        passing_briefs: list[NicheBrief] = []
        for candidate in candidates:
            try:
                brief = await self._scout.enrich(candidate)
                passed, threshold = await self._gate.passes(brief, self._prisma)
                if passed:
                    passing_briefs.append(brief)
            except Exception as exc:
                logger.warning("Candidate '{}' failed pipeline: {}", candidate.primary_keyword, exc)

        logger.info(
            "NicheHuntCrew done — {}/{} briefs passed gate",
            len(passing_briefs),
            len(candidates),
        )
        return passing_briefs
