# Milestone 5 — SEO Listing + Publisher Integration

**Status:** Complete
**Owner:** architect (planning) → implementer (execution) → tester (verification)
**Token budget:** 250k
**Branch:** main (continuing)

## Scope (from SPEC.md §3.2, §3.3, §9)

Build two agents and one gate:
- **SEO Listing**: consumes NicheBrief + BookDraft → ListingContract (title, subtitle, 7 keywords,
  HTML description, BISAC codes, prices). Uses Claude Sonnet 4.6 for content generation.
- **Listing Gate**: validates ListingContract before publishing (no trademarks, no bestseller claims,
  length limits, BISAC format, price range). Synchronous, deterministic.
- **Publisher agent**: bridges ListingContract + BookDraft + AccountRecord → KDPPublisher (M2).
  Handles quota enforcement, DB state transitions (LISTING → PUBLISHING → LIVE), ASIN capture.

## Acceptance criteria (whole milestone)

- [x] `SEOListingCore.generate(brief, draft, plan)` returns a valid `ListingContract`
- [x] `ListingGate.passes(listing)` raises `ListingGateBlocked` on blocked content and returns `(True, [])` otherwise
- [x] `PublisherAgent.publish(listing, draft, account)` calls `KDPPublisher` and returns ASIN
- [x] `PublisherAgent` respects quota via `check_and_consume_quota()` before publishing
- [x] `python scripts/run_publish.py --dry-run` exits 0
- [x] mypy --strict + ruff passing on all M5 modules
- [x] >80% coverage on listing_gate.py (deterministic logic)

## Architectural decisions

[2026-05-06] SEO Listing uses Claude Sonnet 4.6 with structured JSON response for title/subtitle/keywords/description.
  Rationale: template-only produces generic SEO; Claude understands long-tail keyword placement,
  emotional triggers, and KDP-specific formatting constraints better than static templates.
  Fallback: if Claude call fails, construct minimal listing from NicheBrief fields.

[2026-05-06] Listing Gate is synchronous (no DB, no LLM) — all checks are deterministic string operations.
  Trademark blocklist hardcoded for M5 (43 terms). M6 will expose an operator-editable DB table.
  BISAC code format validated by regex `^[A-Z]{3}\d{6}$` (covers all current KDP BISAC codes).
  Price range: $2.99 ≤ price_usd ≤ $24.99 (KDP coloring book practical range, not KDP hard limits).

[2026-05-06] PublisherAgent is a thin orchestrator — it does NOT replicate KDPPublisher logic.
  Sequence: ContentGate check → ListingGate check → quota check → map contracts → browser session →
  KDPPublisher.publish() → DB state transition → return ASIN.

[2026-05-06] Author name split: `brand_author` full name split on first space.
  If no space, first="" last=brand_author (handles single-name authors).

[2026-05-06] Price EUR/GBP fallback: if None in ListingContract, compute EUR = USD × 0.93, GBP = USD × 0.79.
  These constants match KDP's default currency conversion for fresh listings.

## KDP Listing Field Constraints (locked reference)

- Title: 1–200 chars, no ALL-CAPS words >5 chars, no trademarked terms
- Subtitle: 0–200 chars, same restrictions
- Keywords: exactly 7, each ≤50 chars, no duplicates within the 7
- Description HTML: ≤4000 chars, KDP-allowed tags: <b>, <i>, <em>, <strong>, <br>, <ul>, <li>
- BISAC codes: 1–3 codes, format `^[A-Z]{3}\d{6}$`
- Price USD: $2.99–$24.99 (practical coloring book range)
- AI disclosure: always True (non-negotiable per SPEC.md §2)

## Tasks

### T5.1 — M5 exceptions + plan
**Estimated tokens:** 5k
**File:** `apps/agents/colorforge_agents/exceptions.py` (append)
**New exceptions:**
- `ListingGenerationError` — Claude call or JSON parse failure in SEO agent
- `ListingGateBlocked(book_id, failed_checks: list[str])` — listing blocked by gate
- `PublisherAgentError` — publisher orchestration failure (not a KDP step failure)

### T5.2 — SEO Listing agent
**Estimated tokens:** 40k
**Files:**
- `apps/agents/colorforge_agents/seo/__init__.py`
- `apps/agents/colorforge_agents/seo/listing_agent.py`

