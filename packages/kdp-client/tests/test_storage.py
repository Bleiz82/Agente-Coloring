"""Tests for storage.py -- encrypt/decrypt roundtrip."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from colorforge_kdp.exceptions import StorageStateError
from colorforge_kdp.storage import (
    decrypt_storage_state,
    encrypt_storage_state,
    is_storage_valid,
)

VALID_STATE = {"cookies": [{"name": "session", "value": "abc"}], "origins": []}


@pytest.fixture()
def tmp_state(tmp_path: Path) -> Path:
    p = tmp_path / "state.json"
    p.write_text(json.dumps(VALID_STATE))
    return p


@pytest.fixture()
def tmp_encrypted(tmp_path: Path) -> Path:
    return tmp_path / "state.age"


async def test_encrypt_calls_age_binary(tmp_state: Path, tmp_encrypted: Path) -> None:
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await encrypt_storage_state(tmp_state, "age1testpubkey", tmp_encrypted)
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert "age" in args[0]
    assert "--recipient" in args
    assert "age1testpubkey" in args


async def test_encrypt_raises_on_nonzero_returncode(
    tmp_state: Path, tmp_encrypted: Path
) -> None:
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error msg"))
    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        pytest.raises(StorageStateError, match="age encrypt failed"),
    ):
        await encrypt_storage_state(tmp_state, "age1testpubkey", tmp_encrypted)


async def test_encrypt_raises_if_source_missing(tmp_path: Path) -> None:
    with pytest.raises(StorageStateError, match="does not exist"):
        await encrypt_storage_state(
            tmp_path / "missing.json", "age1x", tmp_path / "out.age"
        )


async def test_decrypt_calls_age_binary(tmp_path: Path) -> None:
    encrypted = tmp_path / "state.age"
    encrypted.write_bytes(b"encrypted")
    key = tmp_path / "key.txt"
    key.write_text("AGE-SECRET-KEY-1...")
    out = tmp_path / "state.json"

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    # Simulate age creating the output file
    out.write_text(json.dumps(VALID_STATE))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await decrypt_storage_state(encrypted, key, tmp_path)

    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert "--decrypt" in args
    assert result == out


async def test_decrypt_raises_on_nonzero_returncode(tmp_path: Path) -> None:
    encrypted = tmp_path / "state.age"
    encrypted.write_bytes(b"bad")
    key = tmp_path / "key.txt"
    key.write_text("AGE-SECRET-KEY-1...")
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"decryption failed"))
    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        pytest.raises(StorageStateError, match="age decrypt failed"),
    ):
        await decrypt_storage_state(encrypted, key, tmp_path)


async def test_decrypt_raises_if_encrypted_missing(tmp_path: Path) -> None:
    key = tmp_path / "key.txt"
    key.write_text("AGE-SECRET-KEY-1...")
    with pytest.raises(StorageStateError, match="does not exist"):
        await decrypt_storage_state(tmp_path / "nope.age", key, tmp_path)


async def test_decrypt_raises_if_key_missing(tmp_path: Path) -> None:
    encrypted = tmp_path / "state.age"
    encrypted.write_bytes(b"encrypted")
    with pytest.raises(StorageStateError, match="does not exist"):
        await decrypt_storage_state(encrypted, tmp_path / "nope.txt", tmp_path)


def test_is_storage_valid_true(tmp_state: Path) -> None:
    assert is_storage_valid(tmp_state) is True


def test_is_storage_valid_false_missing(tmp_path: Path) -> None:
    assert is_storage_valid(tmp_path / "nope.json") is False


def test_is_storage_valid_false_no_cookies(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text('{"origins": []}')
    assert is_storage_valid(p) is False


def test_is_storage_valid_false_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not-json")
    assert is_storage_valid(p) is False
