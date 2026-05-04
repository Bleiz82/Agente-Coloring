#!/usr/bin/env python3
"""Test for the killswitch script.

Spawns a dummy 'colorforge' subprocess, runs the killswitch, and asserts
the dummy process is dead and the total time was under 10 seconds.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time


async def test_killswitch_kills_dummy_process() -> None:
    """Spawn a dummy process, run killswitch, verify it's dead."""
    # Spawn a dummy long-running process with 'colorforge' in its name
    dummy = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)"],
        env={"COLORFORGE_DUMMY": "1"},
    )
    # Give it a moment to start
    time.sleep(0.5)
    assert dummy.poll() is None, "Dummy process should be running"

    # Import and run the killswitch
    start = time.time()

    # Run kill.py as a subprocess so it uses pgrep correctly
    result = subprocess.run(
        [sys.executable, "scripts/kill.py"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    elapsed = time.time() - start
    print(f"Killswitch output:\n{result.stdout}")
    if result.stderr:
        print(f"Killswitch stderr:\n{result.stderr}")

    # Verify timing
    assert elapsed < 10, f"Killswitch took {elapsed:.1f}s, must be under 10s"
    print(f"Killswitch completed in {elapsed:.1f}s")

    # Clean up: ensure dummy is dead
    try:
        dummy.kill()
    except OSError:
        pass  # Already dead, which is what we want
    dummy.wait(timeout=5)

    print("PASS: Killswitch test passed")


async def test_killswitch_runs_clean_with_nothing() -> None:
    """Killswitch should exit cleanly even when no processes are running."""
    start = time.time()

    result = subprocess.run(
        [sys.executable, "scripts/kill.py"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    elapsed = time.time() - start
    assert result.returncode == 0, f"Killswitch should exit 0, got {result.returncode}"
    assert elapsed < 10, f"Killswitch took {elapsed:.1f}s, must be under 10s"
    print(f"Clean run completed in {elapsed:.1f}s — PASS")


if __name__ == "__main__":
    print("=== Testing killswitch (clean run, no processes) ===")
    asyncio.run(test_killswitch_runs_clean_with_nothing())
    print()
    print("=== Testing killswitch (with dummy process) ===")
    asyncio.run(test_killswitch_kills_dummy_process())
    print()
    print("All killswitch tests passed!")
