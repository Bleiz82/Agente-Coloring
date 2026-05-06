"""KDP Reports Scraper — downloads and upserts daily sales CSV data."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from colorforge_kdp.types import AccountRecord
from loguru import logger

from colorforge_agents.exceptions import SalesScrapingError

_KDP_REPORTS_URL = "https://kdp.amazon.com/en_US/reports/sales"
_PAGE_GOTO_TIMEOUT = 30_000
_SELECTOR_TIMEOUT = 15_000
_DATE_INPUT_FORMAT = "%Y-%m-%d"


class KDPReportsScraper:
    def __init__(self, prisma: Any) -> None:
        self._prisma = prisma

    async def scrape_account(
        self,
        account: AccountRecord,
        page: Any,
        date_from: date,
        date_to: date,
    ) -> int:
        """Scrape KDP Reports for one account. Returns rows upserted."""
        await self._navigate_to_reports(page)
        csv_text = await self._download_csv(page, date_from, date_to)
        rows = self._parse_csv(csv_text, account.id)
        count = await self._upsert_rows(rows, self._prisma)
        logger.info(
            "KDP sales scrape complete",
            account_id=account.id,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            rows_upserted=count,
        )
        return count

    async def _navigate_to_reports(self, page: Any) -> None:
        """Navigate to KDP Sales Dashboard. Raises SalesScrapingError on timeout."""
        await page.goto(_KDP_REPORTS_URL, timeout=_PAGE_GOTO_TIMEOUT)
        try:
            await page.wait_for_selector(
                '[data-testid="sales-dashboard"], #kdp-sales-report',
                timeout=_SELECTOR_TIMEOUT,
            )
        except Exception as exc:
            raise SalesScrapingError("", "reports page timeout") from exc

    async def _download_csv(
        self, page: Any, date_from: date, date_to: date
    ) -> str:
        """Set date range, click Download, return raw CSV text. Raises SalesScrapingError."""
        try:
            await page.fill(
                '[data-testid="date-from"], #date-from',
                date_from.strftime(_DATE_INPUT_FORMAT),
            )
            await page.fill(
                '[data-testid="date-to"], #date-to',
                date_to.strftime(_DATE_INPUT_FORMAT),
            )

            async with page.expect_download() as download_info:
                await page.click('[data-testid="download-button"], #download-report-btn')

            download = await download_info.value
            path = await download.path()

            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except SalesScrapingError:
            raise
        except Exception as exc:
            raise SalesScrapingError("", f"CSV download failed: {exc}") from exc

    def _parse_csv(self, csv_text: str, account_id: str) -> list[dict[str, Any]]:
        """Parse KDP Reports CSV. Columns: Title,ASIN,Date,Units Sold,Royalty,KENP Read,Marketplace
        Returns list of dicts ready for upsert."""
        rows: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(csv_text))
        for record in reader:
            asin = record.get("ASIN", "").strip()
            if not asin:
                continue

            raw_royalty = record.get("Royalty", "0").strip().lstrip("$")
            royalty = Decimal(raw_royalty) if raw_royalty else Decimal("0")

            raw_date = record.get("Date", "").strip()
            try:
                sale_date = datetime.strptime(raw_date, _DATE_INPUT_FORMAT).date()
            except ValueError:
                continue

            marketplace = record.get("Marketplace", "US").strip() or "US"

            rows.append(
                {
                    "asin": asin,
                    "title": record.get("Title", "").strip(),
                    "date": sale_date,
                    "units_sold": int(record.get("Units Sold", "0").strip() or "0"),
                    "royalty": royalty,
                    "kenp_read": int(record.get("KENP Read", "0").strip() or "0"),
                    "marketplace": marketplace,
                    "account_id": account_id,
                }
            )
        return rows

    async def _upsert_rows(
        self, rows: list[dict[str, Any]], prisma: Any
    ) -> int:
        """Upsert sales_daily rows. Returns count of rows upserted."""
        count = 0
        for row in rows:
            asin: str = row["asin"]
            book = await prisma.book.find_first(where={"asin": asin})
            if book is None:
                logger.debug("Skipping row: no book found for ASIN", asin=asin)
                continue

            book_id: str = book.id
            sale_date: date = row["date"]
            marketplace: str = row["marketplace"]

            await prisma.salesdaily.upsert(
                where={
                    "bookId_date_marketplace": {
                        "bookId": book_id,
                        "date": sale_date,
                        "marketplace": marketplace,
                    }
                },
                data={
                    "create": {
                        "bookId": book_id,
                        "accountId": row["account_id"],
                        "date": sale_date,
                        "unitsSold": row["units_sold"],
                        "royalty": float(row["royalty"]),
                        "kenpRead": row["kenp_read"],
                        "marketplace": marketplace,
                    },
                    "update": {
                        "unitsSold": row["units_sold"],
                        "royalty": float(row["royalty"]),
                        "kenpRead": row["kenp_read"],
                    },
                },
            )
            count += 1
        return count