**Class:** `SEOListingCore(client: Any, prisma: Any)`
- `async generate(brief: NicheBrief, draft: BookDraft, plan: BookPlan) -> ListingContract`
- `async _call_claude(prompt: str) -> dict[str, Any]`
- `_build_prompt(brief, draft, plan) -> str`
- `_parse_response(raw: str, book_id: str, plan: BookPlan) -> ListingContract`
- `_fallback_listing(brief, draft, plan) -> ListingContract` (no Claude, template-based)
- `async _save_to_db(listing: ListingContract, run_id: str) -> None`

**Claude prompt strategy:**
  System: "You are a KDP coloring book SEO specialist. Generate listing metadata as JSON."
  User: NicheBrief pain points + style + differentiators + page count + target keyword
  Response JSON: `{title, subtitle, keywords: [7], description_html, bisac_codes: [1-3], price_usd}`

### T5.3 — Listing Gate
**Estimated tokens:** 20k
**File:** `apps/agents/colorforge_agents/gates/listing_gate.py`

**Class:** `ListingGate`
- `def passes(listing: ListingContract) -> tuple[bool, list[str]]` — raises `ListingGateBlocked`
- `def _check_trademarks(text: str) -> list[str]`
- `def _check_bestseller_claims(text: str) -> list[str]`
- `def _check_lengths(listing) -> list[str]`
- `def _check_bisac(listing) -> list[str]`
- `def _check_price(listing) -> list[str]`
- `def _check_keywords(listing) -> list[str]`

**Blocklist (43 terms, M5 hardcoded):**
  disney, marvel, pokemon, pikachu, harry potter, star wars, minecraft, roblox, fortnite,
  peppa pig, paw patrol, bluey, cocomelon, hello kitty, barbie, batman, superman, spiderman,
  spider-man, frozen, moana, encanto, lilo, stitch, winnie the pooh, snoopy, garfield,
  looney tunes, sesame street, dora, bluey, thomas the tank, peppa, lego (in trademark context),
  nintendo, playstation, xbox, coca-cola, adidas, nike, gucci, louis vuitton, chanel

**Bestseller claim patterns (regex, case-insensitive):**
  `#1 best`, `number one`, `bestselling`, `best-selling`, `amazon's choice`, `top seller`,
  `most popular`, `award winning`, `award-winning`

### T5.4 — Publisher agent
**Estimated tokens:** 35k
**Files:**
- `apps/agents/colorforge_agents/publisher/__init__.py`
- `apps/agents/colorforge_agents/publisher/publisher_agent.py`

**Dataclass:** `PublisherResult(book_id: str, asin: str, account_id: str)`

**Class:** `PublisherAgent(content_gate: ContentGate, listing_gate: ListingGate, prisma: Any, assets_base: Path)`
- `async publish(listing: ListingContract, draft: BookDraft, account: AccountRecord, report: ValidationReport) -> PublisherResult`
- `_map_listing(listing: ListingContract, author: str) -> ListingData`
- `_map_draft(draft: BookDraft) -> BookDraftData`
- `_split_author(brand_author: str) -> tuple[str, str]`
- `async _transition_state(book_id: str, from_state: str, to_state: str, reason: str) -> None`
- `async _write_asin(book_id: str, asin: str) -> None`

**Sequence:**
1. `content_gate.passes(report)` — raises `ContentGateBlocked` if not
2. `listing_gate.passes(listing)` — raises `ListingGateBlocked` if not
3. `check_and_consume_quota(account, prisma)` — raises `QuotaExceeded` if not
4. `_transition_state(book_id, "LISTING", "PUBLISHING", "publisher_agent_start")`
5. `async with AccountBrowserManager(account, prisma=prisma) as (ctx, page)`
6. Build `PublishJobState(book_id, account_id, last_completed_step=None)`
7. `KDPPublisher(page, job_state, assets_dir, prisma).publish(listing_data, draft_data)`
8. `_write_asin(book_id, asin)`
9. `_transition_state(book_id, "PUBLISHING", "LIVE", f"asin={asin}")`
10. Return `PublisherResult(book_id, asin, account.id)`

### T5.5 — scripts/run_publish.py
**Estimated tokens:** 8k
**File:** `scripts/run_publish.py`
- `--dry-run`: validates imports + env vars, exits 0
- `--book-id UUID`: full pipeline run (raises NotImplementedError pending M5 DB wiring)

### T5.6 — Full test suite + make check green
**Estimated tokens:** 50k
**New test files:**
- `apps/agents/tests/test_listing_gate.py` (≥16 tests, covers all 6 check types + edge cases)
- `apps/agents/tests/test_seo_listing.py` (≥10 tests, mock Claude client)
- `apps/agents/tests/test_publisher_agent.py` (≥12 tests, mock KDPPublisher + quota + gates)
