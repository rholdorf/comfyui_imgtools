"""Morph utility functions for face shape morphing.

Provides control point selection, inter-eye distance normalization,
boundary anchor generation, TPS warp computation, and feathered mask generation.
Uses scikit-image only (no OpenCV).
"""

import numpy as np

from .face_mask import FACE_OVAL_INDICES

# Curated subset of 67 MediaPipe face mesh landmark indices for TPS warping.
# Covers face oval (36), eye corners (4), eyebrow endpoints (6),
# nose outline (8), and lip contour (13).
MORPH_CONTROL_INDICES = sorted(set(
    FACE_OVAL_INDICES +  # 36 contour
    [33, 133, 362, 263] +  # eye corners
    [46, 55, 107, 276, 285, 336] +  # eyebrow key points
    [1, 4, 5, 48, 115, 220, 275, 440] +  # nose outline
    [0, 13, 14, 17, 61, 78, 82, 87, 267, 291, 308, 312, 317]  # lip contour
))


def normalize_landmarks(landmarks_px, eye_centers):
    """Normalize landmarks by inter-eye distance for size-independent comparison.

    Centers landmarks on the midpoint between eyes and scales by inter-eye
    distance so that IED = 1.0 in normalized space.

    Args:
        landmarks_px: numpy array of shape (N, 2) with (x, y) pixel coordinates.
        eye_centers: tuple of (left_eye, right_eye), each a numpy array of shape (2,).

    Returns:
        Tuple of (normalized_landmarks, ied) where normalized_landmarks has the
        same shape as input and ied is the inter-eye distance float.
        If IED is near zero, returns (original landmarks, 1.0) as fallback.
    """
    left_eye, right_eye = eye_centers
    ied = float(np.linalg.norm(left_eye - right_eye))

    if ied < 1e-6:
        return landmarks_px, 1.0

    center = (left_eye + right_eye) / 2.0
    normalized = (landmarks_px - center) / ied
    return normalized, ied


def _get_boundary_anchors(width, height):
    """Generate boundary anchor points for TPS edge pinning.

    Returns 12 points: 4 corners + 8 edge points (midpoints and quarter points)
    that map to themselves to prevent TPS from distorting crop borders.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        numpy array of shape (12, 2) with (x, y) coordinates, dtype float64.
    """
    w = width - 1
    h = height - 1
    return np.array([
        [0, 0], [w, 0], [0, h], [w, h],              # corners
        [w / 2, 0], [w / 2, h], [0, h / 2], [w, h / 2],  # edge midpoints
        [w / 4, 0], [3 * w / 4, 0], [0, h / 4], [0, 3 * h / 4],  # quarter points
    ], dtype=np.float64)
