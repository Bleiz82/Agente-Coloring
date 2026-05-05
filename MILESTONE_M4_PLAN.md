# Milestone 4 — Generator + Critic (+ Strategist)

**Status:** In Progress
**Owner:** architect (planning) → implementer (execution) → tester (verification)
**Token budget:** 250k
**Branch:** main (continuing)

## Scope (from SPEC.md §3.2, §9)
Build three agents:
- **Strategist**: consumes NicheBrief + accounts state → BookPlan (per-page prompts, account/author selection, policy awareness).
- **Generator**: consumes BookPlan → BookDraft (Gemini Flash Image generation, Pillow post-processing, ReportLab KDP-compliant PDF assembly).
- **Critic**: consumes BookDraft → ValidationReport (Claude Sonnet 4.6 vision per-page and cover inspection, PDF spec validation).
Also implements the Content Gate between Generator and downstream agents.

## Acceptance criteria (whole milestone)
- [ ] `StrategistCore.plan(brief, accounts, config)` returns a valid `BookPlan` (prompts, account, price)
- [ ] `GeminiImageClient.generate_image(prompt)` calls the API with semaphore-3 concurrency and returns PNG bytes
- [ ] `ImagePostProcessor.process(bytes)` returns grayscale 300-DPI PNG with artifact flag
- [ ] `PDFAssembler.assemble_manuscript(pages, output)` produces a PDF with correct KDP dimensions
- [ ] `GeneratorCore.generate(plan)` produces a `BookDraft` with manuscript + cover PDFs and all page metadata
- [ ] `VisionChecker.check_pages(paths)` returns `list[list[PageFlag]]` parsed from Claude vision JSON
- [ ] `CriticCore.critique(draft)` returns a `ValidationReport` with correct verdict logic
- [ ] `ContentGate.passes(report)` blocks drafts with ≥1 severity-4+ flag or >10% minor flags
- [ ] `python scripts/run_generation.py --dry-run` exits 0
- [ ] mypy --strict + ruff passing on all M4 modules
- [ ] >80% coverage on content_gate.py and pdf_assembler.py (deterministic logic)

## Architectural decisions
[2026-05-05] `google-genai>=0.8.0` SDK used for Gemini image generation.
  API: `client.aio.models.generate_content(model=..., contents=..., config=GenerateContentConfig(response_modalities=["IMAGE"]))`
  Model string: `"gemini-3.1-flash-image-generation"` (configurable via GEMINI_MODEL env var).

[2026-05-05] ReportLab `canvas.Canvas` for PDF assembly (not platypus/flowable).
  Rationale: direct pixel-perfect control over KDP dimensions; flowable API adds unnecessary abstraction.

[2026-05-05] Vision checking batches pages in groups of 5 to stay within Claude's context window.
  Each batch is one Claude call with multiple images; results merged by page index.

[2026-05-05] PDF spec validation via `pypdf` (read PDF metadata + page sizes) — not Claude vision.
  Rationale: Claude vision cannot inspect raw PDF specs reliably; pypdf is deterministic and fast.

[2026-05-05] Strategist uses template-based prompt generation (no LLM call) for M4.
  Rationale: prompts are deterministic transformations of the NicheBrief fields; LLM prompt generation
  is reserved for M6 (flywheel policy application). This keeps M4 testable without LLM mocks.

[2026-05-05] Spine width formula: `0.002252 * page_count` inches (KDP white paper spec).
  Cover width: `(2 * 8.5 + spine + 2 * 0.125)` inches. Cover height: `11.0 + 2 * 0.125` inches.

## KDP PDF Specs (locked reference)
- Trim size: 8.5" × 11.0"
- Bleed (all sides): 0.125"
- Interior gutter: 0.375"
- Full page with bleed: 8.75" × 11.25" → 630 pt × 810 pt (72 pt/in)
- 300 DPI for raster content: 8.5" × 11.0" = 2550 × 3300 px

## Tasks

### T4.1 — Package deps + module skeleton
**Estimated tokens:** 8k
**Dependencies:** M3 complete
**Acceptance:** `python -c "import colorforge_agents.generator; import colorforge_agents.critic; import colorforge_agents.strategist"` succeeds

Add to `apps/agents/pyproject.toml`:
```toml
"google-genai>=0.8.0",
"reportlab>=4.2.0",
"Pillow>=10.4.0",
"pypdf>=4.0.0",
```

Add to `[[tool.mypy.overrides]]`:
```
"google", "google.*",
"reportlab", "reportlab.*",
"PIL", "PIL.*",
"pypdf", "pypdf.*",
```

Add to `exceptions.py`: `ImageGenerationError`, `PDFAssemblyError`, `CriticError`, `ContentGateBlocked`, `StrategistError`.

