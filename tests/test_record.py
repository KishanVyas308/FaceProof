"""Tests for Layer 6: Verification record deterministic serialization and hashing."""

import json
from verification.record import (
    build_verification_record,
    serialize_record_deterministically,
    compute_record_hash
)


def test_build_record_fields():
    record = build_verification_record(
        input_image_sha256="abc123sha",
        match_status="match",
        candidate_image_sha256="def456sha",
        candidate_source_url="https://instagram.com/p/123",
        similarity_score=0.72,
        timestamp_iso="2026-09-07T00:00:00Z",
        pipeline_version="0.1.0"
    )

    assert record["input_image_sha256"] == "abc123sha"
    assert record["match_status"] == "match"
    assert record["similarity_score"] == 0.72
    assert record["timestamp"] == "2026-09-07T00:00:00Z"


def test_deterministic_serialization():
    # Regardless of key order passed, serialized output must match exactly
    dict1 = {
        "timestamp": "2026-09-07T00:00:00Z",
        "similarity_score": 0.75,
        "input_image_sha256": "1111",
        "candidate_image_sha256": "2222",
        "match_status": "match",
        "pipeline_version": "0.1.0",
        "candidate_source_url": "https://instagram.com/p/xyz"
    }

    dict2 = {
        "candidate_source_url": "https://instagram.com/p/xyz",
        "pipeline_version": "0.1.0",
        "match_status": "match",
        "candidate_image_sha256": "2222",
        "input_image_sha256": "1111",
        "similarity_score": 0.75,
        "timestamp": "2026-09-07T00:00:00Z"
    }

    json1 = serialize_record_deterministically(dict1)
    json2 = serialize_record_deterministically(dict2)

    assert json1 == json2

    _, hash1 = compute_record_hash(dict1)
    _, hash2 = compute_record_hash(dict2)

    assert hash1 == hash2
    assert len(hash1) == 64
