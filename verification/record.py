"""Layer 6: Verification Record building and deterministic SHA-256 hashing."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config.settings import PIPELINE_VERSION
from utils.hashing import hash_string


def build_verification_record(
    input_image_sha256: str,
    match_status: str,
    candidate_image_sha256: Optional[str] = None,
    candidate_source_url: Optional[str] = None,
    similarity_score: Optional[float] = None,
    timestamp_iso: Optional[str] = None,
    pipeline_version: str = PIPELINE_VERSION
) -> Dict[str, Any]:
    """
    Constructs a structured verification record.
    Matches must strictly exclude biometric arrays, raw images, or KYC assertions.
    """
    valid_statuses = {"match", "no_match", "no_candidate_found", "candidate_unavailable"}
    if match_status not in valid_statuses:
        raise ValueError(f"Invalid match_status '{match_status}'. Expected one of {valid_statuses}")

    if timestamp_iso is None:
        timestamp_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "candidate_image_sha256": candidate_image_sha256,
        "candidate_source_url": candidate_source_url,
        "input_image_sha256": input_image_sha256,
        "match_status": match_status,
        "pipeline_version": pipeline_version,
        "similarity_score": similarity_score,
        "timestamp": timestamp_iso
    }


def serialize_record_deterministically(record: Dict[str, Any]) -> str:
    """
    Serializes a dictionary deterministically:
    - Alphabetically sorted keys
    - Compact separators (no extra spaces)
    - Unicode handled consistently
    """
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_record_hash(record: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (canonical_json_string, sha256_hash).
    """
    canonical_json = serialize_record_deterministically(record)
    record_hash = hash_string(canonical_json)
    return canonical_json, record_hash


def save_verification_record(
    record: Dict[str, Any],
    run_dir: Path
) -> Tuple[Path, str, str]:
    """
    Saves verification_record.json to run_dir deterministically.
    Returns (saved_path, canonical_json, record_hash).
    """
    canonical_json, record_hash = compute_record_hash(record)
    out_file = run_dir / "verification_record.json"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(canonical_json)

    return out_file, canonical_json, record_hash
