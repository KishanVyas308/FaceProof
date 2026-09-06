"""Layer 1: Input / Camera validation and staging."""

import os
import shutil
import time
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

from config.settings import TMP_DIR
from utils.hashing import hash_file

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class ImageValidationError(Exception):
    """Raised when an input image is missing, unreadable, or invalid."""
    pass


def setup_run_directory() -> Path:
    """Creates a timestamped temporary directory for the pipeline run."""
    timestamp = int(time.time() * 1000)
    run_dir = TMP_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def validate_and_stage_image(image_path_str: str, run_dir: Path) -> Tuple[Path, str]:
    """
    Validates that the given path points to a readable, valid image file
    using both extension and PIL header verification.
    Copies it to the run directory as `input.jpg` and computes its SHA-256 hash.

    Returns:
        (staged_path, sha256_hash)
    """
    if not image_path_str:
        raise ImageValidationError("No image path provided.")

    source_path = Path(image_path_str).resolve()

    if not source_path.exists():
        raise ImageValidationError(f"Input file does not exist: {source_path}")

    if not source_path.is_file():
        raise ImageValidationError(f"Input path is not a file: {source_path}")

    # Check extension
    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(SUPPORTED_EXTENSIONS)
        raise ImageValidationError(
            f"Unsupported file format '{source_path.suffix}'. Supported formats: {allowed}"
        )

    # Deep header verification with PIL
    try:
        with Image.open(source_path) as img:
            img.verify()
    except Exception as e:
        raise ImageValidationError(f"File is corrupted or not a valid image: {e}")

    # Re-open and convert to RGB/JPEG format in staging dir to ensure standard orientation/channels
    target_path = run_dir / "input.jpg"
    try:
        with Image.open(source_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(target_path, "JPEG", quality=95)
    except Exception as e:
        raise ImageValidationError(f"Failed to process and stage input image: {e}")

    # Compute SHA-256 hash of staged image
    sha256 = hash_file(target_path)
    return target_path, sha256


def capture_webcam_frame(run_dir: Path, camera_index: int = 0) -> Tuple[Path, str]:
    """
    Captures a single frame from the system webcam using OpenCV,
    saves it to the run directory as `input.jpg`, and computes its SHA-256 hash.
    """
    try:
        import cv2
    except ImportError:
        raise ImageValidationError("OpenCV is required for webcam capture.")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise ImageValidationError(f"Could not open webcam at index {camera_index}.")

    try:
        # Allow camera warmup
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        if not ret or frame is None:
            raise ImageValidationError("Failed to capture a valid frame from webcam.")

        target_path = run_dir / "input.jpg"
        cv2.imwrite(str(target_path), frame)
    finally:
        cap.release()

    sha256 = hash_file(target_path)
    return target_path, sha256
