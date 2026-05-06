---
name: kdp-cover-compositor
description: Compose a fully KDP-compliant paperback or hardcover wrap PDF (back + spine + front) starting from a Gemini-generated cover image and a BookPlan. Handles trim parametric geometry, bleed, safe zones, spine text, barcode reservation, RGB→CMYK conversion, font embedding, PDF/X-1a output, and full validation. Activate this skill whenever code needs to produce a print-ready cover PDF for KDP submission.
---

# KDP Cover Compositor

> **Source of truth**: `KDP_OFFICIAL_SPECS.md` (project root), sections §1, §2, §3, §5, §7.
> **When to use**: After Gemini generates a raw cover image, OR when the publisher needs a print-ready cover PDF.
> **When NOT to use**: For ebook covers (use a separate ebook-cover skill — different requirements).

---

## 1. Critical KDP rules (non-negotiable)

| Rule | Value | Source |
|------|-------|--------|
| File format | Single PDF (back + spine + front in one file) | KDP_OFFICIAL_SPECS §7 |
| Bleed | 0.125" on all 4 sides | §3 |
| Safe zone (text/critical content) | ≥ 0.25" from outer trim edge | §7 |
| Spine safe zone | ≥ 0.0625" from spine fold lines | §5 |
| Spine fold line variance | ±0.0625" must be tolerated | §5 |
| Spine text minimum | Page count ≥ 79 | §5 |
| Barcode reservation | 2" × 1.2" white box, lower-right back cover, ≥ 0.25" inset | §7 |
| Color mode | CMYK (mandatory for print) | §7 |
| Image DPI | ≥ 300, recommended ≤ 600 | §6, §7 |
| Font embedding | Full embed (not subset) | §6, §7 |
| Layers | All flattened | §7 |
| Max file size | 650 MB hard, 40 MB recommended | §7 |
| PDF format | PDF/X-1a preferred | §6 |

Any violation = KDP rejection or quality loss in print.

---

## 2. Cover geometry formulas

### Spine width (inches)

```
spine_width = page_count × paper_multiplier
```

| paper_multiplier | Paper type |
|------------------|------------|
| 0.002252 | White paper, black ink (DEFAULT for B/W coloring) |
| 0.0025 | Cream paper, black ink |
| 0.002347 | Premium color paper |
| 0.002252 | Standard color paper |

Source: `BookPlan.paper_type` enum (introduced in M6.5).

### Full cover dimensions (inches)

```
cover_width  = 0.125 + trim_width + spine_width + trim_width + 0.125
cover_height = 0.125 + trim_height + 0.125
```

Both back and front are full `trim_width` (no separate "back trim").

### Examples (page_count = 75, white paper, multiplier 0.002252)

| Trim | spine_w | cover_w | cover_h |
|------|---------|---------|---------|
| 8.5×11 (LETTER) | 0.169" | 17.294" | 11.25" |
| 8.5×8.5 (SQUARE_LARGE) | 0.169" | 17.294" | 8.75" |
| 8×10 (KIDS) | 0.169" | 16.294" | 10.25" |
| 7×10 (INTERMEDIATE) | 0.169" | 14.294" | 10.25" |
| 6×9 (POCKET) | 0.169" | 12.294" | 9.25" |

### Coordinate system (origin = bottom-left, points = inches × 72)

```
                                                                         
   ┌─[bleed 0.125"]────────────────────────────────────────────────┐    
   │                                                                │   
   │   BACK COVER     │ SPINE │   FRONT COVER                       │   
   │   (trim_w)       │ (sw)  │   (trim_w)                          │   
   │                  │       │                                     │   
   │   ┌─safe─────┐   │       │   ┌─safe──────┐                     │   
   │   │ blurb    │   │       │   │ TITLE     │                     │   
   │   │ bio      │   │       │   │ subtitle  │                     │   
   │   │          │   │       │   │ author    │                     │   
   │   │ ┌──────┐ │   │       │   │           │                     │   
   │   │ │bcode │ │   │       │   │           │                     │   
   │   │ │ wht  │ │   │       │   │           │                     │   
   │   │ └──────┘ │   │       │   └───────────┘                     │   
   │   └──────────┘   │       │                                     │   
   │                                                                │   
   └────────────────────────────────────────────────────────────────┘   
   ↑                  ↑       ↑                                     ↑   
   bleed              fold    fold                                  bleed
                      left    right                                       

   fold_left_x  = bleed + trim_w
   fold_right_x = bleed + trim_w + spine_w
   front_left_x = fold_right_x  (= start of front cover)
   barcode_x    = bleed + trim_w − 0.25 − 2.0   (right-aligned in back, 0.25" from inside fold) 
   barcode_y    = bleed + 0.25                  (0.25" from bottom)
   barcode_box  = 2.0 × 1.2 inches, fill RGB(255,255,255), no stroke
```

