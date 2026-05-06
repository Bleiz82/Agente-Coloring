---
name: kdp-frontmatter
description: Generate KDP-compliant front matter (title page, copyright, AI disclosure, how-to-use, dedication) and back matter (thank-you, about-author, also-by) for a coloring book interior PDF. Ensures metadata-cover-interior consistency required by KDP manual review. Activate this skill whenever code needs to assemble the non-coloring pages of a book interior.
---

# KDP Front Matter & Back Matter Generator

> **Source of truth**: `KDP_OFFICIAL_SPECS.md` (project root), sections §6, §8, §9, §15.
> **When to use**: After Generator produces coloring page images, BEFORE `pdf_assembler.assemble_manuscript()` builds the final interior PDF.
> **When NOT to use**: For ebook interiors (different layout rules — reflowable text).

---

## 1. Purpose

KDP's manual review (KDP_OFFICIAL_SPECS §15) requires that **title, author, ISBN, and edition information in the manuscript file exactly match the metadata entered during title setup**. A coloring book consisting only of image pages will:

- Risk rejection for "missing title page" (poor customer experience)
- Lack mandatory AI disclosure visible to customers
- Provide no copyright notice (legal exposure)
- Fail to meet professional publishing expectations

This skill produces a structured set of pages prepended (front matter) and appended (back matter) to the coloring image stack, so the final PDF is fully KDP-compliant and customer-ready.

---

## 2. Standard book structure for coloring books

```
┌─────────────────────────────────┐
│  Page i    │ Half-title page    │ ← optional, only if page_count ≥ 60
│  Page ii   │ Blank              │
│  Page iii  │ FULL TITLE PAGE    │ ← MANDATORY
│  Page iv   │ COPYRIGHT PAGE     │ ← MANDATORY (includes AI disclosure)
│  Page v    │ DEDICATION         │ ← optional (BookPlan.include_dedication)
│  Page vi   │ Blank              │
│  Page vii  │ HOW TO USE         │ ← MANDATORY for coloring books
│  Page viii │ Blank or section   │
│                                 │
│  Pages 1-N │ COLORING PAGES     │ ← from Generator
│                                 │
│  Page N+1  │ THANK YOU          │ ← MANDATORY
│  Page N+2  │ Blank              │
│  Page N+3  │ ABOUT THE AUTHOR   │ ← MANDATORY
│  Page N+4  │ ALSO BY THIS AUTHOR│ ← optional, only if author has ≥ 2 books
└─────────────────────────────────┘
```

### Pagination rules (KDP §6, §15)

- All pages count toward `page_count` (front matter is not free)
- Even pages = LEFT (verso), odd pages = RIGHT (recto)
- Title page = recto (right-hand) → page iii or page 1 in some conventions
- Copyright = verso (left-hand) → directly after title page
- Max 4 consecutive blank pages mid-book; max 10 at the end
- Use Roman numerals (i, ii, iii) for front matter, Arabic (1, 2, 3) starting from first coloring page (recommended but optional)

For ColorForge automation simplicity, this skill produces **all-Arabic numbering starting from page 1** (compliant, just less traditional).

---

## 3. Page-by-page specifications

### 3.1 Title page (MANDATORY)

**Layout**:
```
                                              
                                              
                                              
            [BOOK TITLE]                      
                                              
            [Subtitle]                        
                                              
                                              
                                              
                                              
                                              
                                              
                                              
            [Author Name]                     
                                              
                                              
                                              
            [ColorForge Studio]               
            (publisher / imprint)             
                                              
```

**Specs**:
- Trim-size aware (centered horizontally, ~30% from top vertically)
- Title: same font as cover (font_category from cover compositor), 36-48pt
- Subtitle: 18-22pt, lighter weight
- Author: 14-16pt, italic
- Imprint: 10pt, sans-serif

**Constraint**: Title text must match `BookDraft.title` exactly. Author must match `BookDraft.author`. Subtitle must match `BookDraft.subtitle` if present.

### 3.2 Copyright page (MANDATORY)

Layout:
```
[Book Title]
Copyright © [YEAR] [Author Name]
All rights reserved.

ISBN: [ISBN-13 or "Not assigned"]

Published by [Imprint]
First edition: [YYYY-MM]

────────────────────────────────────────

AI DISCLOSURE
This book contains AI-generated content. The
illustrations were created using AI image
generation tools. The author has reviewed,
selected, and curated all content to ensure
quality and originality.

────────────────────────────────────────

No part of this publication may be reproduced,
distributed, or transmitted in any form or by
any means, including photocopying, recording,
or other electronic or mechanical methods,
without the prior written permission of the
publisher, except in the case of brief
quotations embodied in critical reviews.

For permission requests, contact:
[contact_email or website]

Printed in [Country] by Amazon KDP.
```

