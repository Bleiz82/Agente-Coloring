"""Tests for PolicyProposer — ProposedPolicy generation from differential signals."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from colorforge_agents.monitor.analyzer import DifferentialReport, DifferentialSignal
from colorforge_agents.monitor.policy_proposer import PolicyProposer


def _make_signal(feature: str = "page_count", effect: float = 0.8) -> DifferentialSignal:
    return DifferentialSignal(
        feature_name=feature,
        winner_value=60.0,
        loser_value=30.0,
        effect_size=effect,
        direction="higher_is_better",
    )


def _make_report(n_signals: int = 3, winners: int = 5, losers: int = 5) -> DifferentialReport:
    return DifferentialReport(
        winners_count=winners,
        losers_count=losers,
        signals=[_make_signal(f"feat_{i}", 0.5 + i * 0.1) for i in range(n_signals)],
        analysis_date=datetime.now(UTC),
    )


def _make_proposer() -> PolicyProposer:
    return PolicyProposer(client=MagicMock(), prisma=MagicMock())


# ── propose returns empty on edge cases ───────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_empty_signals():
    p = _make_proposer()
    report = DifferentialReport(winners_count=5, losers_count=5, signals=[])
    result = await p.propose(report, "acc-1")
    assert result == []


@pytest.mark.asyncio
async def test_propose_insufficient_winners():
    p = _make_proposer()
    report = _make_report(winners=2, losers=5)
    result = await p.propose(report, "acc-1")
    assert result == []


@pytest.mark.asyncio
async def test_propose_insufficient_losers():
    p = _make_proposer()
    report = _make_report(winners=5, losers=1)
    result = await p.propose(report, "acc-1")
    assert result == []


# ── Claude call failure is swallowed ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_claude_failure_returns_empty():
    p = _make_proposer()
    p._client.messages.create = AsyncMock(side_effect=Exception("API timeout"))
    p._prisma.policy.create = AsyncMock()
    report = _make_report()
    result = await p.propose(report, "acc-1")
    assert result == []


# ── _parse_response ───────────────────────────────────────────────────────────

def test_parse_response_valid():
    p = _make_proposer()
    raw = [
        {
            "rule_text": "Books with 60+ pages outperform shorter ones",
            "rule_machine_readable": {"type": "page_count", "operator": "gte", "value": 60},
            "applies_to": ["strategist"],
            "confidence_score": 75,
            "supporting_evidence": [],
        }
    ]
    policies = p._parse_response(raw)
    assert len(policies) == 1
    assert policies[0].rule_text == "Books with 60+ pages outperform shorter ones"
    assert policies[0].status == "PROPOSED"
    assert policies[0].confidence_score == 75.0


def test_parse_response_skips_empty_rule_text():
    p = _make_proposer()
    raw = [{"rule_text": "", "rule_machine_readable": {}, "applies_to": [], "confidence_score": 50}]
    policies = p._parse_response(raw)
    assert policies == []


def test_parse_response_max_five():
    p = _make_proposer()
    raw = [
        {
            "rule_text": f"Rule {i}", "rule_machine_readable": {},
            "applies_to": ["strategist"], "confidence_score": 50,
        }
        for i in range(10)
    ]
    policies = p._parse_response(raw)
    assert len(policies) == 5


# ── _build_prompt ─────────────────────────────────────────────────────────────

def test_build_prompt_contains_signal_names():
    p = _make_proposer()
    report = _make_report(n_signals=2)
    prompt = p._build_prompt(report)
    assert "feat_0" in prompt
    assert "feat_1" in prompt
    assert "Winners: 5" in prompt
    assert "Losers: 5" in prompt


# ── _save_policies called ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_saves_to_db():
    p = _make_proposer()
    raw_response = [
        {
            "rule_text": "Test rule",
            "rule_machine_readable": {},
            "applies_to": ["strategist"],
            "confidence_score": 60,
            "supporting_evidence": [],
        }
    ]
    p._call_claude = AsyncMock(return_value=raw_response)  # type: ignore[method-assign]
    p._prisma.policy.create = AsyncMock()

    report = _make_report()
    await p.propose(report, "acc-1")

    p._prisma.policy.create.assert_called_once()
