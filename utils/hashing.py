"""Hashing utilities for FaceProof."""

import hashlib
from pathlib import Path
from typing import Union


def hash_bytes(data: bytes) -> str:
    """Computes lowercase hex SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_string(text: str) -> str:
    """Computes lowercase hex SHA-256 hash of a UTF-8 string."""
    return hash_bytes(text.encode("utf-8"))


def hash_file(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Computes lowercase hex SHA-256 hash of a file on disk."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def hex_to_bytes32(hex_hash: str) -> bytes:
    """Converts a 64-char hex string to 32 bytes (bytes32 format for Solidity)."""
    clean_hex = hex_hash.strip()
    if clean_hex.startswith("0x"):
        clean_hex = clean_hex[2:]
    if len(clean_hex) != 64:
        raise ValueError(f"Expected 64 hex characters for SHA-256 / bytes32, got {len(clean_hex)}")
    return bytes.fromhex(clean_hex)
