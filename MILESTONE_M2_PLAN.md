# Milestone 2 — KDP Client + Multi-Account Manager

**Status:** Complete
**Owner:** architect (planning) → implementer (execution) → tester (verification)
**Token budget:** 200k
**Branch:** main (continuing from m1-foundation merge)

## Scope (from SPEC.md §3, §8)
Build `packages/kdp-client` — the Playwright-based KDP automation library — and `apps/worker` — the RQ-based process that hosts browser jobs. This is the lowest-level layer everything else builds on.

## Acceptance criteria (whole milestone)
- [x] `packages/kdp-client` installs cleanly (`uv sync`)
- [x] Multi-account BrowserContext isolation: each account gets its own context, proxy, fingerprint, storageState — verified by test
- [x] storageState encrypt/decrypt roundtrip works (age binary)
- [x] Quota enforcement raises `QuotaExceeded` at 5/day (ramp period) and 10/day (post-60d)
- [x] KDP publisher 8-step flow: step resumption from last successful step — verified by mock test
- [x] Amazon Bestsellers scraper extracts CompetitorSnap fields from mock HTML
- [x] Worker process starts (`python apps/worker/run_worker.py --dry-run`) without errors
- [x] mypy --strict + ruff passing on all M2 modules
- [x] 40 tests passing, critical paths (storage, quota, browser) >80% coverage
- [x] All KDP UI selectors marked `# VERIFY_SELECTOR` — operator must validate on first real run

## Architectural decisions
[2026-05-04] Use `age` CLI binary (subprocess) for storageState encryption, not pure-Python age.
  Rationale: age binary is battle-tested, widely available on Linux VPS, avoids maintaining crypto code.
  Alternative: pyage (rejected — immature, not audited).

[2026-05-04] KDP UI selectors are placeholders marked `# VERIFY_SELECTOR`.
  Rationale: Cannot validate selectors against live KDP UI in sandboxed session. Operator must run
  `python scripts/kdp_login.py --account=X --verify-selectors` on first real run.

[2026-05-04] Worker uses RQ (redis-queue) not Celery.
  Rationale: SPEC.md §4 specifies RQ on Python side. Simpler ops, no Celery beat needed (scheduler
  is a systemd timer). Celery rejected for over-engineering at this scale.

## Tasks

### T2.1 — kdp-client: package structure + dependencies ✅ / ⏳ / ❌
**Estimated tokens:** 8k
**Dependencies:** M1 complete
**Acceptance:** `uv sync` in kdp-client package succeeds; all module files importable

Add to `packages/kdp-client/pyproject.toml`:
- playwright>=1.48.0, playwright-stealth>=1.0.6
- prisma>=0.15.0 (prisma-client-py)
- rq>=1.16.0, redis>=5.0.0
- cryptography>=42.0.0
- aiohttp>=3.9.0
- loguru>=0.7.0, pydantic>=2.0.0

Create directory skeleton:
```
packages/kdp-client/
  colorforge_kdp/
    __init__.py
    exceptions.py   (T2.2)
    types.py        (T2.2)
    browser.py      (T2.3)
    storage.py      (T2.4)
    quota.py        (T2.5)
    publisher.py    (T2.6)
    scraper.py      (T2.7)
  tests/
    __init__.py
    test_browser.py   (T2.9)
    test_storage.py   (T2.9)
    test_quota.py     (T2.9)
    test_publisher.py (T2.9)
    test_scraper.py   (T2.9)
  pyproject.toml
```

---

### T2.2 — kdp-client: exceptions + domain types
**Estimated tokens:** 8k
**Dependencies:** T2.1
**Acceptance:** `mypy --strict colorforge_kdp/exceptions.py colorforge_kdp/types.py` clean

`exceptions.py`:
- `ColorforgeKDPError(Exception)` — base
- `QuotaExceeded(ColorforgeKDPError)` — fields: account_id, limit, current_count
- `SelectorMissing(ColorforgeKDPError)` — fields: selector, step, screenshot_path
- `LoginRequired(ColorforgeKDPError)` — fields: account_id, redirect_url
- `PublishStepFailed(ColorforgeKDPError)` — fields: step, book_id, reason, screenshot_path
- `StorageStateError(ColorforgeKDPError)` — fields: path, reason
- `CaptchaDetected(ColorforgeKDPError)` — fields: url, screenshot_path
- `ScraperRateLimitExceeded(ColorforgeKDPError)`

