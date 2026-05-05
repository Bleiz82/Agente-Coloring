# Milestone 3 — Niche Hunter + Deep Scout

**Status:** Complete
**Owner:** architect (planning) → implementer (execution) → tester (verification)
**Token budget:** 200k
**Branch:** main (continuing)

## Scope (from SPEC.md §3, §7)
Build the first two agents in the pipeline: Niche Hunter (scrapes Amazon + Trends, computes Profitability Score, writes NicheCandidate to DB) and Deep Scout (enriches top-K candidates with pain points via Claude, style classification via vision, Qdrant embeddings — writes NicheBrief). Also implements the Niche Gate.

## Acceptance criteria (whole milestone)
- [x] `apps/agents` installs cleanly (`uv sync`)
- [x] `compute_profitability_score()` produces correct weighted total for known inputs
- [x] NicheHunterAgent runs with mock AmazonScraper + mock Trends, writes NicheCandidate to DB
- [x] DeepScoutAgent runs with mock Claude + mock Qdrant, writes NicheBrief to DB
- [x] NicheGate correctly passes/blocks briefs against dynamic threshold
- [x] `python scripts/run_niche_hunt.py --dry-run` exits 0
- [x] mypy --strict + ruff passing on all M3 modules
- [x] >80% coverage on scoring and gate (deterministic logic)
- [x] All external API calls (Claude, Trends, Qdrant) behind injectable interfaces (mockable in tests)

## Architectural decisions
[2026-05-04] sentence-transformers `all-MiniLM-L6-v2` for Qdrant embeddings (local, free).
  Rationale: Anthropic doesn't offer embeddings API. Local model avoids per-call cost.
  Alternative: OpenAI embeddings (rejected — adds vendor dependency).

[2026-05-04] pytrends for Google Trends (unofficial). Graceful degradation to 0.0 if unavailable.
  Rationale: Only official option is Google Trends API (enterprise). pytrends is widely used.
  Risk: rate limits. Mitigated by Redis cache with 6h TTL + exponential backoff.

[2026-05-04] Pinterest Trends via Playwright scrape of trends.pinterest.com.
  Rationale: No public API. Scrape is lightweight (single page, no login needed).
  Fallback: return None if scrape fails (signal weight 0.10, not critical).

[2026-05-04] CrewAI agents kept thin — pure orchestration wrappers around domain logic.
  Rationale: Business logic in plain async classes (NicheHunterCore, DeepScoutCore) is
  testable without CrewAI. CrewAI agents delegate to core classes.

[2026-05-04] Claude Sonnet 4.6 for pain point extraction AND style classification.
  Rationale: Same model specified in SPEC for Critic. Reuse. Vision for cover style,
  text for review pain points.

## Tasks

### T3.1 — agents package: deps + module skeleton
**Estimated tokens:** 8k
**Dependencies:** M2 complete
**Acceptance:** `python -c "import colorforge_agents"` succeeds

Update `apps/agents/pyproject.toml`:
```toml
dependencies = [
    "crewai>=0.80.0",
    "anthropic>=0.40.0",
    "pytrends>=4.9.2",
    "qdrant-client>=1.11.0",
    "sentence-transformers>=3.0.0",
    "prisma>=0.15.0",
    "redis>=5.0.0",
    "playwright>=1.48.0",
    "loguru>=0.7.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
]
```

Create skeleton:
```
apps/agents/colorforge_agents/
  scoring/
    __init__.py
    profitability.py     (T3.2)
  trends/
    __init__.py
    google.py            (T3.3)
    pinterest.py         (T3.3)
  niche_hunter/
    __init__.py
    hunter.py            (T3.4)
  deep_scout/
    __init__.py
    scout.py             (T3.5)
    review_scraper.py    (T3.5)
    llm_analyzer.py      (T3.5)
    embedder.py          (T3.5)
  gates/
    __init__.py
    niche_gate.py        (T3.6)
  crew.py                (T3.7)
  exceptions.py          (T3.1)
tests/
  test_scoring.py        (T3.8)
  test_niche_gate.py     (T3.8)
  test_hunter.py         (T3.8)
  test_scout.py          (T3.8)
```

---

### T3.2 — Profitability Score engine (CRITICAL PATH)
**Estimated tokens:** 20k
**Dependencies:** T3.1
**Acceptance:** `compute_profitability_score(known_inputs)` matches expected output within 0.01

