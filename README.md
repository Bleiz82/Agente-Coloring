# ColorForge AI

Self-improving multi-agent system for KDP coloring book publishing. Targets 15%+ hit rate on 250 books/month across 3 KDP accounts.

## Quick Start

### Prerequisites
- Node.js >= 20.10
- pnpm >= 9.12 (`npm install -g pnpm`)
- Python >= 3.12
- uv (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose

### Bootstrap (first time)

```bash
# 1. Clone and enter the repo
git clone <repo-url> colorforge
cd colorforge

# 2. Copy environment file
cp .env.example .env

# 3. Install all dependencies
make install
# Or manually:
#   pnpm install
#   uv sync

# 4. Start infrastructure (Postgres, Qdrant, Redis)
make infra-up

# 5. Run database migrations
pnpm db:push

# 6. Seed initial data (3 accounts, 1 niche, 3 policies)
pnpm db:seed

# 7. Verify everything works
make check
```

Or run the bootstrap script:
```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

### Daily Commands

```bash
make help          # Show all available commands
make check         # Lint + typecheck + test (TS + Python)
make test          # Run all tests
make lint          # Run linters
make infra-up      # Start Postgres + Qdrant + Redis
make infra-down    # Stop infrastructure
make db-seed       # Re-seed database (idempotent)
make kill          # Emergency killswitch — halts everything in <10s
```

### Database

```bash
pnpm db:generate   # Regenerate Prisma client after schema changes
pnpm db:migrate    # Run migrations (dev)
pnpm db:push       # Push schema to DB without migration
pnpm db:seed       # Seed initial data
pnpm db:studio     # Open Prisma Studio GUI
```

## Architecture

See [SPEC.md](./SPEC.md) for the full Master Specification.

### Monorepo Structure

```
colorforge/
├── .claude/              # Claude Code config (agents, skills, commands)
├── apps/
│   ├── agents/           # Python — AI agent system (M3-M6)
│   ├── dashboard/        # Next.js 14 — operator dashboard (M7)
│   └── worker/           # Python — browser automation worker (M2)
├── packages/
│   ├── db/               # Prisma schema + seed + migrations
│   ├── shared/           # Zod contracts + shared TS types
│   └── kdp-client/       # Python — KDP automation library (M2)
├── infra/                # Docker Compose + DB init scripts
├── scripts/              # Killswitch, bootstrap, encryption
├── config/               # Style fingerprints, categories, blocklists
└── docs/                 # Runbook, operational docs
```

### Stack

| Layer | Technology |
|-------|-----------|
| Agents | Python 3.12, CrewAI, Pydantic v2 |
| Dashboard | Next.js 14, tRPC v11, shadcn/ui, Tailwind 3 |
| Database | Postgres 16, Prisma 5 |
| Vector Store | Qdrant 1.11+ |
| Queue/Cache | Redis 7+, BullMQ/RQ |
| Image Gen | Gemini 3.1 Flash Image |
| Validation | Claude Sonnet 4.6 (vision) |
| Browser | Playwright 1.48+ with stealth |
| Linting | ruff + mypy (Python), biome (TS) |
| Testing | pytest (Python), vitest (TS) |

### Milestones

- **M1** — Foundation & Schema (current)
- **M2** — KDP Client + Multi-Account Manager
- **M3** — Niche Hunter + Deep Scout
- **M4** — Generator + Critic
- **M5** — SEO Listing + Publisher Integration
- **M6** — Performance Monitor + Flywheel
- **M7** — Dashboard
- **M8** — Hardening + Observability + Go-Live

## Safety

- **Killswitch**: `python scripts/kill.py` halts all processes in <10 seconds
- **Rate limiting**: Max 5 publishes/account/day during 60-day warming period
- **AI Disclosure**: Always enabled on every KDP submission
- **Account isolation**: Separate browser contexts, proxies, and fingerprints per account
- **Secrets**: Never in code or logs; encrypted via sops+age