---

## 3. Font catalog (bundled in `assets/fonts/`)

All fonts are open-source (OFL or Apache 2.0). Download once, commit to repo.

| Niche category | Title font | Body font | Source |
|----------------|------------|-----------|--------|
| Adult coloring (mandala, zen, geometric) | Playfair Display Bold | Lato Regular | Google Fonts (OFL) |
| Kids coloring | Bebas Neue Bold | Comic Neue Regular | Google Fonts (OFL) |
| Activity / workbook | Montserrat Bold | Open Sans Regular | Google Fonts (OFL) |
| Pocket / travel | Lobster Regular | Source Sans 3 Regular | Google Fonts (OFL) |
| Default fallback | Montserrat Bold | Open Sans Regular | Google Fonts (OFL) |

### Niche → font mapping (keyword detection)

```python
NICHE_FONT_MAP = {
    "mandala": "Adult", "zen": "Adult", "geometric": "Adult",
    "stress relief": "Adult", "meditation": "Adult", "adult": "Adult",
    "kids": "Kids", "children": "Kids", "toddler": "Kids", "preschool": "Kids",
    "kindergarten": "Kids", "boys": "Kids", "girls": "Kids",
    "workbook": "Activity", "activity": "Activity", "educational": "Activity",
    "homeschool": "Activity", "practice": "Activity",
    "travel": "Pocket", "pocket": "Pocket", "mini": "Pocket", "on the go": "Pocket",
}
```

Lookup logic: scan `niche.brief.theme.lower() + " " + niche.brief.audience.lower()` for first matching keyword. Default to "Default" category.

### Font sizing formulas (output in points, 1pt = 1/72 inch)

```
title_pt    = trim_height_pt × 0.075   # clamped to [48, 96]
subtitle_pt = title_pt × 0.40          # clamped to [18, 36]
author_pt   = title_pt × 0.30          # clamped to [14, 28]
spine_pt    = (spine_width_pt - 4.5)   # clamped to [12, 24]; only if page_count ≥ 79
back_blurb_pt = 11
back_bio_pt   = 9
```

KDP minimum interior font is 7pt; cover has no explicit minimum but readability requires ≥ 9pt.

---

## 4. Composition algorithm

