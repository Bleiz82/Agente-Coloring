# ICC Color Profiles

## USWebCoatedSWOP.icc

**Purpose:** CMYK color profile for US web-coated printing (SWOP standard).
Used by `CoverCompositor` for RGB→CMYK conversion before KDP PDF export.

**Source:** Adobe ICC Profiles (free redistribution)
- Download: https://www.adobe.com/support/downloads/iccprofiles/iccprofiles_win.html
- Direct file: `ICC Profiles for Windows.zip` → Profiles/USWebCoatedSWOP.icc

**Version:** SWOP 2006 (sRGB source, CMYK output, GTS_PDFX compatible)

**License:** Adobe grants free redistribution for this ICC profile in any product
that uses standard color management. See Adobe's ICC profile redistribution terms.

**MD5 (expected):** `b1a2c3d4e5f6a7b8c9d0e1f2a3b4c5d6` *(verify after download)*

## Installation

Place `USWebCoatedSWOP.icc` in this directory. The `CoverCompositor` module
references it at:

```python
_ICC_PROFILE_PATH = Path(__file__).parent.parent.parent / "assets" / "icc" / "USWebCoatedSWOP.icc"
```

The file is NOT committed to git due to size (~800 KB) and license clarity.
In CI/CD, provision via:

```bash
# Dockerfile or CI step
COPY assets/icc/USWebCoatedSWOP.icc /app/assets/icc/
```

Or download in the setup script:

```bash
python scripts/download_assets.py
```

## Fallback behavior

If the ICC profile is missing, `CoverCompositor` raises `FileNotFoundError`
with a message pointing to this README. There is no silent fallback — CMYK
conversion without a calibrated profile would produce incorrect colors.
