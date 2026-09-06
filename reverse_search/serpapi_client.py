"""Layer 3: Reverse Image Search using SerpApi Google Lens."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import requests

from config.settings import ALLOWED_DOMAINS, SERPAPI_KEY


class SerpApiError(Exception):
    """Base exception for SerpApi issues."""
    pass


class SerpApiAuthError(SerpApiError):
    """Raised on invalid API key or authentication failure."""
    pass


class SerpApiQuotaExceededError(SerpApiError):
    """Raised when monthly search quota or rate limit is reached."""
    pass


@dataclass
class SearchCandidate:
    """Represents a discovered reverse image search match."""
    title: str
    source_url: str
    domain: str
    thumbnail_url: Optional[str] = None
    direct_image_url: Optional[str] = None
    rank: int = 0


def extract_domain(url: str) -> str:
    """Extracts base domain from a URL, lowercased without www."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def is_allowed_social_domain(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """Checks if a URL belongs to one of the configured social media platforms."""
    domains = allowed_domains or ALLOWED_DOMAINS
    actual_domain = extract_domain(url)
    return any(actual_domain == d or actual_domain.endswith("." + d) for d in domains)


import io
from PIL import Image

def upload_image_to_serpapi(image_path: Path, api_key: str) -> str:
    """
    Uploads a local image to SerpApi's dedicated /image endpoint.
    Automatically compresses/resizes to satisfy the < 500 KB limit.
    Returns the SerpApi image_id.
    """
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            # Resize if large to ensure fast upload and under 500 KB
            rgb_img.thumbnail((1200, 1200))
            buf = io.BytesIO()
            quality = 85
            rgb_img.save(buf, format="JPEG", quality=quality)
            while len(buf.getvalue()) > 490000 and quality > 30:
                buf = io.BytesIO()
                quality -= 15
                rgb_img.save(buf, format="JPEG", quality=quality)
            image_bytes = buf.getvalue()
    except Exception as e:
        raise SerpApiError(f"Failed to process image for SerpApi upload: {e}")

    try:
        resp = requests.post(
            "https://serpapi.com/image",
            files={"image": ("image.jpg", image_bytes, "image/jpeg")},
            data={"api_key": api_key},
            timeout=25
        )
    except requests.exceptions.RequestException as e:
        raise SerpApiError(f"Failed to connect to SerpApi image upload endpoint: {e}")

    if resp.status_code in (401, 403):
        raise SerpApiAuthError("SerpApi authentication failed during image upload. Check your SERPAPI_KEY.")
    elif resp.status_code != 200:
        raise SerpApiError(f"SerpApi image upload failed with status {resp.status_code}: {resp.text[:200]}")

    try:
        upload_data = resp.json()
    except Exception:
        raise SerpApiError("SerpApi image upload returned invalid response.")

    image_id = upload_data.get("image_id")
    if not image_id:
        raise SerpApiError(f"SerpApi did not return an image_id: {upload_data}")

    return image_id


def search_google_lens(
    image_path: Path,
    api_key: Optional[str] = None,
    custom_image_url: Optional[str] = None,
    allow_demo_fallback: bool = False
) -> List[SearchCandidate]:
    """
    Performs a genuine reverse image search using SerpApi Google Lens engine.

    Returns a list of SearchCandidate objects filtered to social media domains.
    """
    key = api_key or SERPAPI_KEY
    if not key or key == "your_serpapi_key_here":
        if allow_demo_fallback:
            # Demo mode fallback for offline evaluation / automated tests
            return [
                SearchCandidate(
                    title="Sample Public Post on Instagram",
                    source_url="https://www.instagram.com/p/sample_demo_post_2026/",
                    domain="instagram.com",
                    thumbnail_url=None,
                    direct_image_url=None,
                    rank=1
                )
            ]
        raise SerpApiAuthError(
            "SerpApi key is not configured. Please set SERPAPI_KEY in your .env file."
        )

    params = {
        "engine": "google_lens",
        "api_key": key
    }

    if custom_image_url:
        params["url"] = custom_image_url
    else:
        # Use SerpApi official /image upload endpoint
        image_id = upload_image_to_serpapi(image_path, key)
        params["image_id"] = image_id

    serpapi_endpoint = "https://serpapi.com/search.json"

    try:
        response = requests.get(serpapi_endpoint, params=params, timeout=35)
    except requests.exceptions.RequestException as e:
        raise SerpApiError(f"Network error connecting to SerpApi: {e}")

    # Handle HTTP error statuses
    if response.status_code in (401, 403):
        raise SerpApiAuthError("SerpApi authentication failed. Invalid API key.")
    elif response.status_code == 429:
        raise SerpApiQuotaExceededError("SerpApi rate limit or monthly search quota exceeded.")
    elif response.status_code != 200:
        raise SerpApiError(f"SerpApi returned HTTP status {response.status_code}: {response.text[:200]}")

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise SerpApiError("SerpApi returned invalid non-JSON response.")

    # Check for SerpApi error in JSON
    if "error" in data:
        err_msg = str(data["error"])
        if "quota" in err_msg.lower() or "limit" in err_msg.lower():
            raise SerpApiQuotaExceededError(f"SerpApi quota limit: {err_msg}")
        raise SerpApiError(f"SerpApi error: {err_msg}")

    # Extract matches from visual_matches
    visual_matches = data.get("visual_matches", [])
    candidates: List[SearchCandidate] = []

    for rank, match in enumerate(visual_matches, 1):
        link = match.get("link", "")
        if not link:
            continue

        domain = extract_domain(link)
        title = match.get("title", "")
        thumbnail = match.get("thumbnail")
        original_img = match.get("original") or match.get("image")

        candidate = SearchCandidate(
            title=title,
            source_url=link,
            domain=domain,
            thumbnail_url=thumbnail,
            direct_image_url=original_img,
            rank=rank
        )
        candidates.append(candidate)

    # Filter to social media allowlist
    social_candidates = [c for c in candidates if is_allowed_social_domain(c.source_url)]
    return social_candidates
