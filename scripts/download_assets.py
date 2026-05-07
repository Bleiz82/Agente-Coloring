"""Download bundled font and ICC assets for ColorForge agents.

Run once during dev setup or in CI before running the agent test suite.

Usage:
    python scripts/download_assets.py
    python scripts/download_assets.py --fonts-only
    python scripts/download_assets.py --icc-only
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_FONTS_DIR = _REPO_ROOT / "apps" / "agents" / "assets" / "fonts"
_ICC_DIR = _REPO_ROOT / "apps" / "agents" / "assets" / "icc"

# Google Fonts static URLs (stable, versioned CDN paths)
_FONT_URLS: list[tuple[str, str]] = [
    # (filename, url)
    (
        "PlayfairDisplay-Bold.ttf",
        "https://fonts.gstatic.com/s/playfairdisplay/v37/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKdFvUDQ.ttf",
    ),
    (
        "PlayfairDisplay-Regular.ttf",
        "https://fonts.gstatic.com/s/playfairdisplay/v37/nuFiD-vYSZviVYUb_rj3ij__anPXDTnohkk73g.ttf",
    ),
    (
        "Lato-Regular.ttf",
        "https://fonts.gstatic.com/s/lato/v24/S6uyw4BMUTPHjx4wXiWtFCc.ttf",
    ),
    (
        "Lato-Italic.ttf",
        "https://fonts.gstatic.com/s/lato/v24/S6u8w4BMUTPHjxsAXC-v.ttf",
    ),
    (
        "Lato-Bold.ttf",
        "https://fonts.gstatic.com/s/lato/v24/S6u9w4BMUTPHh6UVSwiPHA.ttf",
    ),
    (
        "BebasNeue-Regular.ttf",
        "https://fonts.gstatic.com/s/bebasneue/v14/JTUSjIg69CK48gW7PXoo9Wdhyzbi.ttf",
    ),
    (
        "ComicNeue-Regular.ttf",
        "https://fonts.gstatic.com/s/comicneue/v8/4UaErEJDsxBrF37olUeDx63j5pN1MwI.ttf",
    ),
    (
        "Montserrat-Bold.ttf",
        "https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCuM73w5aXp-p7K4KLg.ttf",
    ),
    (
        "Montserrat-Regular.ttf",
        "https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtZ73w5aXp-p7K4KLg.ttf",
    ),
    (
        "OpenSans-Regular.ttf",
        "https://fonts.gstatic.com/s/opensans/v40/memvYaGs126MiZpBA-UvWbX2vVnXBbObj2OVZyOOSr4dVJWUgsjZ0C24.ttf",
    ),
    (
        "Lobster-Regular.ttf",
        "https://fonts.gstatic.com/s/lobster/v30/neILzCirqoswsqX9zoKmMw.ttf",
    ),
    (
        "SourceSans3-Regular.ttf",
        "https://fonts.gstatic.com/s/sourcesans3/v15/nwpBtKy2OAdR1K-IwhWudF-R9QMylBJAV3Bo8Ky461EN_io6npfB.ttf",
    ),
    (
        "JetBrainsMono-Regular.ttf",
        "https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjOVrMl0w.ttf",
    ),
]

_ICC_URL = (
    "https://download.adobe.com/pub/adobe/iccprofiles/win/AdobeICCProfilesCS4Win_end-user.zip"
)


def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  [skip] {dest.name} already present")
        return
    print(f"  [dl]   {dest.name} ...", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        size = dest.stat().st_size
        print(f" {size // 1024} KB")
    except Exception as exc:
        print(f" FAILED: {exc}")
        sys.exit(1)


def download_fonts() -> None:
    _FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading fonts to {_FONTS_DIR} ...")
    for filename, url in _FONT_URLS:
        _download(url, _FONTS_DIR / filename)
    print("Fonts OK.")


def create_stub_icc() -> None:
    """Create a minimal stub ICC profile for CI/test environments.

    The stub is not colorimetrically accurate but allows import without errors.
    For production, replace with the real USWebCoatedSWOP.icc from Adobe.
    """
    _ICC_DIR.mkdir(parents=True, exist_ok=True)
    icc_path = _ICC_DIR / "USWebCoatedSWOP.icc"
    if icc_path.exists():
        print(f"  [skip] {icc_path.name} already present")
        return
    # Minimal ICC v2 CMYK profile header (128-byte stub that Pillow can open)
    # This is a valid ICC profile structure for testing purposes only.
    import struct

    profile_size = 128
    header = bytearray(profile_size)
    # Profile size (bytes 0-3, big-endian)
    struct.pack_into(">I", header, 0, profile_size)
    # CMM type: b'lcms' (bytes 4-7)
    header[4:8] = b"lcms"
    # Profile version: 2.1.0 (bytes 8-11)
    header[8:12] = b"\x02\x10\x00\x00"
    # Device class: 'prtr' (output) (bytes 12-15)
    header[12:16] = b"prtr"
    # Color space: 'CMYK' (bytes 16-19)
    header[16:20] = b"CMYK"
    # PCS: 'Lab ' (bytes 20-23)
    header[20:24] = b"Lab "
    # Rendering intent: perceptual (bytes 64-67)
    header[64:68] = b"\x00\x00\x00\x00"
    # Profile creator: 'stub' (bytes 80-83)
    header[80:84] = b"stub"
    # Signature 'acsp' (bytes 36-39)
    header[36:40] = b"acsp"
    # Tag count: 0 (bytes 128 - just header, no tags for stub)
    icc_path.write_bytes(bytes(header))
    print(f"  [stub] Created {icc_path.name} (test stub — replace with real profile for prod)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ColorForge bundled assets")
    parser.add_argument("--fonts-only", action="store_true")
    parser.add_argument("--icc-only", action="store_true")
    parser.add_argument("--stub-icc", action="store_true", help="Create stub ICC for CI")
    args = parser.parse_args()

    if args.icc_only:
        create_stub_icc()
        return
    if args.fonts_only:
        download_fonts()
        return

    download_fonts()
    if args.stub_icc:
        create_stub_icc()
    else:
        print(
            "\nNote: ICC profile not downloaded. For production use, download"
            " USWebCoatedSWOP.icc from Adobe and place it in apps/agents/assets/icc/."
            "\nFor CI/testing, run with --stub-icc to create a test stub."
        )


if __name__ == "__main__":
    main()
