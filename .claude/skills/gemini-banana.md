# Gemini 3.1 Flash Image (Nano Banana 2) Skill

Use this skill when generating coloring book pages or covers.

## API basics
- Model: `gemini-3-1-flash-image` via Google AI SDK (`google-genai` Python package)
- Cost: ~$0.039 per image (1024x1024 default), our line-art workflow uses 1024x1280 (8.5:11 ratio)
- Rate limit: ~5 req/s default tier, ~20 req/s paid tier. Enforce with asyncio.Semaphore.
- Output: base64 PNG, decode and save to disk.

## Prompt pattern for COLORING PAGE (interior)
"Black and white coloring book line art for adults. Subject: {SUBJECT}. Style: clean bold outlines, uniform line weight, NO shading, NO gradients, NO grayscale fill. Background: pure white, no patterns. Composition: subject centered, fills 80% of frame, leaves 10% margin on all sides. Detail level: {DETAIL_TIER} (sparse / medium / dense). Aspect: portrait 8.5:11. Negative: no text, no watermarks, no signatures, no shading, no color, no double lines."

## Prompt pattern for COVER
"Coloring book cover illustration, eye-catching, high contrast. Title placeholder area in upper third (we'll overlay text in post). Main subject: {COVER_SUBJECT} in {STYLE_FINGERPRINT} style. Color: vibrant but limited palette ({PALETTE_HINT}). Readable at thumbnail size 200px: bold central element, clear silhouette. Background: {BACKGROUND_HINT}. Aspect: portrait 8.5:11."

## Detail tier mapping
- sparse: 30-50% white space, simple shapes, suitable for kids 4-8
- medium: 15-25% white space, moderate complexity, adult casual
- dense: <10% white space, intricate patterns, mandala/zentangle style

## Quality patterns we've learned (update from policies)
- "Uniform line weight" must be in every prompt or Gemini drifts to varied weights
- Negative prompts work: explicit "NO shading" reduces failures by ~40%
- Composition hint "fills 80% of frame" prevents tiny subjects on big backgrounds
- For figurative subjects (humans, animals): add "anatomically simple, cartoon style" to reduce malformed-anatomy artifacts

## Post-processing always required
1. Convert to grayscale even if already monochrome (normalize)
2. Threshold to pure black/white (eliminates faint gray pixels that print badly)
3. Verify 300 DPI metadata (Pillow can lie about DPI; set explicitly)
4. Resize/canvas to exact 8.625x11.25" at 300 DPI = 2587x3375 px

## When to retry vs kill
- Artifact detected (text, shading, color): retry once with refined prompt
- Composition issue (subject too small, off-center): retry once with stronger composition hint
- Anatomy malformed on figurative: retry once with "simple cartoon style" added
- Failed twice: kill page, try alternative subject from BookPlan's reserve list
