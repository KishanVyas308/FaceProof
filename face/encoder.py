"""Layer 2: Face Detection & Encoding Layer using InsightFace."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union
import warnings
import cv2
import numpy as np

# Suppress internal library deprecation/future warnings from insightface/skimage
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


class FaceDetectionError(Exception):
    """Raised when face detection or encoding fails."""
    pass


class NoFaceDetectedError(FaceDetectionError):
    """Raised specifically when zero faces are detected in an image."""
    pass


@dataclass
class FaceEncodingResult:
    """Structured result containing face detection and normalized 512-d embedding."""
    embedding: np.ndarray          # Primary (or largest) normalized 512-d embedding
    bbox: Tuple[int, int, int, int] # (x1, y1, x2, y2)
    det_score: float               # Detection confidence score
    face_count: int                # Total faces detected in image
    all_embeddings: List[np.ndarray] = field(default_factory=list) # All detected face embeddings


import os
import sys
from contextlib import contextmanager

@contextmanager
def _suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull."""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


_FACE_APP = None


def get_face_analysis_app(model_pack: str = "buffalo_l"):
    """
    Singleton lazy initializer for insightface.app.FaceAnalysis.
    Configures CPU or CUDA execution providers.
    """
    global _FACE_APP
    if _FACE_APP is not None:
        return _FACE_APP

    import insightface
    from insightface.app import FaceAnalysis
    import onnxruntime as ort

    available_providers = ort.get_available_providers()
    providers = ["CUDAExecutionProvider"] if "CUDAExecutionProvider" in available_providers else ["CPUExecutionProvider"]

    with _suppress_stdout_stderr():
        try:
            app = FaceAnalysis(name=model_pack, providers=providers)
            app.prepare(ctx_id=0, det_size=(640, 640))
            _FACE_APP = app
        except Exception as e:
            # Fallback to buffalo_s if buffalo_l has issues
            if model_pack == "buffalo_l":
                try:
                    app = FaceAnalysis(name="buffalo_s", providers=providers)
                    app.prepare(ctx_id=0, det_size=(640, 640))
                    _FACE_APP = app
                except Exception as fallback_err:
                    raise FaceDetectionError(f"Failed to initialize FaceAnalysis app: {fallback_err}")
            else:
                raise FaceDetectionError(f"Failed to initialize FaceAnalysis app: {e}")

    return _FACE_APP


def normalize_l2(vector: np.ndarray) -> np.ndarray:
    """Computes L2 normalization of an embedding vector."""
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def encode_face(
    image_path: Union[str, Path],
    require_face: bool = True,
    warn_callback: Optional[callable] = None
) -> FaceEncodingResult:
    """
    Detects and encodes faces in an image.

    Args:
        image_path: Path to the image file
        require_face: If True, raises NoFaceDetectedError if face_count == 0
        warn_callback: Optional callback to notify when multiple faces are detected

    Returns:
        FaceEncodingResult with primary embedding, bbox, det_score, and face count.
    """
    path_str = str(Path(image_path).resolve())
    img = cv2.imread(path_str)
    if img is None:
        raise FaceDetectionError(f"Could not read image file at {path_str}")

    app = get_face_analysis_app()
    faces = app.get(img)

    face_count = len(faces)
    if face_count == 0:
        if require_face:
            raise NoFaceDetectedError(f"No face detected in image: {path_str}")
        return FaceEncodingResult(
            embedding=np.zeros(512, dtype=np.float32),
            bbox=(0, 0, 0, 0),
            det_score=0.0,
            face_count=0,
            all_embeddings=[]
        )

    # If multiple faces detected, select the one with largest bounding box area
    if face_count > 1 and warn_callback:
        warn_callback(f"Multiple faces detected ({face_count}). Selecting largest primary face.")

    def bbox_area(face) -> float:
        bbox = face.bbox
        return max(0.0, float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])))

    sorted_faces = sorted(faces, key=bbox_area, reverse=True)
    primary_face = sorted_faces[0]

    all_normalized_embeddings = [
        normalize_l2(f.embedding.astype(np.float32)) for f in faces if hasattr(f, "embedding") and f.embedding is not None
    ]

    primary_embedding = normalize_l2(primary_face.embedding.astype(np.float32))
    bbox = tuple(map(int, primary_face.bbox))
    det_score = float(primary_face.det_score) if hasattr(primary_face, "det_score") else 1.0

    return FaceEncodingResult(
        embedding=primary_embedding,
        bbox=bbox,
        det_score=round(det_score, 4),
        face_count=face_count,
        all_embeddings=all_normalized_embeddings
    )
