"""Policy Proposer — generates ProposedPolicy rules from DifferentialReport signals."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from colorforge_agents.contracts import ProposedPolicy
from colorforge_agents.config.models import POLICY_PROPOSER_MODEL
from colorforge_agents.monitor.analyzer import DifferentialReport


class PolicyProposer:
    def __init__(self, client: Any, prisma: Any) -> None:
        self._client = client
        self._prisma = prisma

    async def propose(self, report: DifferentialReport, account_id: str) -> list[ProposedPolicy]:
        if len(report.signals) == 0:
            return []
        if report.winners_count < 3 or report.losers_count < 3:
            return []

        prompt = self._build_prompt(report)

        try:
            raw = await self._call_claude(prompt)
        except Exception as exc:
            logger.warning(
                "Policy proposer Claude call failed",
                exc_info=exc,
                account_id=account_id,
            )
            return []

        policies = self._parse_response(raw)
        await self._save_policies(policies)
        return policies

    def _build_prompt(self, report: DifferentialReport) -> str:
        signal_lines = "\n".join(
            f"- {s.feature_name}: winners={s.winner_value}, losers={s.loser_value}, "
            f"effect_size={s.effect_size:.2f}, direction={s.direction}"
            for s in report.signals[:5]
        )
        return (
            "You are a KDP publishing strategy analyst.\n"
            "Analyze these differential signals between winner and loser books.\n"
            "Return a JSON array of at most 5 policy rules (the most impactful ones).\n\n"
            f"Winners: {report.winners_count} books\n"
            f"Losers: {report.losers_count} books\n\n"
            f"Top signals by effect size:\n{signal_lines}\n\n"
            "Return JSON array where each element has:\n"
            "{\n"
            '  "rule_text": "human-readable rule (1 sentence)",\n'
            '  "rule_machine_readable": '
            '{"type": "...", "parameter": "...", "operator": "...", "value": ...},\n'
            '  "applies_to": ["strategist" | "generator" | "seo"],\n'
            '  "confidence_score": 0-100 (based on effect size and sample size),\n'
            '  "supporting_evidence": []\n'
            "}"
        )

    async def _call_claude(self, prompt: str) -> list[dict[str, Any]]:
        response = await self._client.messages.create(
            model=POLICY_PROPOSER_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text: str = response.content[0].text
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group())  # type: ignore[no-any-return]

    def _parse_response(self, raw: list[dict[str, Any]]) -> list[ProposedPolicy]:
        policies: list[ProposedPolicy] = []
        for item in raw[:5]:
            rule_text: str = item.get("rule_text", "")
            if not rule_text:
                continue
            policies.append(
                ProposedPolicy(
                    rule_text=rule_text,
                    rule_machine_readable=item.get("rule_machine_readable", {}),
                    applies_to=item.get("applies_to", ["strategist"]),
                    originating_experiment_id=None,
                    confidence_score=float(item.get("confidence_score", 50)),
                    supporting_evidence=item.get("supporting_evidence", []),
                    status="PROPOSED",
                    proposed_at=datetime.now(UTC),
                )
            )
        return policies

    async def _save_policies(self, policies: list[ProposedPolicy]) -> None:
        for policy in policies:
            await self._prisma.policy.create(
                data={
                    "ruleText": policy.rule_text,
                    "ruleMachineReadable": policy.rule_machine_readable,
                    "appliesTo": policy.applies_to,
                    "confidenceScore": policy.confidence_score,
                    "supportingEvidence": policy.supporting_evidence,
                    "status": "PROPOSED",
                }
            )
