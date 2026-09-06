"""Tests for Layer 2: Face detection and encoding."""

from PIL import Image
import numpy as np
import pytest
from face.encoder import encode_face, NoFaceDetectedError, normalize_l2


def test_normalize_l2():
    vec = np.array([3.0, 4.0], dtype=np.float32)
    normed = normalize_l2(vec)
    assert np.linalg.norm(normed) == pytest.approx(1.0, abs=1e-5)
    assert normed[0] == pytest.approx(0.6, abs=1e-5)
    assert normed[1] == pytest.approx(0.8, abs=1e-5)


def test_zero_vector_normalize():
    vec = np.zeros(512, dtype=np.float32)
    normed = normalize_l2(vec)
    assert np.all(normed == 0)


def test_blank_image_raises_no_face(tmp_path):
    blank_img = tmp_path / "landscape.jpg"
    # Create simple landscape image without face
    Image.new("RGB", (300, 300), color=(100, 150, 200)).save(blank_img)

    with pytest.raises(NoFaceDetectedError):
        encode_face(blank_img, require_face=True)

    # When require_face=False, returns structured zero result
    res = encode_face(blank_img, require_face=False)
    assert res.face_count == 0
    assert res.det_score == 0.0
    assert len(res.embedding) == 512
