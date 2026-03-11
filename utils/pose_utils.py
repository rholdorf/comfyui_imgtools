"""Pose utility functions for 3D face analysis.

Provides pose angle extraction from MediaPipe's 4x4 transformation matrix,
3D landmark frontalization via inverse rotation, IPD normalization for
cross-image comparability, and head dimensions estimation.

All functions use SciPy's Rotation class (already a transitive dependency
via scikit-image) and NumPy. No new dependencies required.
"""

import numpy as np
from scipy.spatial.transform import Rotation

# MediaPipe 478-landmark model iris center indices.
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473


def _extract_pure_rotation(transform_matrix: np.ndarray) -> Rotation:
    """Extract a pure rotation from a 4x4 transform, removing uniform scale.

    Args:
        transform_matrix: 4x4 transformation matrix (may include scale).

    Returns:
        SciPy Rotation object representing the pure rotation.
    """
    rot3 = transform_matrix[:3, :3].copy()
    det = np.linalg.det(rot3)
    if abs(det) > 1e-12:
        scale = np.cbrt(det)
        rot3 = rot3 / scale
    return Rotation.from_matrix(rot3)


def extract_pose_angles(transform_matrix: np.ndarray) -> dict:
    """Extract pitch, yaw, roll angles from a 4x4 transformation matrix.

    Uses SciPy Rotation to decompose the rotation into Euler angles.
    Handles uniform scale by normalizing the 3x3 rotation sub-matrix.

    Args:
        transform_matrix: numpy array (4, 4) — MediaPipe face geometry
            transformation matrix (may include uniform scale).

    Returns:
        Dict with keys:
        - pitch: float, rotation around X axis in degrees
        - yaw: float, rotation around Y axis in degrees
        - roll: float, rotation around Z axis in degrees
        - matrix: the original 4x4 transform_matrix (ndarray)
    """
    r = _extract_pure_rotation(transform_matrix)
    pitch, yaw, roll = r.as_euler("XYZ", degrees=True)
    return {
        "pitch": float(pitch),
        "yaw": float(yaw),
        "roll": float(roll),
        "matrix": transform_matrix,
    }


def frontalize_landmarks(
    landmarks_3d: np.ndarray, transform_matrix: np.ndarray
) -> np.ndarray:
    """Frontalize 3D landmarks by applying the inverse of the head rotation.

    Centers landmarks on their centroid, applies the inverse rotation to
    undo head pose, then re-adds the centroid. The result approximates
    what the landmarks would look like from a frontal viewpoint.

    Args:
        landmarks_3d: numpy array (478, 3) of 3D landmark coordinates.
        transform_matrix: numpy array (4, 4) — transformation matrix
            representing the head pose (rotation + optional scale).

    Returns:
        numpy array (478, 3) of frontalized landmark coordinates.
    """
    r = _extract_pure_rotation(transform_matrix)
    r_inv = r.inv()

    centroid = landmarks_3d.mean(axis=0)
    centered = landmarks_3d - centroid
    frontalized = r_inv.apply(centered)
    return frontalized + centroid


def normalize_landmarks_3d(
    landmarks_3d: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Normalize 3D landmarks by inter-pupillary distance (IPD).

    Centers landmarks on the midpoint between iris centers and scales
    so that the 3D Euclidean IPD equals 1.0. This enables cross-image
    comparison of face geometry regardless of original scale.

    Args:
        landmarks_3d: numpy array (478, 3) of 3D landmark coordinates.

    Returns:
        Tuple of (normalized_landmarks, original_ipd) where:
        - normalized_landmarks: (478, 3) centered and scaled so IPD = 1.0
        - original_ipd: float, the original inter-pupillary distance.
          Returns 1.0 if IPD is near-zero (degenerate case).
    """
    left_iris = landmarks_3d[LEFT_IRIS_CENTER]
    right_iris = landmarks_3d[RIGHT_IRIS_CENTER]
    ipd = float(np.linalg.norm(left_iris - right_iris))

    if ipd < 1e-8:
        return landmarks_3d.copy(), 1.0

    midpoint = (left_iris + right_iris) / 2.0
    normalized = (landmarks_3d - midpoint) / ipd
    return normalized, ipd


def compute_head_dimensions(
    landmarks_3d: np.ndarray, ipd: float
) -> dict:
    """Compute head bounding-box dimensions in IPD-normalized units.

    Args:
        landmarks_3d: numpy array (478, 3) of 3D landmark coordinates.
        ipd: float, inter-pupillary distance for normalization.

    Returns:
        Dict with keys width, height, depth — each a float representing
        the bounding-box extent along that axis divided by IPD.
    """
    if ipd < 1e-8:
        ipd = 1.0

    extents = landmarks_3d.max(axis=0) - landmarks_3d.min(axis=0)
    return {
        "width": float(extents[0] / ipd),
        "height": float(extents[1] / ipd),
        "depth": float(extents[2] / ipd),
    }
