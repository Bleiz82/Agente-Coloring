# ColorForge AI — Claude Code Master Context

## Project Identity
ColorForge AI is a self-improving multi-agent system for KDP coloring book publishing.
Owner: Stefano (DigIdentity Agency). Goal: 15%+ hit rate on 250 books/month across 3 accounts.
Read SPEC.md in repo root for full context. This file is operational rules.

## Stack (LOCKED — do not change without architect approval)
Python 3.12 + uv | TypeScript 5.5 + Next.js 14 + tRPC v11 | Prisma 5 (shared schema)
Postgres 16 | Qdrant 1.11+ | Redis 7+ | CrewAI 0.80+ | Playwright 1.48+
Gemini 3.1 Flash Image (generation) | Claude Sonnet 4.6 (critic, vision)
ReportLab + Pillow (PDF) | Recharts + shadcn/ui + Tailwind 3 (dashboard)
ruff + mypy strict | biome | pytest + vitest | conventional commits

## Delegation Rules (CRITICAL — these save 60% tokens)
- DEFAULT MODEL for any code writing: invoke `implementer` subagent (Opus 4.6)
- ARCHITECT (this main session, Opus 4.7) does ONLY:
  * Read SPEC.md and design decisions
  * Plan milestone tasks (write MILESTONE_M*_PLAN.md)
  * Debug stuck cases that implementer failed twice
  * Code review on critical paths: kdp-client, scoring formula, gates, killswitch
