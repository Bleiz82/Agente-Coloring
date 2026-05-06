"""Domain exceptions for the colorforge-agents package."""
from __future__ import annotations


class ColorforgeAgentsError(Exception):
    """Base exception for all agent errors."""


class ScoringError(ColorforgeAgentsError):
    """Error in Profitability Score computation."""


class TrendsUnavailable(ColorforgeAgentsError):
    """Trends API unavailable — caller should use fallback 0.0."""


class LLMAnalysisError(ColorforgeAgentsError):
    """Claude API call failed for pain point or style extraction."""


class EmbeddingError(ColorforgeAgentsError):
    """Qdrant embedding or upsert failed."""


class NicheGateBlocked(ColorforgeAgentsError):
    """Niche brief blocked by Niche Gate."""
    def __init__(self, niche_id: str, score: float, threshold: float) -> None:
        self.niche_id = niche_id
        self.score = score
        self.threshold = threshold
        super().__init__(
            f"Niche {niche_id} blocked: score={score:.1f} < threshold={threshold:.1f}"
        )


class StrategistError(ColorforgeAgentsError):
    """Strategist failed to produce a BookPlan."""


class ImageGenerationError(ColorforgeAgentsError):
    """Gemini image generation API call failed."""


class PDFAssemblyError(ColorforgeAgentsError):
    """ReportLab PDF assembly failed."""


class CriticError(ColorforgeAgentsError):
    """Critic agent failed (vision API or JSON parse error)."""


class ContentGateBlocked(ColorforgeAgentsError):
    """BookDraft blocked by Content Gate."""
    def __init__(self, book_id: str, verdict: str, reason: str) -> None:
        self.book_id = book_id
        self.verdict = verdict
        self.reason = reason
        super().__init__(f"Book {book_id} blocked: verdict={verdict} — {reason}")


class ListingGenerationError(ColorforgeAgentsError):
    """SEO Listing agent failed (Claude API or JSON parse error)."""


class ListingGateBlocked(ColorforgeAgentsError):
    """ListingContract blocked by Listing Gate."""
    def __init__(self, book_id: str, failed_checks: list[str]) -> None:
        self.book_id = book_id
        self.failed_checks = failed_checks
        super().__init__(
            f"Book {book_id} listing blocked: {'; '.join(failed_checks)}"
        )


class PublisherAgentError(ColorforgeAgentsError):
    """Publisher agent orchestration failure (not a KDP step failure)."""


class SalesScrapingError(ColorforgeAgentsError):
    """KDP Reports scraping failed for an account."""
    def __init__(self, account_id: str, reason: str) -> None:
        self.account_id = account_id
        self.reason = reason
        super().__init__(f"Sales scraping failed for account {account_id}: {reason}")


class InsufficientSalesData(ColorforgeAgentsError):
    """Not enough sales data for differential analysis."""
    def __init__(self, account_id: str, min_required: int, actual: int) -> None:
        self.account_id = account_id
        self.min_required = min_required
        self.actual = actual
        super().__init__(
            f"Account {account_id}: need {min_required} samples, got {actual}"
        )


class PerformanceMonitorError(ColorforgeAgentsError):
    """Performance Monitor orchestration failure."""