**Specs**:
- Body font: 9-10pt serif (Lato Regular or system equivalent)
- Center-aligned title block, left-aligned legal text
- Margins per KDP §4 (gutter rules apply)
- AI Disclosure section is **NON-NEGOTIABLE** when `book_plan.ai_disclosure = True` (always True for ColorForge output)

**Variables to fill**:
- `{title}` ← BookDraft.title
- `{year}` ← current year
- `{author}` ← BookDraft.author
- `{isbn}` ← BookDraft.isbn or "Not assigned" (low-content fallback — but coloring books are NOT low-content per KDP §14)
- `{imprint}` ← "ColorForge Studio" or BookPlan.imprint
- `{publication_month}` ← "{year}-{MM}" of submission date
- `{contact}` ← static config (e.g., "support@colorforgeai.com")
- `{country}` ← "United States" (KDP default)

### 3.3 Dedication (OPTIONAL)

Only included if `BookPlan.include_dedication = True` and `BookPlan.dedication_text` is non-empty.

Layout:
```
                                          



              For [name],                    
              [optional second line]         
                                              


                                          
```

**Specs**:
- Centered both horizontally and vertically
- Italic serif, 14-16pt
- Single page, no page number visible

### 3.4 How-to-use page (MANDATORY for coloring books)

Layout:
```
HOW TO USE THIS BOOK

[Niche-aware introductory paragraph, 2-3 sentences]

TIPS FOR THE BEST EXPERIENCE

• [tip 1, niche-specific]
• [tip 2, niche-specific]
• [tip 3, niche-specific]
• [tip 4, generic]

RECOMMENDED COLORING TOOLS

• Colored pencils (e.g., Prismacolor, Faber-Castell)
• Fine-tip markers (e.g., Tombow, Staedtler)
• Gel pens for accents
• Watercolor pencils (avoid heavy water — paper is print-grade, not watercolor)

A NOTE ON PAPER

This book is printed on standard KDP paper.
For best results with markers, place a blank
sheet behind each page to prevent bleed-through.

────────────────────────────────────────

Enjoy your creative journey!
```

**Specs**:
- Heading: 18pt bold sans-serif
- Body: 11pt serif
- Bullet list with hanging indent
- Single page if possible (10pt body if content overflows)

**Niche-aware customization** (selected by Strategist or Listing Agent):

| Niche category | Intro paragraph template |
|----------------|---------------------------|
| Adult / mandala / zen | "Welcome to your stress-relief sanctuary. The intricate mandalas in this book are designed to slow your breathing, center your focus, and bring a meditative calm to your day." |
| Kids | "Get ready for hours of fun! These big, simple designs are perfect for little hands learning to color inside the lines. There's no wrong way to color." |
| Activity / educational | "This workbook combines coloring with learning. Each page is designed to engage both creativity and curiosity, making practice feel like play." |
| Travel / pocket | "Compact and ready for adventure. Whether you're on a plane, train, or waiting room, these pages are your portable creative escape." |
| Default | "Welcome to your coloring journey. Take your time, choose your favorite tools, and enjoy the meditative flow of bringing each page to life." |

**Niche-aware tip lists**:

| Niche | Tip examples |
|-------|--------------|
| Adult | "Start with the outermost ring and work inward — it builds focus." / "Use a limited palette (3-5 colors) for a more harmonious result." / "Try shading with two tones of the same color for depth." |
| Kids | "Pick your favorite color first!" / "Coloring outside the lines is okay — your art, your rules." / "Try rainbow order if you can't decide." |
| Activity | "Read any text on the page before you color." / "Save the answer key — color it last." / "Track your progress in the back of the book." |
| Travel | "Use travel-friendly tools (no liquid markers)." / "Snap a photo of finished pages — share with #ColorForge." / "Each page is a memory of where you colored it." |

### 3.5 Coloring pages (provided by Generator, NOT this skill)

Inserted as-is between front matter and back matter. This skill only provides the wrapping pages.

### 3.6 Thank-you page (MANDATORY)

Layout:
```
                                          



        THANK YOU                             
                                              
        for choosing this book.               
                                              
        If you enjoyed your coloring          
        journey, a brief review on            
        Amazon would mean the world.          
                                              
        Your feedback helps fellow            
        colorists discover books              
        they'll love.                         
                                              


                                          
```

