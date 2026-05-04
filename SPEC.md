# ColorForge AI — Master Specification Document

**Version:** 1.0
**Owner:** Stefano (DigIdentity Agency)
**Last updated:** 2026-04-29
**Status:** Pre-implementation, locked for M1 kickoff

## 0. How to use this document

This is the single source of truth for the ColorForge AI system. It lives in the repo as SPEC.md and must be referenced by every Claude Code session. When something contradicts this document, this document wins unless explicitly amended via a versioned changelog at the bottom.

The document is structured top-down: mission and constraints first, then architecture, then the contracts each component must respect, then the data model, then operational concerns. Implementation details that are not architecturally relevant are deliberately left to milestone-level prompts.

Read sections 1-4 once to internalize. Sections 5-9 are reference material to consult on demand.

## 1. Mission and success criteria

ColorForge AI is a self-improving multi-agent system that researches profitable Amazon KDP coloring book niches, generates production-quality books end-to-end, publishes them across multiple seller accounts, monitors real sales performance, and evolves its own strategy over time based on observed outcomes.

The system targets a measurable outcome: lifting the user's current 5% hit rate (1 winner per 20 books) to 15% or higher within 90 days of full operation, while scaling output to 250 books per month distributed across 3 KDP accounts. Success is measured exclusively by net profit per published book over a rolling 30-day window, not by volume or vanity metrics.

The system is owned, hosted, and operated by a single technical user. It must be runnable on a single VPS with Postgres+Redis+Qdrant in Docker, with all secrets locally controlled, and must never depend on third-party SaaS for core logic (only for commodity APIs: Gemini, Claude, proxy provider).

## 2. Hard constraints

These are non-negotiable and bind every implementation decision.

**Compliance.** Every published book must declare AI-generated content via the KDP disclosure flag. The system never bypasses Amazon checks, never spoofs identity, never operates accounts not legally owned by the operator. Multi-account is limited to legitimate family/business accounts with proper tax separation.

**Account safety.** Each KDP account runs in a dedicated isolated browser context with its own persistent storageState, dedicated residential proxy from the account's resident country, and stable browser fingerprint. Accounts never share cookies, IP, or fingerprint. Publishing rate is capped at 5 books/day/account for the first 60 days of system operation, scaling to 10/day only after 60 days of clean history.

**Quality gates.** No book reaches the Publisher agent without passing three validation gates: niche profitability gate, content quality gate (independent Critic with vision), listing compliance gate. Failed books are either regenerated (max 2 retries) or killed and logged. The system has the courage to publish nothing on a given day if nothing meets quality bar.

**Token economy.** Architectural decisions, debugging of stuck cases, and code review of critical-path code are reserved for Opus 4.7. All routine implementation, test writing, refactoring, and boilerplate is delegated to Opus 4.6 via subagents. This delegation is enforced by the agents configuration in .claude/agents/.

**Observability.** Every agent invocation, every API call, every gate decision, every prompt version is logged with structured JSON to a queryable store. Nothing in the system is a black box; if a book fails, you can reconstruct exactly why in under 5 minutes.

**Killswitch.** A single command (python kill.py) halts every agent, every browser context, every queued job within 10 seconds. This is tested in CI.

## 3. System architecture

### 3.1 High-level topology

The system runs as four cooperating processes on a single VPS, communicating via Redis (job queue) and Postgres (shared state):

**The agents process** (Python) hosts the seven AI agents orchestrated by CrewAI. It consumes jobs from Redis queues and writes outcomes to Postgres. Each agent runs in its own asyncio task pool to maximize parallelism where the workload allows.

**The worker process** (Python) handles long-running browser automation: KDP scraping, KDP publishing, Amazon scraping. It is separated from the agents process because Playwright is memory-heavy and benefits from independent restart cycles.

**The dashboard process** (Next.js 14) serves the UI and tRPC API. It is read-mostly: the only writes it does are user-triggered actions (approve a book, kill a book, schedule a niche, promote a policy).

**The scheduler** (a thin systemd timer + Python entrypoint) triggers daily/weekly cycles: niche hunt at 02:00, performance monitor at 03:00, weekly retrospective on Sundays.

All processes share Postgres for structured data, Qdrant for vector memory, Redis for queue/cache. Asset files (PDFs, images) live on the VPS filesystem under /var/colorforge/assets/{account}/{book_id}/ with daily backup to S3-compatible storage.

