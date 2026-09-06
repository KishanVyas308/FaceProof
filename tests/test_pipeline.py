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
