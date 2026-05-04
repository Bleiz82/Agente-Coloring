"""StorageState encryption and decryption via the age CLI binary."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from colorforge_kdp.exceptions import StorageStateError

_AGE_BINARY = "age"  # must be on PATH on the VPS


async def encrypt_storage_state(
    state_path: Path,
    age_pubkey: str,
    dest: Path,
) -> None:
    """Encrypt state_path with age --recipient pubkey, writing to dest.

    Raises StorageStateError on subprocess failure.
    """
    if not state_path.exists():
        raise StorageStateError(state_path, "source file does not exist")

    dest.parent.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        _AGE_BINARY,
        "--recipient",
        age_pubkey,
        "--output",
        str(dest),
        str(state_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise StorageStateError(
            dest,
            f"age encrypt failed (rc={proc.returncode}): {stderr.decode().strip()}",
        )
    logger.debug("storageState encrypted to {}", dest)


async def decrypt_storage_state(
    encrypted: Path,
    age_key: Path,
    tmpfs_dir: Path,
) -> Path:
    """Decrypt age-encrypted storageState to tmpfs_dir/{stem}.json.

    Returns the path of the decrypted file.
    Raises StorageStateError on subprocess failure or if encrypted file missing.
    """
    if not encrypted.exists():
        raise StorageStateError(encrypted, "encrypted file does not exist")
    if not age_key.exists():
        raise StorageStateError(age_key, "age identity key file does not exist")

    tmpfs_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmpfs_dir / f"{encrypted.stem}.json"

    proc = await asyncio.create_subprocess_exec(
        _AGE_BINARY,
        "--decrypt",
        "--identity",
        str(age_key),
        "--output",
        str(out_path),
        str(encrypted),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise StorageStateError(
            encrypted,
            f"age decrypt failed (rc={proc.returncode}): {stderr.decode().strip()}",
        )
    logger.debug("storageState decrypted to {}", out_path)
    return out_path


def is_storage_valid(state_path: Path) -> bool:
    """Return True if state_path exists, parses as JSON, and contains a 'cookies' key."""
    if not state_path.exists():
        return False
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and "cookies" in data
    except (json.JSONDecodeError, OSError):
        return False


__all__ = [
    "encrypt_storage_state",
    "decrypt_storage_state",
    "is_storage_valid",
    "StorageStateError",
]
