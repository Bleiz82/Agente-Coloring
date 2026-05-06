"""Publisher agent — bridges ListingContract + BookDraft to KDPPublisher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.book_plan import BookFormat
from colorforge_agents.contracts.listing import ListingContract
from colorforge_agents.contracts.validation_report import ValidationReport
from colorforge_agents.exceptions import PublisherAgentError
from colorforge_agents.gates.content_gate import ContentGate
from colorforge_agents.gates.listing_gate import ListingGate


@dataclass(frozen=True)
class PublisherResult:
    book_id: str
    asin: str
    account_id: str


class PublisherAgent:
    """Orchestrates book publishing: gate checks → quota → browser → KDPPublisher → DB."""

    def __init__(
        self,
        content_gate: ContentGate,
        listing_gate: ListingGate,
        prisma: Any,
        assets_base: Path,
    ) -> None:
        self._content_gate = content_gate
        self._listing_gate = listing_gate
        self._prisma = prisma
        self._assets_base = assets_base

    async def publish(
        self,
        listing: ListingContract,
        draft: BookDraft,
        account: Any,  # colorforge_kdp.types.AccountRecord
        report: ValidationReport,
        book_format: BookFormat = BookFormat.PAPERBACK,
    ) -> PublisherResult:
        """Run full publish pipeline. Returns PublisherResult with ASIN on success."""
        book_id = draft.book_id

        # 1. Content quality gate
        self._content_gate.passes(report)  # raises ContentGateBlocked if not

        # 2. Listing compliance gate
        self._listing_gate.passes(listing)  # raises ListingGateBlocked if not

        # 3. Weekly per-format quota check
        try:
            from colorforge_kdp.quota import check_and_consume_quota
            await check_and_consume_quota(account, self._prisma, book_format.value)
        except ImportError as exc:
            raise PublisherAgentError("colorforge_kdp not installed") from exc

        # 4. Transition → PUBLISHING
        await self._transition_state(book_id, "LISTING", "PUBLISHING", "publisher_agent_start")

        # 5. Browser session + KDP publish
        assets_dir = self._assets_base / account.id / book_id
        asin = ""
        try:
            from colorforge_kdp.browser import AccountBrowserManager
            from colorforge_kdp.publisher import KDPPublisher
            from colorforge_kdp.types import PublishJobState

            listing_data = self._map_listing(listing, account)
            draft_data = self._map_draft(draft)
            job_state = PublishJobState(book_id=book_id, account_id=account.id)

            async with AccountBrowserManager(account, prisma=self._prisma) as (_ctx, page):
                publisher = KDPPublisher(page, job_state, assets_dir, self._prisma)
                asin = await publisher.publish(listing_data, draft_data)
        except Exception as exc:
            logger.error("book={} KDP publish failed: {}", book_id, exc)
            reason = f"publish_failed: {exc}"
            await self._transition_state(book_id, "PUBLISHING", "VALIDATING", reason)
            raise PublisherAgentError(f"KDP publish failed for {book_id}: {exc}") from exc

        # 6. Persist ASIN and transition → LIVE
        await self._write_asin(book_id, asin)
        await self._transition_state(book_id, "PUBLISHING", "LIVE", f"asin={asin}")

        logger.info("book={} published successfully asin={}", book_id, asin or "unknown")
        return PublisherResult(book_id=book_id, asin=asin, account_id=account.id)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _map_listing(self, listing: ListingContract, account: Any) -> Any:
        from colorforge_kdp.publisher import ListingData

        author_first, author_last = self._split_author(account.label)
        price_eur = (
            listing.price_eur if listing.price_eur is not None
            else round(listing.price_usd * 0.93, 2)
        )
        price_gbp = (
            listing.price_gbp if listing.price_gbp is not None
            else round(listing.price_usd * 0.79, 2)
        )

        return ListingData(
            title=listing.title,
            subtitle=listing.subtitle or "",
            author_first=author_first,
            author_last=author_last,
            description=listing.description_html,
            keywords=listing.keywords,
            price_usd=listing.price_usd,
            price_eur=price_eur,
            price_gbp=price_gbp,
            bisac_categories=listing.bisac_codes,
        )

    def _map_draft(self, draft: BookDraft) -> Any:
        from colorforge_kdp.publisher import BookDraftData

        return BookDraftData(
            interior_pdf=Path(draft.manuscript_pdf_path),
            cover_pdf=Path(draft.cover_pdf_path),
        )

    @staticmethod
    def _split_author(brand_author: str) -> tuple[str, str]:
        parts = brand_author.strip().split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "", parts[0]

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _transition_state(
        self, book_id: str, from_state: str, to_state: str, reason: str
    ) -> None:
        try:
            await self._prisma.book.update(
                where={"id": book_id},
                data={"state": to_state, "updatedAt": datetime.now(tz=UTC)},
            )
            await self._prisma.bookevent.create(
                data={
                    "bookId": book_id,
                    "eventType": "state_transition",
                    "payload": {"from": from_state, "to": to_state, "reason": reason},
                    "createdAt": datetime.now(tz=UTC),
                }
            )
        except Exception as exc:
            logger.error("book={} DB state transition failed: {}", book_id, exc)

    async def _write_asin(self, book_id: str, asin: str) -> None:
        if not asin:
            return
        try:
            await self._prisma.book.update(
                where={"id": book_id},
                data={"asin": asin, "updatedAt": datetime.now(tz=UTC)},
            )
        except Exception as exc:
            logger.error("book={} failed to write ASIN {}: {}", book_id, asin, exc)
