"""Success Score Engine — computes SuccessScore per book from sales_daily data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

from loguru import logger

from colorforge_agents.contracts import SuccessScore


class SuccessScorer:
    def __init__(self, prisma: Any) -> None:
        self._db = prisma

    def _calc_score(
        self,
        units: int,
        royalty: float,
        kenp: int,
        refunds: int,
    ) -> float:
        base = min(royalty / 50.0, 1.0) * 60.0
        units_pts = min(units / 20.0, 1.0) * 25.0
        kenp_pts = min(kenp / 500.0, 1.0) * 10.0
        refund_penalty = min(refunds * 5, 15)
        score = max(0.0, base + units_pts + kenp_pts - refund_penalty)
        return min(score, 100.0)

    def _classify(self, royalty: float) -> Literal["winner", "flat", "loser"]:
        if royalty >= 50.0:
            return "winner"
        if royalty >= 10.0:
            return "flat"
        return "loser"

    def _percentile(self, value: float, population: list[float]) -> float:
        if not population:
            return 50.0
        return sum(1 for x in population if x <= value) / len(population) * 100.0

    async def compute(
        self,
        book_id: str,
        window_days: Literal[7, 14, 30],
    ) -> SuccessScore:
        cutoff_date = date.today() - timedelta(days=window_days)

        rows = await self._db.salesdaily.find_many(
            where={"bookId": book_id, "date": {"gte": cutoff_date}}
        )

        units_sold = sum(r.unitsSold for r in rows)
        royalty_total = float(sum(r.royalty for r in rows))
        kenp_read = sum(r.kenpRead for r in rows)
        refund_count = sum(r.refunds for r in rows)

        computed_score = self._calc_score(units_sold, royalty_total, kenp_read, refund_count)
        classification = self._classify(royalty_total)

        book = await self._db.book.find_unique(where={"id": book_id})
        account_id: str | None = book.accountId if book is not None else None
        niche_id: str | None = book.nicheId if book is not None else None

        percentile_within_account = 50.0
        percentile_within_niche = 50.0

        if account_id is not None:
            account_books = await self._db.book.find_many(
                where={"accountId": account_id, "status": "LIVE"}
            )
            account_royalties: list[float] = []
            for bid in [b.id for b in account_books]:
                peer_rows = await self._db.salesdaily.find_many(
                    where={"bookId": bid, "date": {"gte": cutoff_date}}
                )
                account_royalties.append(float(sum(r.royalty for r in peer_rows)))

            percentile_within_account = self._percentile(royalty_total, account_royalties)

            if niche_id is not None:
                niche_books = await self._db.book.find_many(
                    where={"nicheId": niche_id, "status": "LIVE"}
                )
                niche_royalties: list[float] = []
                for nb in niche_books:
                    niche_rows = await self._db.salesdaily.find_many(
                        where={"bookId": nb.id, "date": {"gte": cutoff_date}}
                    )
                    niche_royalties.append(float(sum(r.royalty for r in niche_rows)))
                percentile_within_niche = self._percentile(royalty_total, niche_royalties)

        logger.info(
            "scored book",
            book_id=book_id,
            window_days=window_days,
            score=computed_score,
            classification=classification,
        )

        return SuccessScore(
            book_id=book_id,
            window_days=window_days,
            units_sold=units_sold,
            royalty_total=royalty_total,
            kenp_read=kenp_read,
            refund_count=refund_count,
            computed_score=computed_score,
            classification=classification,
            percentile_within_account=percentile_within_account,
            percentile_within_niche=percentile_within_niche,
        )

    async def compute_all_live(
        self,
        account_id: str,
        window_days: int,
    ) -> list[SuccessScore]:
        books = await self._db.book.find_many(
            where={"accountId": account_id, "status": "LIVE"}
        )
        results: list[SuccessScore] = []
        for book in books:
            validated_window: Literal[7, 14, 30]
            if window_days == 7:
                validated_window = 7
            elif window_days == 14:
                validated_window = 14
            else:
                validated_window = 30
            score = await self.compute(book.id, validated_window)
            results.append(score)
        return results