Create skeleton:
```
colorforge_agents/
  strategist/
    __init__.py
    strategist.py     (T4.2)
  generator/
    __init__.py
    generator.py      (T4.6)
    image_gen.py      (T4.3)
    post_processor.py (T4.4)
    pdf_assembler.py  (T4.5)
  critic/
    __init__.py
    critic.py         (T4.8)
    vision_checker.py (T4.7)
  gates/
    content_gate.py   (T4.8)
tests/
  test_strategist.py  (T4.9)
  test_generator.py   (T4.9)
  test_critic.py      (T4.9)
  test_content_gate.py (T4.9)
  test_pdf_assembler.py (T4.9)
scripts/
  run_generation.py   (T4.6)
```

---

### T4.2 — Strategist agent
**Estimated tokens:** 25k
**Dependencies:** T4.1
**Acceptance:** mock test — 1 NicheBrief + 2 accounts → BookPlan with correct page_count, prompts, account_id

```python
class AccountState(BaseModel):
    account_id: str
    brand_author: str
    publications_last_30d: int
    niche_specializations: list[str]

class StrategistConfig(BaseModel):
    page_count: int = 75
    target_price: float = 7.99
    max_daily_pubs_per_account: int = 5

class StrategistCore:
    def __init__(self, prisma: Any) -> None: ...
    async def plan(self, brief: NicheBrief, accounts: list[AccountState], config: StrategistConfig) -> BookPlan: ...
    def _select_account(self, accounts, config) -> AccountState: ...
    def _derive_style_fingerprint(self, brief) -> str: ...
    def _build_page_prompts(self, brief, page_count, style_fp) -> list[PagePrompt]: ...
    def _cover_brief_from_niche(self, brief, style_fp) -> CoverBrief: ...
```

Page prompt template: `"Black and white coloring book line art for adults. Subject: {theme}. Style: clean bold outlines, uniform line weight, NO shading, NO gradients. Background: pure white. Detail level: {tier}."`

Complexity progression: first 20% sparse, middle 60% medium, last 20% dense.
Account selection: account with fewest `publications_last_30d` (deterministic tiebreak by account_id).

---

### T4.3 — Gemini image client
**Estimated tokens:** 18k
**Dependencies:** T4.1
**Acceptance:** mock test — API called once per `generate_image()`; semaphore respected; PNG bytes returned

```python
class GeminiImageClient:
    _MAX_CONCURRENT = 3
    DEFAULT_MODEL = "gemini-3.1-flash-image-generation"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None: ...
    async def generate_image(self, prompt: str) -> bytes: ...
    async def _call_api(self, prompt: str) -> bytes: ...
```

Uses `google.genai` async client. Response: `candidates[0].content.parts` → find `part.inline_data` → return `part.inline_data.data` (bytes).
Raises `ImageGenerationError` on API failure or missing image part.
Exponential backoff: 3 retries, base 2s, cap 30s.

---

### T4.4 — Image post-processor (Pillow)
**Estimated tokens:** 15k
**Dependencies:** T4.1
**Acceptance:** test — grayscale PNG in → grayscale 300 DPI PNG out; artifact flag set for solid-block image

```python
@dataclass
class ProcessedImage:
    data: bytes
    artifact_detected: bool
    width_px: int
    height_px: int

class ImagePostProcessor:
    TARGET_DPI = 300
    PAGE_W_PX = 2550  # 8.5" * 300 DPI
    PAGE_H_PX = 3300  # 11.0" * 300 DPI

    def process(self, image_bytes: bytes) -> ProcessedImage: ...
    def _to_grayscale(self, img: Image.Image) -> Image.Image: ...
    def _normalize_contrast(self, img: Image.Image) -> Image.Image: ...
    def _resize_to_target(self, img: Image.Image) -> Image.Image: ...
    def _detect_artifacts(self, img: Image.Image) -> bool: ...
```

Artifact detection: compute std-dev of pixel values in 10 random 50×50 patches; if any patch std-dev < 5.0 (near-solid), flag as artifact.
Contrast normalization: stretch histogram to [10, 245] range (linear, per CLAHE approximation).

---

### T4.5 — PDF assembler (ReportLab)
**Estimated tokens:** 20k
**Dependencies:** T4.1
**Acceptance:** test — KDP dimensions verified; spine formula correct; pypdf reads output page size

```python
class PDFAssemblyResult(BaseModel):
    output_path: str
    page_width_pts: float
    page_height_pts: float
    page_count: int

class PDFAssembler:
    TRIM_W_IN = 8.5
    TRIM_H_IN = 11.0
    BLEED_IN = 0.125
    GUTTER_IN = 0.375
    PT_PER_IN = 72.0
    SPINE_PER_PAGE = 0.002252

    def assemble_manuscript(self, page_images: list[Path], output_path: Path) -> PDFAssemblyResult: ...
    def assemble_cover(self, cover_image: Path, page_count: int, output_path: Path) -> PDFAssemblyResult: ...
    def spine_width_inches(self, page_count: int) -> float: ...
```