- TESTER subagent (Opus 4.6) writes and runs tests after each task
- NEVER read full files when grep/find suffices. NEVER re-read files in same session.
- Use skills (.claude/skills/*) instead of re-explaining domain knowledge
- When task is "write boilerplate X", invoke implementer immediately, do not narrate

## Code Conventions
- Python: ruff format + check, mypy --strict, async-first, Pydantic v2 only
- TS: biome format + lint, strict tsconfig, no `any`, no `as` casts unless documented
- Imports: absolute from package root, no deep relative
- Errors: typed exceptions in Python (custom exception classes per domain), Result type optional in TS via neverthrow
- Logging: loguru in Python with structured JSON, pino in TS
- Tests: every public function gets at least one test; >80% coverage on critical paths

## Git Hygiene
- Conventional commits: `feat(m1):`, `fix(m2):`, `refactor(m3):`, `test(m1):`, `docs:`, `chore:`
- One commit per atomic task, never bundle unrelated changes
- Branch per milestone: `m1-foundation`, `m2-kdp-client`, etc. Merge to main on milestone close.
- Never commit: secrets, .env files, storageState files, generated PDFs, node_modules, .venv

## Non-Negotiables
1. Multi-account isolation: separate BrowserContext + proxy + fingerprint + storageState
2. Rate limiting: max 5 publishes/account/day for first 60 days (DB-enforced)
3. Every published book passes 3 validation gates
4. Every prompt change versioned in prompts_history table
5. Killswitch `python scripts/kill.py` halts everything in <10s (tested in CI)
6. AI content disclosure flag = true on every book
7. No secret in code or logs. Use Doppler or .env.encrypted via sops+age.
8. No mocks left in production code paths. Tests use mocks; src must not.

## Current Milestone
M7 — Dashboard. Status: Complete.
Next: M8 — KDP compliance (K05-K07, K09-K10) + pipeline hardening.

### M6.5 Fixes Applied (2026-05-06)
- K01: Weekly per-format quota (10/week) replaces daily quota (5/day) in `colorforge_kdp/quota.py`
- K02: Gutter table corrected in `pdf_assembler._compute_gutter_inches` (was 0.5/0.625/0.75, now 0.375/0.5/0.625/0.75/0.875)
- K03: Outside margin validation added (`_validate_outside_margin`, constant 0.375" with bleed)
- K04: kdp-specs.md spine text threshold corrected from 100 → 79 pages
- K08: `TrimSize` enum (5 sizes) + `trim_size` field on `BookPlan`; Strategist auto-selects from niche keywords
- K11: `PaperType` enum with `spine_multiplier` property; `PDFAssembler.spine_width_inches()` uses it
- K12: `CoverFinish` enum + field on `BookPlan` (default MATTE)
- `BookFormat` enum (PAPERBACK/HARDCOVER) added; quota tracked per-format
- Deferred to M8: K05 (trademark blacklist), K06 (CMYK cover), K07 (barcode area), K09, K10

### M7 Dashboard Delivered (2026-05-06)
- Next.js 14 App Router dashboard at `apps/dashboard/` — TypeScript strict, tRPC v11, Prisma 5
- Health engine: `computeSystemHealth` pure fn, 5-state beacon (BLACK/RED/ORANGE/YELLOW/GREEN)
- tRPC routers: health, alerts, books, accounts, sales, policies, killswitch, feedback
- Pages: Overview, Books, Performance, Niches, Ledger, Alerts, Policies, Accounts, Settings, Research, Research/[nicheId]
- UI components: StatusBeacon, KPICard, SparkLine, AlertRow, PolicyCard, BookTable, KillswitchButton, RoyaltyChart, BookStateChart
- Auth: JWT (jose), bcrypt, httpOnly cookie, middleware guard
- SSE: /api/sse/alerts for live alert streaming
- Tests: 77 Vitest unit tests (health engine 46, format 21, killswitch 8) + 8 Playwright E2E scenarios
- Schema extensions: FeedbackEvent, SystemConfig, SystemState, CompetitorSnapshot (v2.2 CI models)

## Open Decisions (architect log here)
[2026-04-29] Stack locked per SPEC.md section 4.
[2026-04-29] Prisma chosen as ORM with prisma-client-py for Python interop.
[2026-04-29] Single repo, pnpm + uv workspaces. No turborepo until M7.
[2026-05-04] playwright-stealth v2.x API: use Stealth().apply_stealth_async(page) — stealth_async removed in v2.
[2026-05-04] age CLI binary (subprocess) used for storageState encryption, not pure-Python age.
[2026-05-04] Worker uses RQ (not Celery) per SPEC.md §4. Systemd timer handles scheduling.
[2026-05-06] Pillow LANCZOS compatibility: use `getattr(PILImage, "Resampling", PILImage).LANCZOS` (works Pillow <9.1 and ≥9.1).
[2026-05-06] PDF height = 810.0 pt (11.0 + 2×0.125)*72, NOT 819 — confirmed by pypdf roundtrip test.
[2026-05-06] When all Generator pages fail, skip PDF assembly and touch placeholder file — avoids PDFAssemblyResult(page_count=0) gt=0 violation.
[2026-05-06] ListingContract Pydantic max_length prevents constructing violating instances — tests use model_construct() to bypass validation for gate length checks.
[2026-05-06] QuotaExceeded from kdp-client propagates uncaught through PublisherAgent — callers distinguish it from KDP browser failures (PublisherAgentError).
[2026-05-06] _validate_image_dpi uses round() for DPI comparison — Pillow returns 299.9994 for nominal 300 DPI PNGs (floating point).
[2026-05-06] BookPlan has trim_size/paper_type/cover_finish/book_format fields with backward-compatible defaults — existing tests unaffected.
[2026-05-06] PDFAssembler.__init__ now takes trim_size and paper_type; module-level TRIM_W_IN/TRIM_H_IN kept as backward-compat constants for LETTER.
[2026-05-06] assemble_manuscript reserves outside margin 0.375" (bleed) when computing img_w — previously filled to trim edge leaving 0" margin.

## How to Start a Task
1. If task is in MILESTONE_M*_PLAN.md, read its acceptance criteria
2. If implementation: invoke `implementer` subagent with task description + acceptance
3. If test: invoke `tester` subagent
4. If debugging stuck case: stay as architect, read minimal context, propose fix
5. After every task: run `make check` (lint + typecheck + test). Commit if green.
