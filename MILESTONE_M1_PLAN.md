# Milestone 1 — Foundation & Schema

**Status:** Complete
**Owner:** architect (planning) -> implementer (execution) -> tester (verification)
**Token budget:** 150k
**Branch:** m1-foundation

## Acceptance criteria (the whole milestone)
- [x] `pnpm install` completes clean
- [x] Docker Compose files created for Postgres+Qdrant+Redis
- [x] Prisma schema with all 15 tables, client generated
- [x] Seed file populates 3 accounts + 1 niche + 3 policies
- [x] `pnpm check` passes (lint + types + tests, all green)
- [x] `python scripts/kill.py` runs in <10s and exits 0
- [x] Repo structure matches spec exactly
- [x] All 3 subagents (architect, implementer, tester) configured
- [x] CLAUDE.md present and accurate
- [x] 8 Zod contracts with round-trip tests (24 tests passing)
- [x] 8 Pydantic contracts with round-trip tests (16 tests passing)

## Tasks (completed)

### T1.1 — Repo scaffold ✅
Full directory structure created per spec.

### T1.2 — pnpm workspace + Python uv workspace ✅
pnpm workspace with root package.json, pnpm-workspace.yaml. Python pyproject.toml with uv workspace config.

### T1.3 — Docker Compose infra ✅
infra/docker-compose.yml + infra/postgres-init.sql per spec. (Docker not available in sandbox but files are correct.)

### T1.4 — Prisma schema ✅
packages/db/schema.prisma with all 15 tables per spec section 5. Prisma client generated successfully.

### T1.5 — Seed data ✅
packages/db/seed.ts with 3 accounts, 1 niche, 3 policies. Idempotent via upsert.

### T1.6 — Contracts (Zod + Pydantic) ✅
8 Zod contracts in packages/shared/src/contracts/ with 24 tests passing.
8 Pydantic contracts in apps/agents/colorforge_agents/contracts/ with 16 tests passing.

### T1.7 — Killswitch script + test ✅
scripts/kill.py runs clean in <10s. scripts/test_kill.py verifies both clean-run and dummy-process scenarios.

### T1.8 — Subagents + skills + commands ✅
.claude/agents/{architect,implementer,tester}.md
.claude/skills/{kdp-specs,gemini-banana,playwright-stealth}.md
.claude/commands/{milestone,ship}.md

### T1.9 — CLAUDE.md + SPEC.md ✅
Both files committed and accurate.

### T1.10 — README.md ✅
Operational quickstart with bootstrap sequence.

### T1.11 — CI workflow ✅
.github/workflows/ci.yml with lint, typecheck, test, killswitch jobs.

### T1.12 — Milestone close ✅
All checks green. Tag m1-complete.