`types.py` (Pydantic v2):
- `Fingerprint`: user_agent, viewport (w/h), locale, timezone_id, screen (w/h)
- `ProxyConfig`: server, username, password
- `AccountRecord`: id, label, proxy_config, fingerprint, storage_state_encrypted_path, daily_quota, created_at, account_age_days (property)
- `CompetitorSnap`: rank, asin, title, author, price_usd, review_count, cover_url, bsr_category (mirrors Zod contract in packages/shared)
- `PublishStep` (IntEnum): NAVIGATE=1, BOOK_DETAILS=2, KEYWORDS_CATEGORIES=3, UPLOAD_INTERIOR=4, UPLOAD_COVER=5, PRICING=6, REVIEW=7, SUBMIT=8
- `PublishJobState`: book_id, account_id, last_completed_step (Optional[PublishStep]), asin (Optional[str])

---

### T2.3 — kdp-client: multi-account browser context manager
**Estimated tokens:** 20k
**Dependencies:** T2.2
**Acceptance:** unit test with AsyncMock playwright confirms context created with correct proxy/fingerprint/storageState params

`browser.py`:
```python
class AccountBrowserManager:
    def __init__(self, account: AccountRecord, storage_dir: Path, age_key_path: Path): ...
    async def __aenter__(self) -> tuple[BrowserContext, Page]: ...
    async def __aexit__(self, *args) -> None: ...
    async def _detect_login_expiry(self, page: Page) -> None: ...  # raises LoginRequired if redirected to login
```

- Decrypts storageState to tmpfs before launching (calls storage.decrypt_storage_state)
- Passes proxy, UA, viewport, locale, timezone, screen to `browser.new_context()`
- Calls `stealth_async(page)` after page creation
- Detects login expiry: if page URL contains "signin" after navigation → raises LoginRequired
- On exit: saves updated storageState back (re-encrypts)

---

### T2.4 — kdp-client: storageState encryption + login CLI
**Estimated tokens:** 20k
**Dependencies:** T2.2
**Acceptance:** encrypt + decrypt roundtrip test passes with dummy JSON; `scripts/kdp_login.py --help` prints usage

`storage.py`:
```python
async def encrypt_storage_state(state_path: Path, age_pubkey: str, dest: Path) -> None: ...
async def decrypt_storage_state(encrypted: Path, age_key: Path, tmpfs_dir: Path) -> Path: ...
def is_storage_valid(state_path: Path) -> bool: ...  # parses JSON, checks for "cookies" key
```

- encrypt: `subprocess.run(["age", "--recipient", pubkey, "--output", dest, state_path])`
- decrypt: `subprocess.run(["age", "--decrypt", "--identity", key, "--output", out, encrypted])`
- Both raise StorageStateError on non-zero returncode

`scripts/kdp_login.py`:
- CLI: `--account=LABEL --accounts-config=PATH --age-pubkey=KEY [--verify-selectors]`
- Opens headed Playwright browser (no proxy, no stealth — for manual use)
- Navigates to kdp.amazon.com
- Waits for operator to complete login manually
- On URL change to bookshelf: saves storageState, encrypts, confirms to operator

---

### T2.5 — kdp-client: quota enforcement
**Estimated tokens:** 12k
**Dependencies:** T2.2
**Acceptance:** mock Prisma test — 5 books today raises QuotaExceeded during 60d ramp; 6th on day 61 succeeds (limit=10)

`quota.py`:
```python
async def check_and_consume_quota(account: AccountRecord, prisma) -> None: ...
async def get_today_publish_count(account_id: str, prisma) -> int: ...
def get_daily_limit(account: AccountRecord) -> int: ...  # 5 if <60 days, else 10
```

- `get_today_publish_count`: counts books with state IN ['publishing','live'] and updatedAt >= today 00:00 UTC
- `check_and_consume_quota`: get count, compare to limit, raise QuotaExceeded if >=limit
- Note: "consume" is checked-only here — actual quota is enforced by DB state changes in Publisher

---

### T2.6 — kdp-client: KDP publisher (8-step atomic/resumable flow) ⚠️ CRITICAL PATH
**Estimated tokens:** 45k
**Dependencies:** T2.3, T2.4, T2.5
**Acceptance:** mock test — step 3 failure + resume from step 3 works; ASIN extracted after step 8

`publisher.py`:
```python
class KDPPublisher:
    def __init__(self, page: Page, job_state: PublishJobState, assets_dir: Path, prisma): ...
    async def publish(self, listing: ListingData, book_draft: BookDraftData) -> str: ...  # returns ASIN
    async def _execute_step(self, step: PublishStep, fn: Callable) -> None: ...
    async def _load_last_step(self) -> Optional[PublishStep]: ...  # reads book_events from DB
    async def _save_step(self, step: PublishStep) -> None: ...  # writes book_events to DB
    async def _screenshot(self, step: PublishStep) -> Path: ...
```

