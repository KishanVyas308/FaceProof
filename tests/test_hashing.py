"""Tests for hashing utilities and bytes32 conversion."""

import pytest
from utils.hashing import hash_bytes, hash_string, hash_file, hex_to_bytes32


def test_hash_string():
    # Known SHA-256 for empty string: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert hash_string("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert hash_string("hello world") == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_hash_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    assert hash_file(test_file) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_hex_to_bytes32():
    hash_hex = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    b32 = hex_to_bytes32(hash_hex)
    assert len(b32) == 32
    assert b32.hex() == hash_hex

    # Test with 0x prefix
    b32_prefixed = hex_to_bytes32("0x" + hash_hex)
    assert b32_prefixed == b32

    # Test invalid length
    with pytest.raises(ValueError):
        hex_to_bytes32("1234abcd")
