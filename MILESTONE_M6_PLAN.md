# Milestone 6 — Performance Monitor + Flywheel

**Status:** In Progress
**Owner:** architect (planning) → implementer (execution) → tester (verification)
**Token budget:** 250k
**Branch:** main (continuing)

## Scope (from SPEC.md §3.2 §3.4 §9)

Build the agent that closes the flywheel:
- **KDP Reports Scraper**: Playwright scraper that logs into KDP Reports for each account
  and harvests daily sales data into `sales_daily` table.
- **Success Score Engine**: Computes `SuccessScore` per book at 7/14/30-day windows from
  `sales_daily`; classifies winner/flat/loser per SPEC §1 definitions.
- **Differential Analyzer**: Weekly analysis — extracts signals that distinguish winners from
  losers (niche, page count, price, style, keyword patterns, etc.).
- **Policy Proposer**: Uses Claude Sonnet 4.6 to generate human-readable + machine-readable
  `ProposedPolicy` records from differential analysis output.
- **Royalty Snapshot Writer**: Monthly aggregates into `royalty_snapshots` per account.
- **Performance Monitor orchestrator**: Wraps all components, writes to `policies`/`alerts`
  tables, runs via systemd timer nightly at 03:00.
- **scripts/run_monitor.py**: CLI entrypoint for manual runs and dry-run mode.

## Acceptance criteria (whole milestone)

- [ ] `PerformanceMonitor.run(account_ids)` fetches sales, scores all live books, writes
      `ProposedPolicy` records to DB — integration test with seeded DB passes
- [ ] `SuccessScorer.compute(book_id, window)` returns correct `SuccessScore` from seed data
- [ ] `BookClassifier.classify_all(account_id)` returns winner/flat/loser for each book
- [ ] `DifferentialAnalyzer.analyze(winners, losers)` returns non-empty `DifferentialReport`
- [ ] `PolicyProposer.propose(report)` returns list of `ProposedPolicy` with status=PROPOSED
- [ ] `RoyaltySnapshotWriter.write_monthly(account_id, year_month)` upserts correct aggregate
- [ ] `python scripts/run_monitor.py --dry-run` exits 0
- [ ] mypy --strict + ruff passing on all M6 modules
- [ ] >80% coverage on scorer.py and analyzer.py (deterministic logic)

## Architectural decisions

[2026-05-06] KDP Reports scraper uses Playwright, same stealth setup as kdp-client (M2).
  Navigates to: kdp.amazon.com → Reports & Analytics → KDP Sales Dashboard.
  Downloads CSV via "Download" button, parses CSV, upserts to sales_daily.
  Idempotent: uses @@unique([bookId, date, marketplace]) — upsert on conflict.

[2026-05-06] SuccessScore.computed_score formula:
  base = min(royalty_total / 50.0, 1.0) * 60   # 60 pts from royalty (winner = $50)
  units = min(units_sold / 20.0, 1.0) * 25      # 25 pts from units (20+ = full)
  kenp = min(kenp_read / 500.0, 1.0) * 10       # 10 pts from KENPs (500 = full)
  refund_penalty = min(refund_count * 5, 15)    # -15 pts max for refunds
  computed_score = max(0, base + units + kenp - refund_penalty)
  classification: winner if royalty_total >= 50, flat if >= 10, else loser.

[2026-05-06] Differential analysis compares medians of numeric features (page count, price,
  profitability_score) and mode of categorical features (niche category, style) between
  winner group and loser group. Minimum sample size: 3 winners AND 3 losers.
  If insufficient data, returns empty policy list (not an error — expected early on).

[2026-05-06] Policy Proposer uses Claude Sonnet 4.6 with JSON response.
  Prompt includes top 5 differential signals ranked by effect size.
  Each signal → one ProposedPolicy. Max 5 policies per run to avoid spam.
  Fallback: if Claude fails, skip policy generation (log warning, not error).

[2026-05-06] Royalty snapshots: computed as SUM(royalty) per (accountId, yearMonth) from
  sales_daily. hitRate = winner_count / total_live_books * 100.
  Upserted monthly (not incremental), so re-running is safe.

[2026-05-06] Alerts written to `alerts` table for:
  - account with zero sales scraped (severity=WARNING)
  - >50% of books classified loser in last 30 days (severity=WARNING)
  - Policy confidence_score > 70 proposed (severity=INFO)

## Tasks

### T6.1 — M6 exceptions
**File:** `apps/agents/colorforge_agents/exceptions.py` (append)
**New exceptions:**
- `SalesScrapingError(account_id, reason)` — KDP Reports scraping failed
- `PerformanceMonitorError` — monitor orchestration failure
- `InsufficientSalesData(account_id, min_required, actual)` — not enough data for analysis

### T6.2 — KDP Reports Scraper
**File:** `apps/agents/colorforge_agents/monitor/scraper.py`

**Class:** `KDPReportsScraper(page: Page, prisma: Any)`
- `async scrape_account(account: AccountRecord, date_from: date, date_to: date) -> int`
  (returns number of rows upserted)