**Specs**:
- Centered vertically and horizontally
- Heading: 24pt bold
- Body: 14pt
- No specific link to Amazon (KDP §8 prohibits URLs in metadata; gentle in-book request is allowed)
- **MUST NOT** include phone, email, URL → KDP rejects descriptions with these, and being conservative protects the manuscript too

### 3.7 About-the-author page (MANDATORY)

Layout:
```
ABOUT THE AUTHOR

[Author Name]

[Bio paragraph 1: who they are, ~50 words]

[Bio paragraph 2: what they create, ~40 words]

[Optional: brief sentence about other books or themes]

[Optional: Instagram / website handle WITHOUT URL — e.g., "Find more on Instagram @authorhandle"]
```

**Specs**:
- Heading: 20pt bold sans-serif
- Author name: 16pt
- Body: 11pt serif
- 1 page total
- For ColorForge: bio is generic / persona-based, generated by Strategist or pre-configured per `account.brand_persona`

**Brand persona templates** (one per KDP account):

| Persona | Bio template |
|---------|--------------|
| Mindful artist | "[Name] is a mindful artist who believes coloring is the simplest path to creative joy. Her designs invite you to slow down, breathe, and rediscover the meditative magic of pencils on paper." |
| Studio brand | "[Name] is a small independent studio dedicated to creating coloring books that delight, challenge, and relax. Each title is crafted with care for colorists of every level." |
| Kids' creator | "[Name] makes coloring books for the youngest artists. With big, friendly designs and themes kids love, every page is an invitation to play and create." |
| Educational | "[Name] designs activity books that turn learning into adventure. Her work bridges creativity and curiosity, helping young minds grow one colorful page at a time." |

Selected by `BookPlan.account.brand_persona`.

### 3.8 Also-by page (OPTIONAL)

Only included if `BookDraft.author` has ≥ 2 published titles in the database.

Layout:
```
ALSO BY [AUTHOR NAME]

• [Title 1]
• [Title 2]
• [Title 3]

Find them all on Amazon.
```

**Specs**:
- Heading: 18pt
- List: 12pt
- 1 page
- Pulls from `Book.author = current_author AND state = PUBLISHED` query

---

## 4. Layout specifications (apply to all front/back matter pages)

### Page dimensions

Same as coloring interior:
- `page_width = trim_width + 0.125"` (bleed)
- `page_height = trim_height + 0.25"` (bleed both top and bottom)

Front matter pages do NOT need bleed for backgrounds (text-only). But the page size must match the bleed-extended size to be in the same PDF as the bleed-enabled coloring pages.

### Margins (per KDP §4 gutter table)

Same gutter rules as coloring interior:

| Page count | Inside (gutter) | Outside (with bleed) |
|-----------|-----------------|----------------------|
| 24-150 | 0.375" | 0.375" |
| 151-300 | 0.5" | 0.375" |
| 301-500 | 0.625" | 0.375" |

Note: even though front matter pages have no bleed *content*, they share the same page geometry as the rest of the PDF. Margins must respect the gutter for the total page_count (front + coloring + back).

### Fonts

| Use | Font | Size |
|-----|------|------|
| Page heading | Montserrat Bold | 18-24pt |
| Title page (book title) | (cover font_category title font) | 36-48pt |
| Body text | Lato Regular | 11pt |
| Small print (copyright legal) | Lato Regular | 9pt |
| Italic accents (dedication) | Lato Italic | 14pt |

All fonts bundled in `assets/fonts/` (shared with kdp-cover-compositor skill).

### Page numbering

- Roman numerals i-viii on front matter (or omit, simpler)
- Arabic numerals 1-N on coloring pages
- Arabic continuation on back matter
- Page numbers at bottom-center, 9pt, 0.25" from bottom edge
- **NEVER** on title page, copyright page, or dedication (visual cleanliness)

For ColorForge MVP: omit page numbers entirely (acceptable for low-content-style books, simplifies layout). Add in M8 if customer feedback requests them.

---

## 5. composeManuscript algorithm

