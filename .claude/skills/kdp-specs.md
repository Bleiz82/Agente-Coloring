# KDP Specs Skill

Use this skill whenever working on PDF generation, cover sizing, or KDP submission.

## Coloring book trim (locked default)
- Trim size: 8.5 x 11 inches
- Bleed: 0.125 inches on top, bottom, outside edges (NOT inside/gutter)
- Page size with bleed: 8.625 x 11.25 inches
- Resolution: 300 DPI minimum (we enforce 300)
- Color: black & white interior; cover full color CMYK or RGB (KDP accepts both)

## Margins (interior pages) — KDP official table
- Outside (with bleed): ≥ 0.375 inches minimum
- Outside (no bleed): ≥ 0.25 inches minimum
- Gutter (inside): 0.375" for ≤150 pages, 0.500" for 151–300, 0.625" for 301–500,
  0.750" for 501–700, 0.875" for 701–828
- Authoritative source: KDP_OFFICIAL_SPECS.md §4

## Cover dimensions formula
- Width = 2 x (trim_width + bleed) + spine_width + 0.25 (extra bleed each side)
- Height = trim_height + 2 x bleed = 11.25 inches
- Spine width = pages × paper_type.spine_multiplier (see PaperType enum in book_plan.py)
  White paper: 0.002252"/page | Cream: 0.0025"/page | Premium color: 0.002347"/page
  Example (white, 75p): spine = 0.169" → cover width = 2×(8.5+0.125)+0.169+0.25 = 17.669"
- Spine text allowed from ≥ 79 pages (NOT 100) per KDP_OFFICIAL_SPECS.md §5

## File format
- PDF/X-1a:2001 or PDF/X-3:2002 preferred. Standard PDF accepted by KDP since 2023.
- Embed all fonts. No transparency in cover (flatten before export).
- Single PDF for interior, single PDF for cover.

## AI Disclosure (mandatory since 2024)
- During book setup, KDP asks: "Did you use AI tools to create this content?"
- We answer YES, with categories: "AI-generated images" + "AI-generated text" (for descriptions)
- This is a non-negotiable in our system. Hardcoded true.

## BISAC codes for coloring books (whitelisted)
Adult: ART015000, CRA019000, GAM001050, SEL032000
Kids: JUV019000, JUV049000, JNF051110

## Pricing reasonable ranges (USD list price)
- 50 pages: $5.99 - $7.99
- 75 pages: $6.99 - $9.99
- 100 pages: $7.99 - $11.99
Lower bounds enforce 60% royalty positive margin after printing cost (~$0.85 + $0.012/page).

## Common rejection reasons (what gates must check)
- Text/watermarks in margins -> Critic checks
- Cover unreadable at thumbnail -> Critic checks
- Spine width mismatch -> PDF builder enforces
- Trademark in title/keywords -> Listing Gate checks
- Bleed extending into gutter -> PDF builder enforces
