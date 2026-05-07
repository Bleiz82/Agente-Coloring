# ColorForge AI — Soft-Launch Checklist (v1.0.0)

**Target: first 5 books on secondary account, manual review gate on each.**

---

## Pre-Launch (run once)

### Infrastructure
- [ ] Postgres 16 running, schema migrated (`prisma migrate deploy`)
- [ ] Redis 7+ running (or `REDIS_URL` unset to use in-memory cache fallback)
- [ ] Qdrant 1.11+ running, coloring-book collection created
- [ ] Doppler / `.env.encrypted` loaded — all required vars present
- [ ] `uv run python scripts/run_publish.py --dry-run` exits 0

### Assets
- [ ] `python scripts/download_assets.py` ran successfully (fonts + ICC profile)
- [ ] `assets/fonts/` has all 8 required TTF files (see `assets/fonts/README.md`)
- [ ] `assets/icc/USWebCoatedSWOP.icc` present (649 KB)

### Accounts
- [ ] Secondary KDP account credentials in DB (`Account.label = "secondary"`)
- [ ] `storageState` encrypted and stored for secondary account
- [ ] Proxy assigned and verified for secondary account

### Quota
- [ ] Weekly quota reset (10 PAPERBACK / 10 HARDCOVER per account)
- [ ] Quota table seeded: `prisma studio` or SQL insert into `QuotaUsage`

---

## Per-Book Gate (run before every KDP submission)

### Content Quality
- [ ] All coloring pages generated (no placeholder images)
- [ ] ValidationReport `overall_score >= 0.80`
- [ ] No blank page runs > 4 mid-book or > 10 at end
- [ ] Total page count 24 -- 828

### Cover
- [ ] Cover image loaded correctly, no AI artifacts visible
- [ ] CMYK conversion succeeded (ICC profile applied)
- [ ] Spine text included iff page_count >= 79
- [ ] Barcode area is white (>= 95% white pixels)
- [ ] PDF file size < 650 MB

### Listing
- [ ] `ListingGate.passes()` returns `(True, [])` -- no trademark violations
- [ ] `low_content` flag correct (False for coloring books)
- [ ] Price in range $7.99 -- $14.99
- [ ] 7 keywords, all < 50 chars, no repetition of title words
- [ ] BISAC code correct (ART015000 for adult coloring)
- [ ] `ai_disclosure = True` on ListingContract
- [ ] AI disclosure phrase "AI-generated" present in copyright page text

### Final checks
- [ ] `uv run python scripts/run_e2e_dryrun.py` shows 7/7 PASS
- [ ] Weekly quota not exceeded for account+format

---

## Publish Command

```bash
# Soft-launch: generate + review + publish on secondary account
uv run --project apps/agents python scripts/run_publish.py \
    --account secondary \
    --niche-id <uuid-from-db> \
    --review

# Skip review gate (use only after first 5 books validate OK):
uv run --project apps/agents python scripts/run_publish.py \
    --account secondary \
    --niche-id <uuid-from-db> \
    --no-review
```

---

## Post-Publish Verification (within 24h)

- [ ] Book appears in KDP Bookshelf (status: In Review or Live)
- [ ] ASIN written to `Book.asin` in DB
- [ ] Book state transitioned to `LIVE` in DB
- [ ] No KDP rejection email received
- [ ] Cover thumbnail matches expected design

---

## Rollback Procedure

If any gate fails or KDP rejects:

1. Set book state to `VALIDATING` in DB
2. Fix the root cause (see error in `BookEvent` table)
3. Re-run generation or listing fix
4. Re-run through all per-book gate checks above
5. Re-submit

Emergency halt: `python scripts/kill.py` -- stops all agents in < 10s.

---

## Acceptance Criteria for Soft-Launch Graduation

Graduate to full automation (remove `--review`) when:
- [ ] 5/5 soft-launch books go Live on KDP with no rejection
- [ ] No ListingGateBlocked errors in production logs (7 days)
- [ ] Weekly quota never exceeded
- [ ] E2E dry-run passes on every CI run

Tag: `v1.0.0-launch` after graduation.
