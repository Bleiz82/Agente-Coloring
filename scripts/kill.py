#!/usr/bin/env python3
"""ColorForge emergency killswitch.

Halts every running agent, browser context, and queued job within 10 seconds.
Tested in CI: scripts/test_kill.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time


KILL_TIMEOUT_SECONDS = 10


async def flush_redis_queues() -> None:
    """Drain all Redis queues so no new job picks up."""
    try:
        import redis.asyncio as redis
    except ImportError:
        print("[killswitch] redis package not installed, skipping queue flush")
        return

    password = os.environ.get("REDIS_PASSWORD", "colorforge_dev")
    r = redis.Redis(host="localhost", port=6379, password=password)
    try:
        keys = await r.keys("queue:*")
        if keys:
            await r.delete(*keys)
            print(f"[killswitch] Flushed {len(keys)} queues")
        await r.set("colorforge:killswitch", "1", ex=300)  # 5 min lockout
        print("[killswitch] Killswitch flag set in Redis (5 min lockout)")
    except Exception as e:
        print(f"[killswitch] Redis flush warning: {e}")
    finally:
        await r.aclose()


def kill_processes() -> int:
    """SIGTERM then SIGKILL all colorforge processes (excluding ourselves)."""
    killed = 0
    my_pid = str(os.getpid())

    try:
        ps = subprocess.run(
            ["pgrep", "-f", "colorforge"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [p for p in ps.stdout.strip().split("\n") if p and p != my_pid]

        for pid in pids:
            try:
                subprocess.run(["kill", "-TERM", pid], check=False)
                killed += 1
            except Exception as e:
                print(f"[killswitch] SIGTERM failed for {pid}: {e}")

        if pids:
            time.sleep(2)

        ps = subprocess.run(
            ["pgrep", "-f", "colorforge"],
            capture_output=True,
            text=True,
            check=False,
        )
        remaining = [p for p in ps.stdout.strip().split("\n") if p and p != my_pid]
        for pid in remaining:
            subprocess.run(["kill", "-KILL", pid], check=False)

    except Exception as e:
        print(f"[killswitch] Process kill error: {e}")
    return killed


def kill_browsers() -> int:
    """Close all Chromium/Chrome instances spawned by Playwright."""
    killed = 0
    try:
        ps = subprocess.run(
            ["pgrep", "-f", "playwright"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [p for p in ps.stdout.strip().split("\n") if p]
        for pid in pids:
            subprocess.run(["kill", "-KILL", pid], check=False)
            killed += 1
    except Exception as e:
        print(f"[killswitch] Browser kill error: {e}")
    return killed


async def main() -> int:
    start = time.time()
    print("[killswitch] KILLSWITCH ACTIVATED")

    await flush_redis_queues()
    n_proc = kill_processes()
    n_browsers = kill_browsers()

    elapsed = time.time() - start
    print(
        f"[killswitch] Complete in {elapsed:.1f}s. "
        f"Processes killed: {n_proc}, browsers killed: {n_browsers}"
    )

    if elapsed > KILL_TIMEOUT_SECONDS:
        print(f"[killswitch] WARNING: Exceeded {KILL_TIMEOUT_SECONDS}s timeout!")
        return 2
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    sys.exit(asyncio.run(main()))
