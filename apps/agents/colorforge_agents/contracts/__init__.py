"""ColorForge AI — Pydantic v2 contract models.

These mirror the Zod schemas in the TypeScript side exactly.
Every agent input/output is one of these models serialized to JSONB in Postgres.
"""

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.contracts.niche_candidate import NicheCandidate
from colorforge_agents.contracts.proposed_policy import ProposedPolicy
from colorforge_agents.contracts.success_score import SuccessScore
from colorforge_agents.contracts.validation_report import ValidationReport

__all__ = [
    "BookDraft",
    "BookPlan",
    "ListingContract",
    "NicheBrief",
    "NicheCandidate",
    "ProposedPolicy",
    "SuccessScore",
    "ValidationReport",
]