### 3.2 The seven agents and their contracts

Each agent has a strict input/output contract validated by Pydantic schemas. Agents never call each other directly; they communicate by writing to Postgres and enqueueing jobs in Redis. This keeps them independently testable, retryable, and replaceable.

**Niche Hunter** consumes a configuration record (which categories to scan, freshness threshold) and produces N NicheCandidate records in Postgres with computed Profitability Score. It runs daily, scrapes Amazon Bestsellers via Playwright, queries Google Trends and Pinterest Trends, and writes raw observations alongside computed scores so future scoring algorithm changes can be replayed against historical data.

**Deep Scout** consumes the top-K NicheCandidate records (where K is configurable, default 5) and enriches each with a NicheBrief: deep competitor analysis (top 20 books per niche with full metadata), pain points extracted from 1-2 star reviews via LLM analysis, dominant visual styles classified via Vision API, suggested differentiators. Output is a structured JSON written to the niche_briefs table and embedded into Qdrant.

**Strategist** consumes one or more NicheBrief records plus the current state of all 3 KDP accounts (catalog coherence, recent publications, brand author identity) and produces BookPlan records: which account publishes which niche today, with which style, page count, target price, target keyword. The Strategist consults policy memory and the historical winners archive before deciding. It can decide to publish nothing if no plan crosses the profitability gate threshold.

