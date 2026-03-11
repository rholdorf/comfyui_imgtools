"""Core pipeline functions for building a canonical face model from images.

Provides directory scanning, per-image face processing with pose filtering,
weighted 3D landmark averaging, and end-to-end model building orchestration.

All functions are independent of ComfyUI so they remain testable in isolation.
The FaceModelBuilder node (Plan 02) will call these functions.
"""

import math
from pathlib import Path

import numpy as np
import mediapipe as mp
from PIL import Image

from utils.landmarks import extract_landmarks
from utils.mediapipe_helper import get_landmarker
from utils.model_io import save_face_model
from utils.morph_utils import MORPH_CONTROL_INDICES
from utils.pose_utils import (
    compute_head_dimensions,
    frontalize_landmarks,
    normalize_landmarks_3d,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def scan_images(directory: str) -> list[Path]:
    """Flat scan of a directory for supported image files.

    Args:
        directory: Path to directory containing images.

    Returns:
        Sorted list of Path objects for supported image files.

    Raises:
        ValueError: If directory does not exist or is not a directory.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    images = []
    for p in sorted(dir_path.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(p)
    return images


def process_image(
    image_path: Path,
    landmarker,
    yaw_threshold: float = 45.0,
    pitch_threshold: float = 30.0,
) -> dict:
    """Process a single image: detect face, check pose, normalize landmarks.

    Args:
        image_path: Path to the image file.
        landmarker: A MediaPipe FaceLandmarker instance.
        yaw_threshold: Maximum |yaw| in degrees to accept a face.
        pitch_threshold: Maximum |pitch| in degrees to accept a face.

    Returns:
        Dict with keys: filename, status, yaw, pitch, roll, confidence,
        weight, normalized_3d, head_dims.
    """
    filename = image_path.name

    # Load image
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img, dtype=np.uint8)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)
    h, w = img_np.shape[:2]

    # Detect faces
    result = landmarker.detect(mp_image)
    faces = extract_landmarks(result, w, h)

    if not faces:
        return {
            "filename": filename,
            "status": "NO FACE",
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "confidence": 0.0,
            "weight": 0.0,
            "normalized_3d": None,
            "head_dims": None,
        }

    # Use the first detected face
    face = faces[0]
    pose = face["pose"]
    lm3d = face["landmarks_3d"]

    # Extract confidence from MediaPipe result if available
    confidence = 0.0
    if (hasattr(result, "face_landmarks") and result.face_landmarks
            and len(result.face_landmarks) > 0
            and hasattr(result.face_landmarks[0][0], "presence")):
        confidence = float(result.face_landmarks[0][0].presence)

    if pose is None:
        # Fallback: no transformation matrix available
        # Use landmarks_3d directly (no frontalization), weight=1.0
        normalized, ipd = normalize_landmarks_3d(lm3d)
        head_dims = compute_head_dimensions(lm3d, ipd)
        return {
            "filename": filename,
            "status": "ACCEPTED",
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "confidence": confidence,
            "weight": 1.0,
            "normalized_3d": normalized,
            "head_dims": head_dims,
        }

    yaw = pose["yaw"]
    pitch = pose["pitch"]
    roll = pose["roll"]

    # Check pose thresholds
    if abs(yaw) > yaw_threshold or abs(pitch) > pitch_threshold:
        return {
            "filename": filename,
            "status": "REJECTED",
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "confidence": confidence,
            "weight": 0.0,
            "normalized_3d": None,
            "head_dims": None,
        }

    # Accepted: frontalize, normalize, compute weight
    weight = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
    frontalized = frontalize_landmarks(lm3d, pose["matrix"])
    normalized, ipd = normalize_landmarks_3d(frontalized)
    head_dims = compute_head_dimensions(lm3d, ipd)

    return {
        "filename": filename,
        "status": "ACCEPTED",
        "yaw": yaw,
        "pitch": pitch,
        "roll": roll,
        "confidence": confidence,
        "weight": weight,
        "normalized_3d": normalized,
        "head_dims": head_dims,
    }


def compute_weighted_average(
    accepted_data: list[dict],
) -> tuple[np.ndarray, np.ndarray]:
    """Compute weighted average and stddev of normalized 3D landmarks.

    Args:
        accepted_data: List of dicts, each with 'normalized_3d' (478,3)
            and 'weight' (float).

    Returns:
        Tuple of (mean_3d (478,3), stddev_3d (478,3)).
    """
    weights = np.array([d["weight"] for d in accepted_data])
    total_weight = weights.sum()

    landmarks_stack = np.stack(
        [d["normalized_3d"] for d in accepted_data]
    )  # (N, 478, 3)
    w = weights[:, None, None]  # (N, 1, 1)

    weighted_mean = (landmarks_stack * w).sum(axis=0) / total_weight  # (478, 3)

    # Weighted stddev
    diffs = landmarks_stack - weighted_mean[None, :, :]  # (N, 478, 3)
    weighted_var = (w * diffs**2).sum(axis=0) / total_weight  # (478, 3)
    stddev = np.sqrt(weighted_var)  # (478, 3)

    return weighted_mean, stddev


def build_face_model(
    directory: str,
    yaw_threshold: float = 45.0,
    pitch_threshold: float = 30.0,
    save_path: str = "",
) -> tuple[dict, list[dict], str]:
    """Build a canonical face model from a directory of images.

    Orchestrates: scan_images -> process each -> compute_weighted_average
    -> project to 2D -> compute weighted head_dims -> save model.

    Args:
        directory: Path to directory containing face images.
        yaw_threshold: Maximum |yaw| in degrees to accept a face.
        pitch_threshold: Maximum |pitch| in degrees to accept a face.
        save_path: Where to save the model. Defaults to
            {directory}/face_model.facemodel.npz.

    Returns:
        Tuple of (model_dict, per_image_results, actual_save_path).

    Raises:
        ValueError: If no images are accepted.
    """
    image_paths = scan_images(directory)

    landmarker = get_landmarker(output_facial_transformation_matrixes=True)

    results = []
    for path in image_paths:
        result = process_image(path, landmarker, yaw_threshold, pitch_threshold)
        results.append(result)

    accepted = [r for r in results if r["status"] == "ACCEPTED"]

    if not accepted:
        raise ValueError(
            f"No accepted images in '{directory}'. "
            f"All {len(results)} images were rejected or had no face."
        )

    # Compute weighted average of 3D landmarks
    mean_3d, stddev_3d = compute_weighted_average(accepted)

    # Project to 2D: drop Z column
    canonical_2d = mean_3d[:, :2]  # (478, 2)

    # Weighted average of head dimensions
    total_weight = sum(r["weight"] for r in accepted)
    avg_head_dims = {"width": 0.0, "height": 0.0, "depth": 0.0}
    for r in accepted:
        w = r["weight"] / total_weight
        for key in avg_head_dims:
            avg_head_dims[key] += w * r["head_dims"][key]

    # Determine save path
    if not save_path:
        save_path = str(Path(directory) / "face_model.facemodel.npz")

    # Save model
    control_indices = np.array(MORPH_CONTROL_INDICES, dtype=np.int64)

    save_face_model(
        save_path,
        canonical_landmarks=canonical_2d,
        head_dimensions=avg_head_dims,
        control_indices=control_indices,
        landmark_stddev=stddev_3d,
    )

    # Build model dict (same as what load_face_model returns)
    from utils.model_io import MODEL_VERSION

    model_dict = {
        "version": MODEL_VERSION,
        "canonical_landmarks": canonical_2d,
        "head_dimensions": avg_head_dims,
        "control_indices": control_indices,
        "landmark_stddev": stddev_3d,
    }

    return model_dict, results, save_path
