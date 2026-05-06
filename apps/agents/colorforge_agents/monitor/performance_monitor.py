"""Performance Monitor — nightly orchestrator that closes the flywheel."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from colorforge_agents.contracts import SuccessScore
from colorforge_agents.exceptions import InsufficientSalesData
from colorforge_agents.monitor.analyzer import DifferentialAnalyzer, DifferentialReport
from colorforge_agents.monitor.policy_proposer import PolicyProposer
from colorforge_agents.monitor.scorer import SuccessScorer
from colorforge_agents.monitor.snapshot_writer import RoyaltySnapshotWriter


@dataclass
class PerformanceMonitorResult:
    accounts_scraped: int
    books_scored: int
    policies_proposed: int
    alerts_written: int
    run_date: datetime = field(default_factory=lambda: datetime.now(UTC))


class PerformanceMonitor:
    def __init__(
        self,
        prisma: Any,
        claude_client: Any,
        assets_base: Path,
    ) -> None:
        self._prisma = prisma
        self._claude = claude_client
        self._assets_base = assets_base
        self._scorer = SuccessScorer(prisma)
        self._analyzer = DifferentialAnalyzer(prisma)
        self._proposer = PolicyProposer(claude_client, prisma)
        self._snapshots = RoyaltySnapshotWriter(prisma)

    async def run(self, account_ids: list[str]) -> PerformanceMonitorResult:
        books_scored = 0
        policies_proposed = 0
        alerts_written = 0
        accounts_scraped = 0

        for account_id in account_ids:
            try:
                scores = await self._score_and_classify(account_id)
                books_scored += len(scores)
                accounts_scraped += 1

                loser_count = sum(1 for s in scores if s.classification == "loser")
                if scores and loser_count / len(scores) > 0.5:
                    await self._write_alert(
                        severity="WARNING",
                        source="performance_monitor",
                        title="High loser ratio",
                        message=f"{loser_count}/{len(scores)} books are losers in last 30 days",
                        account_id=account_id,
                        book_id=None,
                    )
                    alerts_written += 1

            except Exception as exc:
                logger.error("Score and classify failed", account_id=account_id, exc_info=exc)
                await self._write_alert(
                    severity="ERROR",
                    source="performance_monitor",
                    title="Scoring failed",
                    message=str(exc),
                    account_id=account_id,
                    book_id=None,
                )
                alerts_written += 1
                continue

            try:
                report = await self._run_differential(account_id)
                proposed = await self._propose_policies(report, account_id)
                policies_proposed += len(proposed)

                for policy in proposed:
                    if policy.confidence_score > 70:
                        await self._write_alert(
                            severity="INFO",
                            source="performance_monitor",
                            title="High-confidence policy proposed",
                            message=policy.rule_text,
                            account_id=account_id,
                            book_id=None,
                        )
                        alerts_written += 1

            except InsufficientSalesData as exc:
                logger.info(
                    "Insufficient data for differential analysis — skipping",
                    account_id=account_id,
                    detail=str(exc),
                )
            except Exception as exc:
                logger.error("Differential analysis failed", account_id=account_id, exc_info=exc)

        await self._write_snapshots(account_ids)

        result = PerformanceMonitorResult(
            accounts_scraped=accounts_scraped,
            books_scored=books_scored,
            policies_proposed=policies_proposed,
            alerts_written=alerts_written,
        )
        logger.info("Performance monitor run complete", **{
            "accounts_scraped": result.accounts_scraped,
            "books_scored": result.books_scored,
            "policies_proposed": result.policies_proposed,
            "alerts_written": result.alerts_written,
        })
        return result

    async def _score_and_classify(self, account_id: str) -> list[SuccessScore]:
        return await self._scorer.compute_all_live(account_id, window_days=30)

    async def _run_differential(self, account_id: str) -> DifferentialReport:
        return await self._analyzer.analyze(account_id, window_days=30)

    async def _propose_policies(
        self, report: DifferentialReport, account_id: str
    ) -> list[Any]:
        return await self._proposer.propose(report, account_id)

    async def _write_snapshots(self, account_ids: list[str]) -> None:
        year_month = date.today().strftime("%Y-%m")
        for account_id in account_ids:
            try:
                await self._snapshots.write_monthly(account_id, year_month)
            except Exception as exc:
                logger.error("Snapshot write failed", account_id=account_id, exc_info=exc)

    async def _write_alert(
        self,
        severity: str,
        source: str,
        title: str,
        message: str,
        account_id: str | None,
        book_id: str | None,
    ) -> None:
        data: dict[str, Any] = {
            "severity": severity,
            "source": source,
            "title": title,
            "message": message,
        }
        if account_id is not None:
            data["accountId"] = account_id
        if book_id is not None:
            data["bookId"] = book_id
        try:
            await self._prisma.alert.create(data=data)
        except Exception as exc:
            logger.error("Failed to write alert", exc_info=exc)