Manuscript: each page 8.75" × 11.25" (trim + bleed), image centered with gutter offset on binding side.
Cover: width = 2*8.5 + spine + 2*0.125; height = 11.0 + 2*0.125. Cover image scaled to fill.

---

### T4.6 — Generator agent + run_generation.py
**Estimated tokens:** 30k
**Dependencies:** T4.2, T4.3, T4.4, T4.5
**Acceptance:** mock test — 1 BookPlan (3 pages) → BookDraft with 3 DraftPages + manuscript/cover paths

```python
class GeneratorCore:
    _MAX_CONCURRENT = 3

    def __init__(
        self,
        image_client: GeminiImageClient,
        post_processor: ImagePostProcessor,
        pdf_assembler: PDFAssembler,
        prisma: Any,
        assets_base: Path,
    ) -> None: ...
    async def generate(self, plan: BookPlan) -> BookDraft: ...
    async def _generate_page(self, prompt: PagePrompt, output_path: Path) -> DraftPage: ...
    async def _generate_cover(self, brief: CoverBrief, output_path: Path) -> Path: ...
```

Asset layout: `{assets_base}/{account_id}/{book_id}/pages/page_{N:03d}.png`
Generation time tracking via `time.monotonic()`.
Pages generated with `asyncio.Semaphore(3)` concurrency.
Failed page (after 2 retries): `validation_status="fail"`, image_path empty string.

---

### T4.7 — Vision checker (Claude Sonnet 4.6 vision)
**Estimated tokens:** 25k
**Dependencies:** T4.1
**Acceptance:** mock test — 2 page images → list[list[PageFlag]] with correct page_index values

```python
class VisionChecker:
    MODEL = "claude-sonnet-4-6"
    BATCH_SIZE = 5

    def __init__(self, client: anthropic.AsyncAnthropic) -> None: ...
    async def check_pages(self, image_paths: list[Path]) -> list[list[PageFlag]]: ...
    async def check_cover(self, cover_path: Path) -> CoverAssessment: ...
    async def check_pdf_specs(self, manuscript_path: Path, cover_path: Path) -> tuple[bool, list[str]]: ...
    async def _check_batch(self, paths: list[Path], start_idx: int) -> list[list[PageFlag]]: ...
```

Page check prompt: system instructs strict coloring-book QA; asks for JSON array (one element per page) of flag arrays. Each flag: `{type, severity, detail}`.
PDF spec check: uses pypdf to verify page dimensions (not Claude vision).
Raises `CriticError` on JSON parse failure.

---

### T4.8 — Critic agent + Content Gate
**Estimated tokens:** 20k
**Dependencies:** T4.7
**Acceptance:** test — 0 flags → "pass"; 1 severity-5 flag → "fail"; >10% minor flags → "needs_regen"

```python
class CriticCore:
    def __init__(self, vision_checker: VisionChecker, prisma: Any) -> None: ...
    async def critique(self, draft: BookDraft) -> ValidationReport: ...
    async def _persist(self, report: ValidationReport) -> None: ...

class ContentGate:
    CRITICAL_SEVERITY = 4

    def passes(self, report: ValidationReport) -> tuple[bool, str]: ...
```

Verdict logic:
- `fail`: any flag with severity ≥ 5, OR cover readability_score < 50, OR PDF non-compliant
- `needs_regen`: any flag severity ≥ 4 (critical), OR >10% pages have any flag
- `pass`: otherwise

ContentGate: passes if verdict == "pass" or verdict == "needs_regen" with <2 critical flags.
Raises `ContentGateBlocked` with book_id + verdict + reason if blocked.

---

### T4.9 — Full test suite
**Estimated tokens:** 40k
**Dependencies:** T4.1–T4.8
**Acceptance:** pytest green, >80% coverage on content_gate.py and pdf_assembler.py

Test files:
- `tests/test_strategist.py` — account selection, prompt count, style fingerprint
- `tests/test_generator.py` — BookDraft structure, concurrency, failed page handling
- `tests/test_critic.py` — verdict logic, per-page flags, cover assessment
- `tests/test_content_gate.py` — all verdict/flag combinations
- `tests/test_pdf_assembler.py` — KDP dimensions, spine formula, pypdf verification
- `tests/test_post_processor.py` — grayscale conversion, DPI, artifact detection

## Token budget tracking
| Task | Estimated | Actual |
|------|-----------|--------|
| T4.1 | 8k  | — |
| T4.2 | 25k | — |
| T4.3 | 18k | — |
| T4.4 | 15k | — |
| T4.5 | 20k | — |
| T4.6 | 30k | — |
| T4.7 | 25k | — |
| T4.8 | 20k | — |
| T4.9 | 40k | — |
| **Total** | **201k** | — |
| **Budget** | **250k** | |
