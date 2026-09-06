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


def upload_temp_image_for_lens(image_path: Path) -> Optional[str]:
    """
    If a local image needs a public temporary URL for Google Lens search,
    uploads anonymously to tmpfiles.org or catbox.
    Returns public URL or None if upload fails.
    """
    try:
        with open(image_path, "rb") as f:
            resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and "url" in data["data"]:
                    url = data["data"]["url"]
                    # tmpfiles.org URLs format: https://tmpfiles.org/12345/img.jpg -> https://tmpfiles.org/dl/12345/img.jpg
                    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass
    return None


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

    # Determine URL or file parameter
    lens_url = custom_image_url
    if not lens_url:
        lens_url = upload_temp_image_for_lens(image_path)

    params = {
        "engine": "google_lens",
        "api_key": key
    }

    if lens_url:
        params["url"] = lens_url

    serpapi_endpoint = "https://serpapi.com/search.json"

    try:
        # If no public URL was acquired, attempt multipart direct upload if supported or send file
        if not lens_url:
            with open(image_path, "rb") as f:
                response = requests.post(serpapi_endpoint, params=params, files={"file": f}, timeout=30)
        else:
            response = requests.get(serpapi_endpoint, params=params, timeout=30)
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
