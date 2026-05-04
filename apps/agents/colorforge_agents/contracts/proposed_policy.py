"""ProposedPolicy contract — output of Performance Monitor flywheel."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProposedPolicy(BaseModel):
    """A learned rule proposed by the Performance Monitor."""

    rule_text: str = Field(min_length=1)
    rule_machine_readable: dict[str, Any]
    applies_to: list[str] = Field(min_length=1)
    originating_experiment_id: str | None = None
    confidence_score: float = Field(ge=0, le=100)
    supporting_evidence: list[str]
    status: Literal["PROPOSED", "APPROVED", "RETIRED", "REJECTED"]
    proposed_at: datetime


PROPOSED_POLICY_EXAMPLE = ProposedPolicy(
    rule_text="Covers with dark backgrounds (brightness < 30) in mandala niche convert 24% better",
    rule_machine_readable={
        "type": "cover_preference",
        "niche_filter": "mandala",
        "parameter": "cover_brightness",
        "operator": "lt",
        "value": 30,
        "effect_size": 0.24,
    },
    applies_to=["strategist", "generator"],
    originating_experiment_id="880e8400-e29b-41d4-a716-446655440003",
    confidence_score=72,
    supporting_evidence=[
        "770e8400-e29b-41d4-a716-446655440002",
        "770e8400-e29b-41d4-a716-446655440005",
    ],
    status="PROPOSED",
    proposed_at=datetime.fromisoformat("2026-06-15T03:00:00+00:00"),
)