```
Input:
  - cover_image_path: Path (RGB PNG from Gemini, must be ≥ 300 DPI in source)
  - book_plan: BookPlan (must have trim_size, paper_type, cover_finish)
  - book_draft: BookDraft (page_count, title, subtitle, author)
  - niche_brief: NicheBrief (for font category selection)
  - output_path: Path (where to write the cover PDF)

Output:
  - CoverCompositionResult Pydantic model with paths, dimensions, validation report

Steps:
  1. Compute geometry
     - trim_w, trim_h ← book_plan.trim_size.{width_inches, height_inches}
     - paper_mult ← book_plan.paper_type.spine_multiplier
     - spine_w ← book_draft.page_count × paper_mult
     - cover_w, cover_h ← formulas in §2
     - all converted to points (× 72)

  2. Spine eligibility
     - If page_count < 79: spine_text_enabled = False, spine_pt = 0
     - Else: spine_text_enabled = True

  3. Font category selection
     - text_for_match ← (niche_brief.theme + " " + niche_brief.audience).lower()
     - For each (keyword, category) in NICHE_FONT_MAP: if keyword in text_for_match → return category
     - Else: "Default"

  4. Canvas creation
     - Create RGB canvas with Pillow at 300 DPI: size = (cover_w × 300, cover_h × 300) pixels
     - Paste Gemini cover image scaled to FRONT COVER region only (right portion of canvas)
     - Generate or render BACK COVER background (use solid color or blurred extension of front art)
     - Render SPINE background (sample dominant color from front art)

  5. Text overlay (Pillow ImageDraw + ImageFont)
     - FRONT: title (top 60% of safe zone), subtitle below title, author at bottom of safe zone
     - SPINE: title text rotated 90° clockwise (reads top-to-bottom on shelf), centered
     - BACK: blurb (top 60% safe zone), bio (bottom 30%), reserve barcode region (bottom-right 2"×1.2" + 0.25" inset)

  6. Barcode area
     - Draw white rectangle: position (back_safe_right - 2.0 - 0.25, bleed + 0.25), size (2.0, 1.2) inches
     - Convert to pixels: × 300
     - No stroke, fill (255, 255, 255)

  7. Validation pre-export (see §5)
     - If any check fails: raise CoverComplianceError with detailed report
     - If only warnings: log and proceed

  8. RGB → CMYK conversion
     - Load ICC profile: assets/icc/USWebCoatedSWOP.icc (bundled)
     - Use Pillow ImageCms.profileToProfile(canvas, srcRGB, dstCMYK, outputMode='CMYK')
     - Embed profile in output

  9. PDF export (ReportLab)
     - Create canvas at exact cover dimensions (cover_w × 72, cover_h × 72) points
     - drawImage at (0, 0) with full canvas
     - Set PDF metadata: /Title (book title), /Producer (ColorForge AI), /Trapped /False
     - Output intent: PDF/X-1a, GTS_PDFX version /PDF/X-1a:2001
     - Embed all fonts (force_embed_subset=False)
     - Disable downsampling
     - Save with optimization

  10. Final validation (post-export)
      - Re-open PDF with pypdf, verify:
        * Page count == 1
        * Page size matches expected (cover_w × cover_h points, ±1 pt tolerance)
        * Color space includes /DeviceCMYK or /ICCBased with CMYK profile
        * All fonts /FontFile or /FontFile2/3 present
      - File size < 40 MB (warning) or < 650 MB (hard)

  11. Return CoverCompositionResult
```

---

## 5. Validation rules (CoverComplianceValidator)

Implemented as standalone class, called automatically at step 7 of the algorithm.

```python
class CoverValidationCheck(StrEnum):
    BLEED_PRESENT = "bleed_present"
    SAFE_ZONE_TEXT = "safe_zone_text"
    BARCODE_AREA_WHITE = "barcode_area_white"
    DPI_300 = "dpi_300"
    SPINE_ELIGIBILITY = "spine_eligibility"
    SPINE_MARGIN = "spine_margin"
    FONT_EMBEDDING = "font_embedding"
    NO_TRANSPARENCY = "no_transparency"
    COLOR_MODE_CMYK = "color_mode_cmyk"
    NO_METADATA_LEAK = "no_metadata_leak"
    FILE_SIZE = "file_size"
    CONTRAST_RATIO = "contrast_ratio"

class CoverValidationReport(BaseModel):
    passed: list[CoverValidationCheck]
    warnings: list[tuple[CoverValidationCheck, str]]
    failures: list[tuple[CoverValidationCheck, str]]
    overall_verdict: Literal["pass", "warn", "fail"]
```

### Per-check logic

| Check | Implementation | Severity if failed |
|-------|----------------|---------------------|
| BLEED_PRESENT | Cover canvas dimensions ≥ trim + 0.25" w + 0.25" h | FAIL |
| SAFE_ZONE_TEXT | All text bounding boxes ≥ 0.25" from outer edges | FAIL |
| BARCODE_AREA_WHITE | Sample 100 pixels in barcode region, > 95% must be RGB(255,255,255) ± 5 | FAIL |
| DPI_300 | Source image PIL `info['dpi']` ≥ 300 in both axes | FAIL |
| SPINE_ELIGIBILITY | If spine has text, page_count ≥ 79 | FAIL |
| SPINE_MARGIN | Spine text bounding box has ≥ 0.0625" margin from spine fold lines | FAIL |
| FONT_EMBEDDING | Re-parse PDF, all fonts must have /FontFile* present | FAIL |
| NO_TRANSPARENCY | PDF has no /SMask or /CA != 1 entries | WARN |
| COLOR_MODE_CMYK | PDF /ColorSpace contains DeviceCMYK or ICC CMYK profile | FAIL |
| NO_METADATA_LEAK | PDF /Metadata has no /Author other than book author | WARN |
| FILE_SIZE | size < 40 MB → pass, 40-650 MB → warn, > 650 MB → fail | depends |
| CONTRAST_RATIO | WCAG AA: text vs background luminance ratio ≥ 4.5:1 | WARN |

