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
M6 — Performance Monitor + Flywheel. Status: Complete.
Next: M7 — Dashboard.

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

## How to Start a Task
1. If task is in MILESTONE_M*_PLAN.md, read its acceptance criteria
2. If implementation: invoke `implementer` subagent with task description + acceptance
3. If test: invoke `tester` subagent
4. If debugging stuck case: stay as architect, read minimal context, propose fix
5. After every task: run `make check` (lint + typecheck + test). Commit if green.
