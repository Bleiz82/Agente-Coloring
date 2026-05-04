"""StorageState encryption and decryption via age."""
from __future__ import annotations

from pathlib import Path

from colorforge_kdp.exceptions import StorageStateError


async def encrypt_storage_state(
    state_path: Path, age_pubkey: str, dest: Path
) -> None:
    """Encrypt a storageState JSON file using the age binary. Implemented in T2.4."""
    raise NotImplementedError


async def decrypt_storage_state(
    encrypted: Path, age_key: Path, tmpfs_dir: Path
) -> Path:
    """Decrypt an age-encrypted storageState to tmpfs_dir. Implemented in T2.4."""
    raise NotImplementedError


def is_storage_valid(state_path: Path) -> bool:
    """Return True if state_path is a valid JSON storageState. Implemented in T2.4."""
    raise NotImplementedError


__all__ = [
    "encrypt_storage_state",
    "decrypt_storage_state",
    "is_storage_valid",
    "StorageStateError",
]