If any FAIL → raise `CoverComplianceError` with full report.
If only WARN → log via loguru `logger.warning()` and proceed.
All-pass → log `logger.info("cover validation: all checks passed")`.

---

## 6. Reference Python implementation (target module)

File: `apps/agents/colorforge_agents/generator/cover_compositor.py`

```python
from pathlib import Path
from typing import Final
from PIL import Image, ImageCms, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import inch
import pypdf

from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import CoverComplianceError

_ASSETS_FONTS_DIR: Final = Path(__file__).parent.parent.parent / "assets" / "fonts"
_ASSETS_ICC_DIR: Final = Path(__file__).parent.parent.parent / "assets" / "icc"
_ICC_PROFILE_PATH: Final = _ASSETS_ICC_DIR / "USWebCoatedSWOP.icc"
_BLEED_IN: Final = 0.125
_SAFE_INSET_IN: Final = 0.25
_BARCODE_W_IN: Final = 2.0
_BARCODE_H_IN: Final = 1.2
_SPINE_TEXT_MIN_PAGES: Final = 79
_RENDER_DPI: Final = 300


class CoverCompositionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: Path
    cover_width_pt: float
    cover_height_pt: float
    spine_width_pt: float
    spine_text_included: bool
    font_category: str
    file_size_bytes: int
    validation_report: "CoverValidationReport"  # see §5


class CoverCompositor:
    """KDP-compliant cover compositor.

    Produces a single-PDF cover (back + spine + front) from a Gemini cover
    image and a BookPlan, applying all KDP geometry, color, and font rules.
    """

    def __init__(self, book_plan: BookPlan) -> None:
        self.plan = book_plan
        self.trim_w_in = book_plan.trim_size.width_inches
        self.trim_h_in = book_plan.trim_size.height_inches
        self.paper_mult = book_plan.paper_type.spine_multiplier

    def compose(
        self,
        cover_image: Path,
        draft: BookDraft,
        niche: NicheBrief,
        output_path: Path,
    ) -> CoverCompositionResult:
        """Build a print-ready cover PDF.

        Raises:
            CoverComplianceError: if any P0 validation check fails.
            FileNotFoundError: if the cover image, ICC profile, or font is missing.
        """
        spine_w_in = draft.page_count * self.paper_mult
        cover_w_in = 2 * _BLEED_IN + 2 * self.trim_w_in + spine_w_in
        cover_h_in = 2 * _BLEED_IN + self.trim_h_in
        spine_eligible = draft.page_count >= _SPINE_TEXT_MIN_PAGES
        font_cat = self._select_font_category(niche)

        # ... (full implementation per §4 algorithm)
```

The full implementation is ~600 LOC and is generated at M8 by the implementer subagent. This skill provides the spec; the code generation reuses these formulas verbatim.

---

## 7. Common pitfalls (KDP rejection causes)

These are the top reasons KDP rejects covers. The compositor must prevent each.

| Pitfall | Prevention |
|---------|------------|
| Layers not flattened | Always render to a single PIL `Image` before PDF export |
| Encrypted PDF | Never set ReportLab `encrypt=` parameter |
| Filename with emoji or non-ASCII | Sanitize: `output_path.name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)` |
| Crop/trim marks | ReportLab default has none; verify no `setLineWidth + line()` near corners |
| Missing title on front | Hard-fail validation if title not rendered |
| Barcode area covered | Step 6 always reserves white box |
| Spine text on < 79 pages | Step 2 disables spine text if ineligible |
| Inset too small | Use `_SAFE_INSET_IN = 0.25` constant, never let text bbox cross |
| RGB output (not CMYK) | Step 8 mandatory CMYK conversion |
| Subset font embedding | ReportLab: register fonts with `pdfmetrics.registerFont(TTFont(name, path, validate=True, subfontIndex=0))` and avoid subset by writing `Producer` metadata triggering full embed |
| Hard edges on spine | Use gradient or matched background color across spine fold ±0.0625" tolerance |
| White border at trim | Image must extend beyond trim by 0.125" on all sides → ensure source PIL image is full `cover_w_in × cover_h_in × 300px` |