```
Input:
  - book_plan: BookPlan (trim_size, paper_type, page_count, account.brand_persona,
                          include_dedication, dedication_text, isbn)
  - book_draft: BookDraft (title, subtitle, author, page_count after coloring,
                            coloring_image_paths)
  - niche_brief: NicheBrief (theme, audience, for how-to-use customization)
  - publisher_info: dict (imprint, contact, country, year)
  - output_path: Path

Output:
  - Path to assembled interior PDF (front matter + coloring + back matter)

Steps:
  1. Compute total page count
     - front_pages = count_front_matter(book_plan)  # 4-7 pages
     - coloring_pages = len(book_draft.coloring_image_paths)
     - back_pages = count_back_matter(book_plan)    # 2-4 pages
     - total = front_pages + coloring_pages + back_pages

  2. Validate KDP minimums
     - assert total >= 24 (KDP §6)
     - assert total <= 828 (KDP §6 paperback)
     - assert no run of 5+ blank pages (KDP §15)

  3. Render front matter to single multi-page PDF (front_matter.pdf)
     - For each page in [title, copyright, dedication?, how_to_use]:
       - Use ReportLab canvas at exact page geometry
       - Render text per §3 specs
       - Embed all fonts
       - Add page break between pages (canvas.showPage())

  4. Render back matter to single multi-page PDF (back_matter.pdf)
     - Same approach: [thank_you, about_author, also_by?]

  5. Concatenate via pypdf
     - merger = pypdf.PdfWriter()
     - merger.append(front_matter.pdf)
     - For img in coloring_image_paths:
         convert img to single-page PDF via existing pdf_assembler logic
         merger.append(...)
     - merger.append(back_matter.pdf)
     - merger.write(output_path)

  6. Validation
     - Re-open output, assert page count == total
     - Assert all fonts embedded
     - Assert file size < 650 MB
     - Assert no blank-page-run violation
     - Assert title text on title page matches book_draft.title (OCR or text extraction check)

  7. Return output_path
```

---

## 6. Reference Python implementation

File: `apps/agents/colorforge_agents/generator/front_matter.py`

```python
from datetime import datetime
from pathlib import Path
from typing import Final
from pydantic import BaseModel, ConfigDict
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdf

from colorforge_agents.contracts.book_plan import BookPlan
from colorforge_agents.contracts.book_draft import BookDraft
from colorforge_agents.contracts.niche_brief import NicheBrief
from colorforge_agents.exceptions import FrontMatterError

_ASSETS_FONTS_DIR: Final = Path(__file__).parent.parent.parent / "assets" / "fonts"
_BLEED_IN: Final = 0.125

class FrontMatterAssemblyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: Path
    page_count: int
    front_matter_pages: int
    coloring_pages: int
    back_matter_pages: int
    total_size_bytes: int


class FrontMatterAssembler:
    """Assemble KDP-compliant front matter and back matter for a coloring book.

    Produces a complete interior PDF combining title page, copyright (with AI
    disclosure), how-to-use, the coloring image stack, thank-you, and
    about-author pages.
    """

    def __init__(self, book_plan: BookPlan) -> None:
        self.plan = book_plan
        self._register_fonts()

    def assemble(
        self,
        draft: BookDraft,
        niche: NicheBrief,
        publisher_info: dict[str, str],
        output_path: Path,
    ) -> FrontMatterAssemblyResult:
        """Build complete interior PDF.

        Raises:
            FrontMatterError: if total page count violates KDP min/max.
            FileNotFoundError: if any required font is missing.
        """
        # ... implementation per §5 algorithm
```

Full implementation ~600 LOC, generated at M8 by implementer subagent.

---

## 7. Validation checklist (auto-run after assembly)

- [ ] `total_pages >= 24` (KDP §6)
- [ ] `total_pages <= 828` (KDP §6 paperback)
- [ ] Title on title page == `BookDraft.title` (string match, exact)
- [ ] Author on title page == `BookDraft.author`
- [ ] Copyright year == current year (or BookPlan.publication_year)
- [ ] AI disclosure present and contains the literal phrase "AI-generated"
- [ ] No URLs, no email addresses, no phone numbers anywhere in front/back matter
- [ ] All fonts embedded (re-parse with pypdf, assert no missing /FontFile)
- [ ] No run of ≥ 5 consecutive blank pages mid-book
- [ ] No run of ≥ 11 consecutive blank pages at end
- [ ] Margins respect gutter rules for total `page_count`
- [ ] File size < 650 MB

If any FAIL → raise `FrontMatterError` with the failed check list.

---

## 8. Niche-aware text customization

The Listing Agent or Strategist provides:
- `niche.brief.theme` (e.g., "ocean mandala", "kids dinosaurs", "travel coloring")
- `niche.brief.audience` (e.g., "adults", "children 6-8", "travelers")

