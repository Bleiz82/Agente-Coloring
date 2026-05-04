#!/usr/bin/env python3
"""Manual KDP login helper -- opens headed browser, saves and encrypts storageState.

Usage:
  python scripts/kdp_login.py \
      --account=stefano-main \
      --age-pubkey=age1... \
      --encrypted-output=secrets/stefano-main.age

The operator logs in manually. When the KDP bookshelf URL is detected,
the script saves storageState and encrypts it with the provided age public key.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Adjust sys.path so colorforge_kdp is importable when run from repo root
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "packages" / "kdp-client"))

from colorforge_kdp.storage import encrypt_storage_state  # noqa: E402

_KDP_HOME = "https://kdp.amazon.com"
_BOOKSHELF_FRAGMENT = "/bookshelf"


async def main(
    account_label: str,
    age_pubkey: str,
    encrypted_output: Path,
) -> None:
    """Run the login flow: open browser, wait for bookshelf, save and encrypt state."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "ERROR: playwright not installed. "
            "Run: pip install playwright && playwright install chromium"
        )
        sys.exit(1)

    print(f"Opening headed browser for account '{account_label}'...")
    print("Please complete the login manually in the browser window.")
    print(f"Script will auto-save when URL contains '{_BOOKSHELF_FRAGMENT}'")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(_KDP_HOME)

        detected = asyncio.Event()

        async def on_frame_nav(frame: object) -> None:
            if hasattr(frame, "url") and _BOOKSHELF_FRAGMENT in str(frame.url):
                detected.set()

        page.on("framenavigated", on_frame_nav)

        print("Waiting for login... (close the browser window to abort)")
        try:
            await asyncio.wait_for(detected.wait(), timeout=300)
        except TimeoutError:
            print("Timed out waiting for login. Aborting.")
            await browser.close()
            sys.exit(1)

        print("Bookshelf detected -- saving storageState...")

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            state = await context.storage_state()
            json.dump(state, tmp)
            tmp_path = Path(tmp.name)

        await browser.close()

    encrypted_output.parent.mkdir(parents=True, exist_ok=True)
    await encrypt_storage_state(
        state_path=tmp_path,
        age_pubkey=age_pubkey,
        dest=encrypted_output,
    )
    tmp_path.unlink(missing_ok=True)  # noqa: ASYNC240

    print(f"storageState saved and encrypted to: {encrypted_output}")
    print("Transfer this file to your VPS and set STORAGE_STATE_PATH in your account config.")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True, help="Account label (for display only)")
    parser.add_argument("--age-pubkey", required=True, help="age public key (age1...)")
    parser.add_argument(
        "--encrypted-output",
        required=True,
        type=Path,
        help="Destination for encrypted .age file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.account, args.age_pubkey, args.encrypted_output))