`colorforge_agents/scoring/profitability.py`:

Signal weights (from SPEC §7):
- demand: 0.20 (inverse median BSR / 100k, capped)
- price: 0.15 (median price normalized to $4-$15)
- competition: 0.20 NEGATIVE (fraction of books with <50 reviews)
- quality_gap: 0.15 (count of severe pain points, normalized 0-10)
- trend: 0.10 (google_trends_90d_slope normalized -1..1 → 0..1)
- seasonality_fit: 0.05 (1.0 if peak ≤30 days away, 0.5 if 30-60d, 0.0 if >60d)
- catalog_fit: 0.10 (cosine similarity 0-1, passed in directly)
- saturation_velocity: 0.05 NEGATIVE (new_pubs_30d normalized against 90d dist)

`ScoreInputs` Pydantic model:
- median_bsr: int
- median_price: float
- low_review_book_count: int  # books with <50 reviews in top 20
- total_top_books: int        # denominator for competition signal
- severe_pain_point_count: int
- google_trends_90d_slope: float
- days_to_peak_season: int    # 0 = now, 999 = no seasonality
- catalog_fit_cosine: float   # 0.0 default if no winners yet
- new_pubs_last_30d: int
- new_pubs_30d_p90: int       # 90th percentile across all niches (for normalization)

`compute_profitability_score(inputs: ScoreInputs) -> ProfitabilityBreakdown`
- Returns ProfitabilityBreakdown (from existing contracts/niche_candidate.py)
- Each signal clamped to [0, 1]
- weighted_total = sum(weight_i * signal_i) * 100

---

### T3.3 — Google Trends + Pinterest Trends client
**Estimated tokens:** 20k
**Dependencies:** T3.1
**Acceptance:** mock test verifies slope extraction; Redis cache hit path tested

`colorforge_agents/trends/google.py`:
```python
class GoogleTrendsClient:
    def __init__(self, redis_client, cache_ttl: int = 21600): ...  # 6h TTL
    async def get_90d_slope(self, keyword: str) -> float: ...
    # Uses pytrends.TrendReq, returns linear regression slope of last 90 days
    # Returns 0.0 on any error (graceful degradation)
    # Caches result in Redis key "trends:google:{keyword}" with TTL
```

`colorforge_agents/trends/pinterest.py`:
```python
class PinterestTrendsClient:
    def __init__(self, redis_client, cache_ttl: int = 21600): ...
    async def get_search_velocity(self, keyword: str) -> float | None: ...
    # Scrapes trends.pinterest.com/explore/{keyword} via httpx (no JS needed)
    # Extracts monthly search count from JSON in page source
    # Returns None on failure
```

---

### T3.4 — Niche Hunter agent
**Estimated tokens:** 35k
**Dependencies:** T3.2, T3.3
**Acceptance:** mock test — 2 categories → 2 NicheCandidate rows written to mock Prisma with correct scores

`colorforge_agents/niche_hunter/hunter.py`:

```python
class NicheHunterConfig(BaseModel):
    categories: list[str]          # Amazon category URLs to scan
    freshness_threshold_hours: int = 23  # skip if scanned in last N hours
    top_k: int = 5                 # how many to pass to Deep Scout
    max_competitors: int = 20

class NicheHunterCore:
    """Pure business logic — no CrewAI. Injected scraper + trends clients."""
    def __init__(self, scraper, trends_google, trends_pinterest, prisma): ...
    async def run(self, config: NicheHunterConfig) -> list[NicheCandidate]: ...
    async def _scan_category(self, category_url: str) -> NicheCandidate | None: ...
    async def _compute_score(self, competitors, trends) -> ProfitabilityBreakdown: ...
    async def _write_to_db(self, candidate: NicheCandidate, run_id: str) -> str: ...

class NicheHunterAgent:
    """CrewAI wrapper around NicheHunterCore."""
    def __init__(self, core: NicheHunterCore): ...
    def as_crewai_agent(self): ...  # returns crewai.Agent
    def as_crewai_task(self, config: NicheHunterConfig): ...  # returns crewai.Task
```

---

### T3.5 — Deep Scout agent (Claude vision + Qdrant)
**Estimated tokens:** 45k
**Dependencies:** T3.2, T3.1
**Acceptance:** mock test — 1 NicheCandidate → NicheBrief written with ≥1 pain point + ≥1 style