Step implementations (all selectors marked `# VERIFY_SELECTOR`):
1. `_step_navigate`: go to `https://kdp.amazon.com/title/new`, click "Paperback" radio  
2. `_step_book_details`: fill title, subtitle, author, series, description textarea; click AI disclosure YES radio
3. `_step_keywords_categories`: fill 7 keyword inputs; select 2 BISAC categories  
4. `_step_upload_interior`: `input[type=file][name=interior]` file upload; wait for "Upload successful" text
5. `_step_upload_cover`: `input[type=file][name=cover]` file upload; wait for confirmation
6. `_step_pricing`: fill price inputs (USD/EUR/GBP); select "60% royalty" radio
7. `_step_review`: click "Save and Continue" or "Launch Previewer"; wait for next page
8. `_step_submit`: click "Publish Your Paperback Book"; extract ASIN from confirmation URL or page

Human-like behavior:
- `await page.mouse.move(x, y)` before every click (random offset)
- `await page.type(sel, text, delay=random.randint(60, 120))`
- `await asyncio.sleep(random.uniform(1.5, 4.0))` between steps

---

### T2.7 — kdp-client: Amazon Bestsellers scraper
**Estimated tokens:** 25k
**Dependencies:** T2.2, T2.3
**Acceptance:** mock HTML test extracts 20 CompetitorSnap records with correct fields

`scraper.py`:
```python
class AmazonScraper:
    def __init__(self, page: Page, rate_limit: int = 200): ...  # pages/hour
    async def scrape_bestsellers(self, category_url: str, max_pages: int = 5) -> list[CompetitorSnap]: ...
    async def _extract_page(self, page_num: int) -> list[CompetitorSnap]: ...
    async def _detect_captcha(self) -> None: ...  # raises CaptchaDetected
```

- Paginates via `?pg=N` query param
- Extracts per book: rank (`#zg-rank`), ASIN (from URL), title, author, price, review count, cover URL
- All selectors marked `# VERIFY_SELECTOR`
- Rate: tracks pages/hour via deque timestamps; sleeps if approaching limit
- Human delays: `random.uniform(2.0, 5.0)` between pages

---

### T2.8 — worker process: RQ worker + job handlers
**Estimated tokens:** 20k
**Dependencies:** T2.5, T2.6, T2.7
**Acceptance:** `python apps/worker/run_worker.py --dry-run` exits 0; mypy --strict on all worker modules

`apps/worker/colorforge_worker/`:
- `worker.py`: RQ `Worker([q_publish, q_scrape], connection=redis_conn)` setup; graceful SIGTERM
- `jobs/publish.py`: `handle_publish_job(book_id: str, account_id: str) -> dict`
  - Fetches Account from DB, creates AccountBrowserManager, checks quota, runs KDPPublisher
  - Returns `{asin, book_id, duration_s}`
- `jobs/scrape.py`: `handle_scrape_job(category_url: str, account_id: str, niche_id: str) -> dict`
  - Fetches Account from DB, creates AmazonScraper, stores CompetitorSnap list to DB
  - Returns `{niche_id, count}`
- `health.py`: aiohttp GET /health → `{"status": "ok", "queues": {...}}`
- `run_worker.py`: entrypoint, `--dry-run` flag validates imports + Redis connection

`apps/worker/pyproject.toml`: add colorforge-kdp-client (local path dep), rq, redis, aiohttp, loguru

---

### T2.9 — full test suite (mocked Playwright)
**Estimated tokens:** 30k
**Dependencies:** T2.1–T2.8
**Acceptance:** `make test` green; coverage >80% on publisher.py and quota.py

Test files:
- `packages/kdp-client/tests/test_storage.py` — encrypt/decrypt roundtrip (subprocess mock + real JSON)
- `packages/kdp-client/tests/test_quota.py` — QuotaExceeded at limit, pass under limit, 60d boundary
- `packages/kdp-client/tests/test_browser.py` — context created with correct params (AsyncMock)
- `packages/kdp-client/tests/test_publisher.py` — step execution, resumption from step 3, ASIN capture
- `packages/kdp-client/tests/test_scraper.py` — HTML fixture extraction
- `apps/worker/tests/test_jobs.py` — job handler stubs (mock KDPPublisher + AmazonScraper)

## Token budget tracking
| Task | Estimated | Actual |
|------|-----------|--------|
| T2.1 | 8k | — |
| T2.2 | 8k | — |
| T2.3 | 20k | — |
| T2.4 | 20k | — |
| T2.5 | 12k | — |
| T2.6 | 45k | — |
| T2.7 | 25k | — |
| T2.8 | 20k | — |
| T2.9 | 30k | — |
| **Total** | **188k** | — |
| **Budget** | **200k** | |
