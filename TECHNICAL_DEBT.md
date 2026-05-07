# ColorForge AI — Technical Debt Register

Last updated: 2026-05-07 (M8 close)

---

## Closed in M8

| ID  | Description                                      | Closed |
|-----|--------------------------------------------------|--------|
| K05 | Trademark blacklist (120+ terms, tier system)    | M8     |
| K06 | CMYK cover compositor (ICC USWebCoatedSWOP)      | M8     |
| K07 | Barcode area white-box reservation               | M8     |
| K09 | low_content flag + PAPERBACK quota routing       | M8     |
| K10 | CoverCompositor integrated in pipeline           | M8     |
| K13 | File size guard (650MB hard / 40MB soft + GS)    | M8     |
| K14 | FrontMatterAssembler (AI disclosure, niche templates) | M8 |
| K15 | CurrencyService (Redis cache, drift detection)   | M8     |
| K16 | UTF-8 pyproject.toml (no em-dash bytes)          | M8     |

## Closed in M6.5

| ID  | Description                                      | Closed |
|-----|--------------------------------------------------|--------|
| K01 | Weekly per-format quota (10/week)                | M6.5   |
| K02 | Gutter table corrected (5 tiers)                 | M6.5   |
| K03 | Outside margin validation (0.375")               | M6.5   |
| K04 | Spine text threshold corrected (79 pages)        | M6.5   |
| K08 | TrimSize enum + Strategist auto-select           | M6.5   |
| K11 | PaperType enum + spine_multiplier property       | M6.5   |
| K12 | CoverFinish enum + BookPlan field                | M6.5   |

---

## Open (post-v1.0)

| ID  | Description                                      | Priority |
|-----|--------------------------------------------------|----------|
| D01 | `image_gen.py` coverage 31% -- no Gemini mock    | Low      |
| D02 | `monitor/` modules 0% coverage (scraper/snapshot/perf) | Medium |
| D03 | `run_publish.py` Prisma integration not tested   | Low      |
| D04 | Pillow `getdata()` deprecation (Pillow 14, 2027) | Low      |
| D05 | `CoverCompositor._export_pdf` PDF/X-1a metadata not set | Medium |
| D06 | Currency drift detection fires on cache seed (not just real drift) | Low |

---

## Never-do List

- Do NOT mock the DB in publisher integration tests (K-incident 2026-04)
- Do NOT use `asyncio.get_event_loop()` in new code (use `asyncio.run()`)
- Do NOT commit storageState files or generated PDFs
