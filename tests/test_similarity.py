"""Tests for Layer 5: Cosine similarity and threshold matching."""

import numpy as np
import pytest
from matching.similarity import compute_cosine_similarity, compare_faces
from face.encoder import FaceEncodingResult


def test_cosine_similarity_identical():
    v1 = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    assert compute_cosine_similarity(v1, v1) == pytest.approx(1.0, abs=1e-4)


def test_cosine_similarity_orthogonal():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert compute_cosine_similarity(v1, v2) == pytest.approx(0.0, abs=1e-4)


def test_cosine_similarity_opposite():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    assert compute_cosine_similarity(v1, v2) == pytest.approx(-1.0, abs=1e-4)


def test_compare_faces_no_face_in_candidate(tmp_path):
    blank_image = tmp_path / "blank.jpg"
    # Create a 100x100 white image
    from PIL import Image
    Image.new("RGB", (100, 100), color="white").save(blank_image)

    fake_input = FaceEncodingResult(
        embedding=np.ones(512, dtype=np.float32) / np.sqrt(512),
        bbox=(10, 10, 50, 50),
        det_score=0.99,
        face_count=1
    )

    result = compare_faces(fake_input, blank_image)
    assert not result.is_match
    assert result.similarity_score is None
    assert result.candidate_face_count == 0
    assert "No face detected" in result.decision_reason