**Generator** consumes a BookPlan and produces a BookDraft with manuscript PDF, cover PDF, and per-page metadata (prompt used, generation timestamp, validation flags). It calls Gemini 3.1 Flash Image with rate-limited concurrency, post-processes images via Pillow (grayscale conversion, contrast normalization, 300 DPI enforcement, artifact detection), and assembles PDFs via ReportLab using KDP-compliant specs (8.5x11" trim, 0.125" bleed, 0.375" gutter margin).

**Critic** consumes a BookDraft and produces a ValidationReport. It uses Claude Sonnet 4.6 with vision (intentionally a different vendor than the Generator to eliminate auto-confirmation bias). It checks every page for line-art quality, AI artifacts, text contamination; checks the cover for thumbnail readability at 200px; checks PDF specs against KDP requirements. Failed pages are flagged for regeneration; books with too many failures are killed.

**SEO Listing** consumes a validated BookDraft plus the originating NicheBrief and produces a Listing record: title, subtitle, 7 keywords, HTML description, BISAC categories, recommended price. Templates are version-controlled and evolve based on patterns extracted from historical winners (see Performance Monitor below).

**Publisher** consumes a BookDraft + Listing and executes the KDP submission flow on the assigned account. It is the only agent that performs irreversible external actions, so it has the most rigorous logging, retry, and idempotency guarantees. Each KDP action is atomic and resumable: a publish that fails at step 6 of 8 can resume from step 7 without redoing 1-6.

**Performance Monitor** is the agent that closes the flywheel. It runs nightly, scrapes KDP Reports for all 3 accounts, computes Success Score per book at 7/14/30 day windows, classifies winner/flat/loser, and runs a weekly differential analysis: what do winners share that losers don't? Output is ProposedPolicy records pending operator approval. Once approved, policies are merged into the policy memory and consumed by Strategist, Generator, SEO agents on next run. This is the mechanism by which the system learns.

### 3.3 Validation gates

Three gates separate the agents into stages, each gate killing or recycling work that doesn't meet criteria.

**Niche Gate** sits between Niche Hunter+Deep Scout and Strategist. A NicheBrief passes only if its Profitability Score exceeds the dynamic threshold (computed as the median score of historical winners' originating niches, refreshed weekly). Failed niches are logged with reason and skipped, freeing budget for better candidates.

**Content Gate** sits between Generator and SEO Listing. The Critic agent is the gate. A BookDraft passes only if zero pages are flagged critical and fewer than 10% are flagged minor. Critical flags include: text contamination, malformed anatomy in figurative pages, cover unreadable at thumbnail size, PDF spec violations.

**Listing Gate** sits between SEO Listing and Publisher. Automated policy check: no trademarked terms in keywords (against a maintained blocklist), no bestseller claims, length limits respected, BISAC codes valid against current KDP whitelist, price within reasonable range for category (computed from niche brief). Failed listings are sent back to SEO with specific reason codes; second failure kills the book.

### 3.4 The flywheel cycle

The system operates on three nested cycles.

**The daily cycle** runs every 24 hours: niche hunt -> deep scout -> strategist -> generation queue (parallel up to 3 concurrent books) -> validation -> publish. Target output: 5-10 books per day distributed across accounts respecting per-account limits.

**The weekly cycle** runs every Sunday: performance monitor differential analysis, generation of proposed policies, operator review notification. The operator approves or rejects proposed policies via the dashboard. Approved policies update the policy memory and are immediately consumed by the next daily cycle.

**The monthly cycle** runs on the 1st of each month: catalog audit identifies losers older than 30 days for unpublishing, identifies winners for potential bundle/sequel opportunities (added to a separate opportunity queue surfaced in the dashboard for manual decision), generates a financial report.

## 4. Stack and tooling (locked)

Python 3.12 with uv as package manager and venv handler. CrewAI 0.80+ for agent orchestration. Playwright 1.48+ with playwright-stealth for browser automation. Pydantic v2 for all schemas. Loguru for structured logging. Pytest with pytest-asyncio and pytest-cov for tests. Ruff and mypy in strict mode for linting and types.

TypeScript 5.5 with Next.js 14 (app router) for the dashboard. tRPC v11 for type-safe API. Prisma 5+ as ORM (schema shared between TS and Python via prisma-client-py). NextAuth v5 with magic link email auth. Recharts for data viz. Framer Motion for animations. shadcn/ui as component library on top of Tailwind 3. Biome instead of ESLint+Prettier. Vitest for tests.

Postgres 16 as the system of record. Qdrant 1.11+ for vector memory. Redis 7+ for queue (BullMQ on TS side, RQ on Python side) and cache. Docker Compose for local infra. systemd units for production deployment on the VPS.

Gemini 3.1 Flash Image (Nano Banana 2) for line-art generation, accessed via Google AI SDK. Claude Sonnet 4.6 for Critic vision validation (Anthropic SDK). Claude Opus 4.7 for architecture/debug, Opus 4.6 for implementation (Claude Code subagents). Smartproxy or Bright Data residential proxies, one dedicated endpoint per KDP account.

Sentry for error tracking. Loki+Grafana optional for observability (deferrable to M8). Doppler or sops+age for secrets management. GitHub Actions for CI (lint, type-check, test on every PR).

Versions are pinned in package.json and pyproject.toml. Major version bumps require explicit approval via a decision log entry.

## 5. Data model

The Postgres schema is the backbone. Full Prisma schema in packages/db/schema.prisma. Below is the conceptual map of all 15 tables.

**niches** — Every niche ever scanned, with raw observations (BSR, prices, review counts) and computed Profitability Score. Updated daily; old rows kept for trend analysis.

**niche_briefs** — Enriched output of Deep Scout, one row per deeply-investigated niche. Contains pain points (JSONB), style classification, suggested differentiators, embedding vector reference in Qdrant.

**accounts** — 3 KDP accounts with identity (brand author names, niche specializations, quotas). Critical: storage_state_path and proxy_endpoint_id are the isolation primitives.

**books** — Main entity. State machine: PLANNED -> GENERATING -> VALIDATING -> LISTING -> PUBLISHING -> LIVE -> KILLED. Every state transition logged in book_events.

**book_events** — Audit trail of every book state transition with reason and payload.

**pages** — Per-page metadata: prompt used, generation timestamp, image hash, validation flags, regeneration count. Enables retry of only failed pages.

**listings** — SEO output: title, subtitle, keywords array, description HTML, BISAC codes, price. Versioned: each edit creates new row.

**validations** — Critic reports: per-book pass/fail, per-page flags, full structured JSON. Append-only.

**sales_daily** — One row per (book, account, date, marketplace) with units sold, royalty, KENP read, refund flag. The feedback signal that drives the flywheel.

**royalty_snapshots** — Monthly aggregates for fast dashboard queries.

**policies** — Learned rules: text description, machine-readable constraint, confidence score, status (proposed/approved/retired).

**prompts_history** — Versions every prompt template used by every agent. Critical for debugging.

**experiments** — A/B test definitions with hypothesis, variants, assigned books, conclusions.

**agents_runs** — Audit log: one row per agent invocation with input/output hash, duration, tokens, cost.

**jobs** — Redis job mirror for resumability after Redis restarts.

**alerts** — Performance Monitor alerts surfaced in dashboard Command Center.

Total: 15 tables. Relationships deliberately denormalized in places for analytics query performance.

## 6. Inter-agent contracts (the wire format)

Every agent input and output is a Pydantic model serialized to JSONB in Postgres. Full definitions in packages/shared/src/contracts/ (Zod) and apps/agents/colorforge_agents/contracts/ (Pydantic).

Key contracts: NicheCandidate, NicheBrief, BookPlan, BookDraft, ValidationReport, Listing, SuccessScore, ProposedPolicy.

These contracts are the API of the system. They are versioned with semantic versioning. Breaking changes require a migration plan.

## 7. The Profitability Score formula

The score computes a value between 0 and 100 from eight signals, each normalized to 0-1 against the rolling 90-day distribution. The signals and initial weights:

- **Demand signal** (weight 0.20) — inverse of median BSR among top 20 books, capped at BSR 100k.
- **Price signal** (weight 0.15) — median list price, normalized to $4-$15 range.
- **Competition signal** (weight 0.20, negative) — count of books with <50 reviews (new entrants proxy).
- **Quality gap signal** (weight 0.15) — count of severe pain points in 1-2 star reviews.
- **Trend signal** (weight 0.10) — 90-day Google Trends slope + Pinterest search velocity.
- **Seasonality fit signal** (weight 0.05) — penalizes niches whose peak is >60 days away.
- **Catalog fit signal** (weight 0.10) — cosine similarity between niche embedding and winners centroid.
- **Saturation velocity signal** (weight 0.05, negative) — rate of new publications in last 30 days.

Weights are intentionally conservative initially. After 60 days, Performance Monitor proposes adjustments based on which signals correlated with actual winners. This is meta-learning.

## 8. Operational concerns

### 8.1 Secrets and credentials
KDP credentials never in plaintext on disk. Bootstrap flow uses manual Playwright login, encrypted storageState via age, decrypted to tmpfs at runtime. API keys via Doppler or sops+age.

### 8.2 Failure modes and recovery
Every agent is idempotent at job level. Common scenarios: KDP UI selector break (screenshot + alert + manual fix), Gemini rate limit (exponential backoff), DB/Redis down (systemd restart), Critic false positive storm (auto-pause if >50% fail in 24h), account warning (halt account queue, alert).

### 8.3 Ramp-up plan
Days 1-7: 2 books/day, manual review. Days 8-30: 5 books/day, operator approves listings. Days 31-60: 8-10 books/day, auto-publish, flywheel policies operator-approved only. Days 61+: 10-15 books/day, low-risk policies may auto-approve.

### 8.4 Cost monitoring
Every API call recorded with token count and cost. Daily ceiling default $50/day. Auto-pause on exceed.

## 9. Milestones reference

Eight milestones, strictly ordered M1 -> M8:
- **M1** — Foundation & Schema
- **M2** — KDP Client + Multi-Account Manager
- **M3** — Niche Hunter + Deep Scout
- **M4** — Generator + Critic (+ Strategist)
- **M5** — SEO Listing + Publisher Integration
- **M6** — Performance Monitor + Flywheel
- **M7** — Dashboard
- **M8** — Hardening + Observability + Go-Live

## 10. Decision log (versioned)

[2026-04-29] CrewAI chosen over LangGraph as agent orchestrator. Rationale: role-based modeling matches 7-agent design; lower learning curve; sufficient production track record.

[2026-04-29] Claude Sonnet 4.6 chosen for Critic role. Rationale: different vendor than Generator (Gemini) eliminates auto-confirmation bias; vision quality at parity with Opus for line-art; cost meaningfully lower.

[2026-04-29] Postgres+Qdrant+Redis chosen as storage trio. Rationale: each excels at its workload; all three run in <1GB RAM each.

## 11. Glossary

- **Hit rate** — % of published books achieving winner classification within 30 days.
- **Winner** — Book earning >$50 royalties in any rolling 30-day window within first 90 days.
- **Flat** — Book earning $10-$50 in any 30-day window.
- **Loser** — Book earning <$10 in first 60 days.
- **Profitability Score** — Niche Hunter's 0-100 ranking from 8 weighted signals (section 7).
- **Success Score** — Performance Monitor's 0-100 per-book score from observed sales.
- **Policy** — Learned rule extracted by the flywheel.
- **Brand author** — Pseudonym tied to niche specializations for catalog coherence.
- **Account warming** — First 60 days with artificially limited publishing rate.

---
*End of Master Specification. This document is the constitution of ColorForge AI.*