The assembler matches against the niche maps in §3.4 to pick the appropriate intro paragraph and tip list. If no match → use "Default" templates.

This ensures every book feels custom-crafted rather than mass-produced, improving customer reviews and reducing return rates.

---

## 9. Test strategy

When implementing `front_matter.py`, generate `tests/test_front_matter.py` with:

1. `test_assemble_full_book_75_pages` — end-to-end smoke test
2. `test_title_page_contains_title` — text extraction with pypdf, assert title present
3. `test_copyright_contains_ai_disclosure` — assert "AI-generated" substring
4. `test_no_dedication_when_disabled` — `include_dedication=False` → page absent
5. `test_dedication_when_enabled` — page rendered with dedication_text
6. `test_how_to_use_adult_persona` — niche="mandala" → adult intro template
7. `test_how_to_use_kids_persona` — niche="kids" → kids intro template
8. `test_how_to_use_default_fallback` — unknown niche → default template
9. `test_about_author_per_persona` — 4 personas → 4 distinct bio outputs
10. `test_also_by_omitted_for_first_book` — author has no other published titles → page absent
11. `test_also_by_included_for_returning_author` — ≥ 2 titles → page present with list
12. `test_total_page_count_arithmetic` — front + coloring + back == reported total
13. `test_min_24_pages_enforced` — try with 5 coloring pages → FrontMatterError
14. `test_no_url_in_back_matter` — regex scan, assert no http/www/@/.com
15. `test_font_embedding_verified` — re-parse PDF, all fonts have /FontFile*
16. `test_blank_page_run_violation` — synthetic case → FrontMatterError
17. `test_consistency_with_metadata` — title in PDF must match BookDraft.title

Coverage target: ≥ 90% on `front_matter.py`.

---

## 10. Integration with existing modules

### Generator integration (M4)

`generator.py` currently calls `pdf_assembler.assemble_manuscript(image_paths, output_path)`. After M8 implementation of this skill, the call sequence becomes:

```python
# Old (M4):
result = pdf_assembler.assemble_manuscript(image_paths, output_path)

# New (M8 with front matter):
fm_assembler = FrontMatterAssembler(book_plan)
result = fm_assembler.assemble(
    draft=book_draft,
    niche=niche_brief,
    publisher_info={
        "imprint": "ColorForge Studio",
        "contact": "support@colorforgeai.com",
        "country": "United States",
        "year": str(datetime.now().year),
    },
    output_path=output_path,
)
```

The old `pdf_assembler.assemble_manuscript()` becomes an internal helper called by `FrontMatterAssembler` for the coloring page block.

### BookPlan extensions needed (already in M6.5 or to add in M8)

```python
class BookPlan(BaseModel):
    # ...existing M6.5 fields (trim_size, paper_type, cover_finish)...

    include_dedication: bool = False
    dedication_text: str | None = None
    imprint: str = "ColorForge Studio"
    publication_year: int = Field(default_factory=lambda: datetime.now().year)
```

---

## 11. Activation triggers

This skill activates automatically when:
- Code references `FrontMatterAssembler`, `front_matter`, `assemble_manuscript_with_frontmatter`, "title page", "copyright page", "AI disclosure page"
- The user mentions "front matter", "back matter", "title page", "copyright", "about the author", "thank you page", "interior layout"
- The implementer subagent is asked to generate interior PDF code beyond bare image stacking

---

## 12. Decisions log

| Decision | Rationale | Date |
|----------|-----------|------|
| AI disclosure mandatory in copyright | KDP §9: AI-generated content must be disclosed; including in book is best practice beyond just KDP form | 2026-05-06 |
| 4 brand personas (mindful, studio, kids, educational) | Covers 95% of coloring book niches; expandable | 2026-05-06 |
| No page numbers in MVP | Simplifies layout; coloring books often omit them; can add in M8 | 2026-05-06 |
| Niche-aware how-to-use | Differentiates books, reduces "samey" complaints | 2026-05-06 |
| Dedication optional | Most ColorForge titles are not personalized; opt-in via BookPlan | 2026-05-06 |
| No URLs anywhere in interior | Defensive: KDP §8 prohibits in description, conservative to extend to interior | 2026-05-06 |
| Generic "support@colorforgeai.com" placeholder | Real contact email configured per account in M7 dashboard | 2026-05-06 |
| Bundled fonts shared with cover skill | DRY; same `assets/fonts/` directory | 2026-05-06 |

---

**End of skill.** Total: ~750 lines, ~9000 tokens. Activates only when needed; keeps implementer context focused.
