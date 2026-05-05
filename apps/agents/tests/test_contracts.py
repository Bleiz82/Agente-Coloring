"""Round-trip serialization tests for all Pydantic contracts."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from colorforge_agents.contracts.book_draft import BOOK_DRAFT_EXAMPLE, BookDraft
from colorforge_agents.contracts.book_plan import BOOK_PLAN_EXAMPLE, BookPlan
from colorforge_agents.contracts.listing import LISTING_EXAMPLE, ListingContract
from colorforge_agents.contracts.niche_brief import NICHE_BRIEF_EXAMPLE, NicheBrief
from colorforge_agents.contracts.niche_candidate import (
    NICHE_CANDIDATE_EXAMPLE,
    NicheCandidate,
)
from colorforge_agents.contracts.proposed_policy import (
    PROPOSED_POLICY_EXAMPLE,
    ProposedPolicy,
)
from colorforge_agents.contracts.success_score import SUCCESS_SCORE_EXAMPLE, SuccessScore
from colorforge_agents.contracts.validation_report import (
    VALIDATION_REPORT_EXAMPLE,
    ValidationReport,
)


def _round_trip(model_class: type, example: object) -> None:
    """Serialize to JSON and back, assert equality."""
    json_str = example.model_dump_json()  # type: ignore[union-attr]
    restored = model_class.model_validate_json(json_str)
    assert restored == example


def test_niche_candidate_round_trip() -> None:
    _round_trip(NicheCandidate, NICHE_CANDIDATE_EXAMPLE)


def test_niche_candidate_from_dict() -> None:
    data = NICHE_CANDIDATE_EXAMPLE.model_dump()
    parsed = NicheCandidate.model_validate(data)
    assert parsed.primary_keyword == "ocean mandala coloring book"


def test_niche_brief_round_trip() -> None:
    _round_trip(NicheBrief, NICHE_BRIEF_EXAMPLE)


def test_niche_brief_pain_points() -> None:
    assert len(NICHE_BRIEF_EXAMPLE.pain_points) >= 1
    assert NICHE_BRIEF_EXAMPLE.pain_points[0].severity >= 1


def test_book_plan_round_trip() -> None:
    _round_trip(BookPlan, BOOK_PLAN_EXAMPLE)


def test_book_plan_page_count_validation() -> None:
    data = BOOK_PLAN_EXAMPLE.model_dump()
    data["page_count"] = 5  # below minimum 20
    with pytest.raises(ValidationError):
        BookPlan.model_validate(data)


def test_book_draft_round_trip() -> None:
    _round_trip(BookDraft, BOOK_DRAFT_EXAMPLE)


def test_validation_report_round_trip() -> None:
    _round_trip(ValidationReport, VALIDATION_REPORT_EXAMPLE)


def test_validation_report_invalid_verdict() -> None:
    data = VALIDATION_REPORT_EXAMPLE.model_dump()
    data["verdict"] = "maybe"
    with pytest.raises(ValidationError):
        ValidationReport.model_validate(data)


def test_listing_round_trip() -> None:
    _round_trip(ListingContract, LISTING_EXAMPLE)


def test_listing_keyword_count() -> None:
    assert len(LISTING_EXAMPLE.keywords) == 7


def test_listing_ai_disclosure_always_true() -> None:
    assert LISTING_EXAMPLE.ai_disclosure is True


def test_success_score_round_trip() -> None:
    _round_trip(SuccessScore, SUCCESS_SCORE_EXAMPLE)


def test_success_score_valid_windows() -> None:
    data = SUCCESS_SCORE_EXAMPLE.model_dump()
    data["window_days"] = 15
    with pytest.raises(ValidationError):
        SuccessScore.model_validate(data)


def test_proposed_policy_round_trip() -> None:
    _round_trip(ProposedPolicy, PROPOSED_POLICY_EXAMPLE)


def test_proposed_policy_json_compatibility() -> None:
    """Verify JSONB-ready serialization (what goes into Postgres)."""
    json_str = PROPOSED_POLICY_EXAMPLE.model_dump_json()
    data = json.loads(json_str)
    assert isinstance(data, dict)
    assert data["status"] == "PROPOSED"
    assert data["confidence_score"] == 72