Submodules:

`colorforge_agents/deep_scout/review_scraper.py`:
- `scrape_low_rated_reviews(asin: str, page: Page, max_reviews: int = 50) -> list[dict]`
- Navigates to Amazon reviews filtered by 1-2 stars
- Returns list of {text, rating, review_id}

`colorforge_agents/deep_scout/llm_analyzer.py`:
- `LLMAnalyzer` class with injected `anthropic.AsyncAnthropic` client
- `async def extract_pain_points(reviews: list[dict]) -> list[PainPoint]`
  - Sends batch of review texts to Claude Sonnet 4.6
  - System prompt instructs structured extraction
  - Parses JSON response into PainPoint list
- `async def classify_cover_styles(cover_urls: list[str]) -> list[StyleClassification]`
  - Downloads cover images (httpx), sends to Claude vision
  - Returns StyleClassification list
- `async def suggest_differentiators(pain_points, styles) -> list[Differentiator]`
  - Single Claude call combining pain points + styles

`colorforge_agents/deep_scout/embedder.py`:
- `NicheEmbedder` class with injected `qdrant_client.AsyncQdrantClient`
- `async def embed_and_store(brief: NicheBrief) -> str`
  - Uses sentence-transformers `all-MiniLM-L6-v2` to embed primary_keyword + pain points summary
  - Upserts vector to Qdrant collection "niches" with niche_id as point ID
  - Returns qdrant_vector_id

`colorforge_agents/deep_scout/scout.py`:
- `DeepScoutCore`: orchestrates review_scraper + llm_analyzer + embedder
- `DeepScoutAgent`: CrewAI wrapper

---

### T3.6 — Niche Gate
**Estimated tokens:** 12k
**Dependencies:** T3.2
**Acceptance:** test — passes above threshold, blocks below, fallback 50.0 when no history

`colorforge_agents/gates/niche_gate.py`:
```python
class NicheGate:
    FALLBACK_THRESHOLD = 50.0

    async def compute_threshold(self, prisma) -> float:
        # Query niches table: get profitabilityScore of niches linked to winner books
        # Winner = books with successScore classification = "winner"
        # Return median. Fallback to 50.0 if <5 data points.
        ...

    async def passes(self, brief: NicheBrief, prisma) -> tuple[bool, float]:
        # Returns (passes: bool, threshold: float)
        ...
```

---

### T3.7 — CrewAI crew + daily run entrypoint
**Estimated tokens:** 15k
**Dependencies:** T3.4, T3.5, T3.6
**Acceptance:** `python scripts/run_niche_hunt.py --dry-run` exits 0

`colorforge_agents/crew.py`:
- `NicheHuntCrew`: CrewAI Crew with NicheHunterAgent + DeepScoutAgent
- `async def run(config: NicheHunterConfig) -> list[NicheBrief]`

`scripts/run_niche_hunt.py`:
- CLI: `--dry-run`, `--config-file`, `--categories` (comma-separated URLs)
- Loads config from env/file, instantiates clients, runs crew
- `--dry-run`: validates imports + config + DB connection, exits 0

---

### T3.8 — Full test suite
**Estimated tokens:** 35k
**Dependencies:** T3.1–T3.7
**Acceptance:** pytest green, >80% coverage on scoring.py and niche_gate.py

Test files:
- `tests/test_scoring.py` — 8 signals, weighted total, edge cases
- `tests/test_niche_gate.py` — threshold, pass/fail, fallback
- `tests/test_hunter.py` — mock scraper + trends, DB writes
- `tests/test_scout.py` — mock Claude + Qdrant, NicheBrief construction
- `tests/test_trends.py` — mock pytrends + httpx, cache hit/miss

## Token budget tracking
| Task | Estimated | Actual |
|------|-----------|--------|
| T3.1 | 8k | ✅ |
| T3.2 | 20k | ✅ |
| T3.3 | 20k | ✅ |
| T3.4 | 35k | ✅ |
| T3.5 | 45k | ✅ |
| T3.6 | 12k | ✅ |
| T3.7 | 15k | ✅ |
| T3.8 | 35k | ✅ |
| **Total** | **190k** | — |
| **Budget** | **200k** | |