- `async _navigate_to_reports(page: Page) -> None`
- `async _download_csv(page: Page, date_from, date_to) -> str` (raw CSV text)
- `_parse_csv(csv_text: str, account_id: str) -> list[dict[str, Any]]`
- `async _upsert_rows(rows: list[dict], prisma: Any) -> int`

**CSV format from KDP Reports:**
  Title, ASIN, Date, Units Sold, Royalty, KENP Read, Marketplace

### T6.3 — Success Score Engine + Classifier
**File:** `apps/agents/colorforge_agents/monitor/scorer.py`

**Class:** `SuccessScorer(prisma: Any)`
- `async compute(book_id: str, window_days: Literal[7, 14, 30]) -> SuccessScore`
- `async compute_all_live(account_id: str, window_days: int) -> list[SuccessScore]`
- `_calc_score(units: int, royalty: float, kenp: int, refunds: int) -> float`
- `_classify(royalty: float) -> Literal["winner", "flat", "loser"]`
- `_percentile(value: float, population: list[float]) -> float`

### T6.4 — Differential Analyzer
**File:** `apps/agents/colorforge_agents/monitor/analyzer.py`

**Dataclass:** `DifferentialReport`
- `winners_count: int`
- `losers_count: int`
- `signals: list[DifferentialSignal]`
- `analysis_date: datetime`

**Dataclass:** `DifferentialSignal`
- `feature_name: str`
- `winner_value: float | str`
- `loser_value: float | str`
- `effect_size: float`  # Cohen's d for numeric, Cramér's V for categorical
- `direction: Literal["higher_is_better", "lower_is_better", "categorical"]`

**Class:** `DifferentialAnalyzer(prisma: Any)`
- `async analyze(account_id: str, window_days: int = 30) -> DifferentialReport`
- `_numeric_signals(winners, losers) -> list[DifferentialSignal]`
- `_categorical_signals(winners, losers) -> list[DifferentialSignal]`
- `_cohens_d(a: list[float], b: list[float]) -> float`
- `_cramers_v(a: list[str], b: list[str]) -> float`

**Features analyzed:**
  Numeric: page_count, price_usd, profitability_score, days_since_publish
  Categorical: niche_category, style_tag (from NicheBrief)

### T6.5 — Policy Proposer
**File:** `apps/agents/colorforge_agents/monitor/policy_proposer.py`

**Class:** `PolicyProposer(client: Any, prisma: Any)`
- `async propose(report: DifferentialReport, account_id: str) -> list[ProposedPolicy]`
- `async _call_claude(prompt: str) -> list[dict[str, Any]]`
- `_build_prompt(report: DifferentialReport) -> str`
- `_parse_response(raw: list[dict]) -> list[ProposedPolicy]`
- `async _save_policies(policies: list[ProposedPolicy]) -> None`

### T6.6 — Royalty Snapshot Writer
**File:** `apps/agents/colorforge_agents/monitor/snapshot_writer.py`

**Class:** `RoyaltySnapshotWriter(prisma: Any)`
- `async write_monthly(account_id: str, year_month: str) -> RoyaltySnapshot`
  (year_month format: "2026-05")
- `async _count_winners(account_id: str, year_month: str) -> int`
- `async _count_live_books(account_id: str) -> int`

### T6.7 — Performance Monitor orchestrator
**File:** `apps/agents/colorforge_agents/monitor/performance_monitor.py`

**Class:** `PerformanceMonitor(prisma, claude_client, assets_base: Path)`
- `async run(account_ids: list[str]) -> PerformanceMonitorResult`
- `async _scrape_account(account_id, scraper) -> int`
- `async _score_and_classify(account_id) -> list[SuccessScore]`
- `async _run_differential(account_id) -> DifferentialReport`
- `async _propose_policies(report, account_id) -> list[ProposedPolicy]`
- `async _write_snapshots(account_ids) -> None`
- `async _write_alert(severity, source, title, message, account_id, book_id) -> None`

**Dataclass:** `PerformanceMonitorResult`
- `accounts_scraped: int`
- `books_scored: int`
- `policies_proposed: int`
- `alerts_written: int`
- `run_date: datetime`

### T6.8 — scripts/run_monitor.py
**File:** `scripts/run_monitor.py`
- `--dry-run`: validate imports + env, exits 0
- `--account-id UUID`: run for single account
- `--all-accounts`: run for all accounts in DB
- `--date-from YYYY-MM-DD`: override date range start (default: yesterday)

### T6.9 — Full test suite
**New test files:**
- `apps/agents/tests/test_scorer.py` (≥12 tests — all SuccessScore edge cases)
- `apps/agents/tests/test_analyzer.py` (≥8 tests — differential analysis, insufficient data)
- `apps/agents/tests/test_policy_proposer.py` (≥8 tests — mock Claude, fallback)
- `apps/agents/tests/test_performance_monitor.py` (≥10 tests — integration, mock scraper)