---

## 8. Test strategy (for the implementer subagent)

When implementing `cover_compositor.py`, generate `tests/test_cover_compositor.py` with at minimum:

1. `test_geometry_letter_size_75_pages` — verify cover_w, cover_h, spine_w within ±0.001"
2. `test_geometry_all_5_trim_sizes` — parametrized over TrimSize enum
3. `test_spine_text_enabled_at_79_pages` — boundary
4. `test_spine_text_disabled_at_78_pages` — boundary
5. `test_font_category_mandala` → "Adult"
6. `test_font_category_kids` → "Kids"
7. `test_font_category_default_fallback` → "Default"
8. `test_barcode_area_is_white` — render, sample pixels in barcode region, assert mean RGB > 250
9. `test_low_dpi_image_raises` — feed 150 DPI image → CoverComplianceError
10. `test_cmyk_conversion` — output PDF /ColorSpace contains DeviceCMYK
11. `test_pdf_under_40_mb_warning` → 50 MB → warn, < 40 MB → pass
12. `test_compose_full_pipeline` — golden image test on 6×9 75-page mandala niche
13. `test_paper_type_cream_spine_calculation` — verify multiplier 0.0025
14. `test_safe_zone_violation_raises` — force text outside safe zone → fail
15. `test_filename_sanitization` — emoji in title doesn't break export

Coverage target: ≥ 90% on `cover_compositor.py`.

---

## 9. Dependencies to add (M8 implementation)

In `apps/agents/pyproject.toml`:

```toml
[project]
dependencies = [
    # ...existing...
    "pypdf>=4.0.0",  # already present
    # Pillow already includes ImageCms; no new deps strictly required
]
```

Bundled assets to commit:

- `assets/fonts/PlayfairDisplay-Bold.ttf`
- `assets/fonts/Lato-Regular.ttf`
- `assets/fonts/BebasNeue-Bold.ttf`
- `assets/fonts/ComicNeue-Regular.ttf`
- `assets/fonts/Montserrat-Bold.ttf`
- `assets/fonts/OpenSans-Regular.ttf`
- `assets/fonts/Lobster-Regular.ttf`
- `assets/fonts/SourceSans3-Regular.ttf`
- `assets/icc/USWebCoatedSWOP.icc` (downloadable from Adobe ICC profiles)

Total bundled assets: ~5-7 MB. Acceptable for repo (all under MIT/OFL/Apache licenses, redistribution allowed).

---

## 10. Activation triggers

This skill activates automatically when:
- Code references `CoverCompositor`, `compose_cover`, `cover_compositor`, `cover.pdf`
- The user mentions "KDP cover", "wrap cover", "spine + front + back", "case laminate cover", "paperback cover compliance"
- The implementer subagent is asked to generate cover-related code

---

## 11. Decisions log (for traceability)

| Decision | Rationale | Date |
|----------|-----------|------|
| Always CMYK | KDP §7 mandates CMYK; RGB rejected at print | 2026-05-06 |
| ICC profile = USWebCoatedSWOP | Industry standard for US offset printing | 2026-05-06 |
| 5 trim sizes only (not 15) | YAGNI for coloring books; expand if niche evolves | 2026-05-06 |
| Bundled fonts (not API) | Offline reliability, no rate limits | 2026-05-06 |
| Strict validation by default | Prevents wasted KDP quota; user can opt out via `strict=False` | 2026-05-06 |
| White barcode box even with own ISBN | Defensive: if user later switches to KDP free ISBN, no rework | 2026-05-06 |

---

**End of skill.** Total: ~700 lines, ~8000 tokens. When activated, the model loads only this file (not the full project context), keeping implementation accurate and token-efficient.
