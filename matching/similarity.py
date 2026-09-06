"""Layer 5: Face Matching / Similarity Layer.

NOTE: A similarity score above threshold indicates the two face images are
visually similar according to the model's embedding space. It does NOT prove
the two images are the same real-world person, and is not a substitute for
KYC or forensic identity verification. MATCH_THRESHOLD is an experimentally
chosen prototype parameter.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import numpy as np

from config.settings import MATCH_THRESHOLD
from face.encoder import encode_face, FaceEncodingResult, NoFaceDetectedError


@dataclass
class SimilarityResult:
    """Represents the outcome of face similarity comparison."""
    similarity_score: Optional[float]
    is_match: bool
    candidate_face_count: int
    decision_reason: str


def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Computes cosine similarity between two 1-D vectors:
    sim = dot(a, b) / (||a|| * ||b||)
    """
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    sim = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    return float(np.clip(sim, -1.0, 1.0))


def compare_faces(
    input_result: FaceEncodingResult,
    candidate_image_path: Union[str, Path],
    threshold: float = MATCH_THRESHOLD,
    warn_callback: Optional[callable] = None
) -> SimilarityResult:
    """
    Detects faces in candidate image and computes cosine similarity against input face embedding.
    If candidate has multiple faces, compares against all and keeps highest similarity score.
    """
    try:
        cand_result = encode_face(
            candidate_image_path,
            require_face=False,
            warn_callback=warn_callback
        )
    except Exception as e:
        return SimilarityResult(
            similarity_score=None,
            is_match=False,
            candidate_face_count=0,
            decision_reason=f"Candidate face detection error: {e}"
        )

    if cand_result.face_count == 0:
        return SimilarityResult(
            similarity_score=None,
            is_match=False,
            candidate_face_count=0,
            decision_reason="No face detected in candidate image"
        )

    # Candidate has at least one face: compare input embedding against all candidate face embeddings
    candidate_embeddings = cand_result.all_embeddings or [cand_result.embedding]
    scores = [
        compute_cosine_similarity(input_result.embedding, c_emb)
        for c_emb in candidate_embeddings
    ]

    max_score = float(max(scores))
    max_score = round(max_score, 4)
    is_match = max_score >= threshold

    reason = (
        f"Similarity {max_score:.2f} >= threshold {threshold:.2f} (faces compared: {len(scores)})"
        if is_match
        else f"Similarity {max_score:.2f} < threshold {threshold:.2f} (faces compared: {len(scores)})"
    )

    return SimilarityResult(
        similarity_score=max_score,
        is_match=is_match,
        candidate_face_count=cand_result.face_count,
        decision_reason=reason
    )
