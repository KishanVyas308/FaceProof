"""Layer 4: Candidate Image Retrieval with fallback handling."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import requests
from PIL import Image

from reverse_search.serpapi_client import SearchCandidate
from utils.hashing import hash_file


class CandidateRetrievalError(Exception):
    """Raised when candidate image cannot be retrieved."""
    pass


@dataclass
class RetrievedCandidate:
    """Represents a successfully downloaded and verified candidate image."""
    candidate: SearchCandidate
    local_image_path: Path
    image_sha256: str


def download_and_verify_image(
    url: str,
    target_path: Path,
    timeout: int = 15
) -> bool:
    """
    Attempts to download an image from a URL, validates that it is a valid image via PIL,
    and saves it to target_path. Returns True on success, False on any failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return False

        # Verify image using PIL
        img = Image.open(resp.raw)
        img.verify()

        # Re-fetch or re-open to save in standard format
        # Since .verify() invalidates file pointer on streams, re-request or fetch content
        resp2 = requests.get(url, headers=headers, timeout=timeout)
        if resp2.status_code != 200:
            return False

        with open(target_path, "wb") as f:
            f.write(resp2.content)

        # Confirm saved file is valid image
        with Image.open(target_path) as saved_img:
            saved_img.convert("RGB").save(target_path, "JPEG", quality=90)

        return True
    except Exception:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        return False


def retrieve_best_candidate_image(
    candidates: List[SearchCandidate],
    run_dir: Path,
    demo_image_fallback: Optional[Path] = None
) -> Optional[RetrievedCandidate]:
    """
    Iterates through candidate results in order of rank.
    Attempts to retrieve the candidate image (preferring direct image URL, then thumbnail).
    Falls back to next candidate if an image is blocked or inaccessible.

    Returns:
        RetrievedCandidate if successful, or None if all candidates were inaccessible.
    """
    if not candidates:
        return None

    for candidate in candidates:
        target_path = run_dir / f"candidate_{candidate.rank}.jpg"

        # Try direct image URL first if available
        urls_to_try = []
        if candidate.direct_image_url:
            urls_to_try.append(candidate.direct_image_url)
        if candidate.thumbnail_url and candidate.thumbnail_url not in urls_to_try:
            urls_to_try.append(candidate.thumbnail_url)

        for url in urls_to_try:
            if download_and_verify_image(url, target_path):
                sha256 = hash_file(target_path)
                return RetrievedCandidate(
                    candidate=candidate,
                    local_image_path=target_path,
                    image_sha256=sha256
                )

        # If demo fallback provided and candidate had no URLs
        if not urls_to_try and demo_image_fallback and demo_image_fallback.exists():
            import shutil
            shutil.copyfile(demo_image_fallback, target_path)
            sha256 = hash_file(target_path)
            return RetrievedCandidate(
                candidate=candidate,
                local_image_path=target_path,
                image_sha256=sha256
            )

    return None
