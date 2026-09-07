"""Tests for Layer 1 and 8: Input validation and pipeline orchestration."""

from pathlib import Path
from PIL import Image
import pytest

from face.input_handler import (
    validate_and_stage_image,
    setup_run_directory,
    ImageValidationError
)
from reverse_search.serpapi_client import (
    is_allowed_social_domain,
    extract_domain
)


def test_domain_filtering():
    assert is_allowed_social_domain("https://www.instagram.com/p/C_12345/")
    assert is_allowed_social_domain("https://instagram.com/reel/xyz")
    assert is_allowed_social_domain("https://x.com/user/status/12345")
    assert is_allowed_social_domain("https://twitter.com/user/status/12345")
    assert is_allowed_social_domain("https://www.facebook.com/photo.php?fbid=1")
    assert not is_allowed_social_domain("https://random-unrelated-blog.net/image.png")
    assert not is_allowed_social_domain("https://wikipedia.org/wiki/Face")


def test_extract_domain():
    assert extract_domain("https://www.instagram.com/explore/") == "instagram.com"
    assert extract_domain("https://sub.domain.co.uk/page") == "sub.domain.co.uk"


def test_input_validation_success(tmp_path):
    run_dir = setup_run_directory()
    valid_img = tmp_path / "valid.png"
    Image.new("RGB", (120, 120), color=(255, 0, 0)).save(valid_img)

    staged_path, sha256 = validate_and_stage_image(str(valid_img), run_dir)
    assert staged_path.exists()
    assert staged_path.name == "input.jpg"
    assert len(sha256) == 64


def test_input_validation_missing_file(tmp_path):
    run_dir = setup_run_directory()
    missing_path = tmp_path / "nonexistent.jpg"

    with pytest.raises(ImageValidationError) as exc:
        validate_and_stage_image(str(missing_path), run_dir)
    assert "does not exist" in str(exc.value)


def test_input_validation_corrupted_file(tmp_path):
    run_dir = setup_run_directory()
    corrupt_file = tmp_path / "corrupt.jpg"
    # Write garbage bytes
    corrupt_file.write_bytes(b"not an image at all just binary garbage\x00\x01\x02")

    with pytest.raises(ImageValidationError) as exc:
        validate_and_stage_image(str(corrupt_file), run_dir)
    assert "corrupted" in str(exc.value).lower() or "not a valid image" in str(exc.value).lower()


def test_retrieve_candidate_images_max_limit(monkeypatch, tmp_path):
    from matching.retrieval import retrieve_candidate_images, retrieve_best_candidate_image
    from reverse_search.serpapi_client import SearchCandidate

    candidates = [
        SearchCandidate(title="Post 1", source_url="https://instagram.com/p/1", domain="instagram.com", thumbnail_url="http://example.com/1.jpg", direct_image_url=None, rank=1),
        SearchCandidate(title="Post 2", source_url="https://instagram.com/p/2", domain="instagram.com", thumbnail_url="http://example.com/2.jpg", direct_image_url=None, rank=2),
        SearchCandidate(title="Post 3", source_url="https://instagram.com/p/3", domain="instagram.com", thumbnail_url="http://example.com/3.jpg", direct_image_url=None, rank=3),
        SearchCandidate(title="Post 4", source_url="https://instagram.com/p/4", domain="instagram.com", thumbnail_url="http://example.com/4.jpg", direct_image_url=None, rank=4),
    ]

    # Mock download_and_verify_image to create a dummy image file and return True
    def mock_download(url, target_path, timeout=15):
        Image.new("RGB", (50, 50), color="blue").save(target_path)
        return True

    monkeypatch.setattr("matching.retrieval.download_and_verify_image", mock_download)

    # Test top-2 max_candidates
    retrieved = retrieve_candidate_images(candidates, tmp_path, max_candidates=2)
    assert len(retrieved) == 2
    assert retrieved[0].candidate.rank == 1
    assert retrieved[1].candidate.rank == 2

    # Test retrieve_best_candidate_image returns first
    best = retrieve_best_candidate_image(candidates, tmp_path)
    assert best is not None
    assert best.candidate.rank == 1


def test_defensive_raw_transaction_attribute():
    # Test compatibility when object has raw_transaction vs rawTransaction
    class SignedTxNew:
        raw_transaction = b"\x01\x02\x03"

    class SignedTxOld:
        rawTransaction = b"\x04\x05\x06"

    new_tx = SignedTxNew()
    old_tx = SignedTxOld()

    raw_new = getattr(new_tx, "raw_transaction", None) or getattr(new_tx, "rawTransaction", None)
    raw_old = getattr(old_tx, "raw_transaction", None) or getattr(old_tx, "rawTransaction", None)

    assert raw_new == b"\x01\x02\x03"
    assert raw_old == b"\x04\x05\x06"

