# Test Fixtures

Generated programmatically by `conftest.py` — do NOT commit binary files here.

## Contents (generated at test runtime)

| File pattern | Description |
|---|---|
| `cover_300dpi_*.png` | 300 DPI RGB PNG, various sizes, used by CoverCompositor tests |
| `cover_150dpi.png` | 150 DPI PNG — triggers DPI validation failure |
| `interior_*.pdf` | Sample interior PDFs (1-3 pages) for FrontMatterAssembler tests |
| `book_plan_*.json` | Sample BookPlan JSON fixtures |
| `book_draft_*.json` | Sample BookDraft JSON fixtures |

## Regenerating fixtures

```bash
cd apps/agents
uv run python -c "import tests.conftest; tests.conftest.generate_fixtures()"
```

Or simply run the test suite — fixtures are auto-generated via `conftest.py` session-scoped fixtures.
