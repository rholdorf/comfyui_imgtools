"""Morph utility functions for face shape morphing.

Provides control point selection, inter-eye distance normalization,
boundary anchor generation, TPS warp computation, and feathered mask generation.
Uses scikit-image only (no OpenCV).
"""

import numpy as np
from skimage.filters import gaussian
from skimage.transform import ThinPlateSplineTransform

from .alignment import compute_eye_centers
from .face_mask import FACE_OVAL_INDICES, generate_face_mask

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


def compute_morph_warp(source_lms, target_lms, strength, img_shape):
    """Compute a TPS transform that morphs source face shape toward target.

    Selects control points, normalizes by inter-eye distance, interpolates
    by strength, and estimates a ThinPlateSplineTransform.

    Args:
        source_lms: numpy array (478, 2) source face landmarks in pixel coords.
        target_lms: numpy array (478, 2) target face landmarks in pixel coords.
        strength: float in [0.0, 1.0], morph intensity.
        img_shape: tuple (H, W) of the image dimensions.

    Returns:
        ThinPlateSplineTransform instance, or None if estimation fails.
    """
    # 1. Select control points
    src_pts = source_lms[MORPH_CONTROL_INDICES]
    tgt_pts = target_lms[MORPH_CONTROL_INDICES]

    # 2. Normalize by inter-eye distance
    src_eye_centers = compute_eye_centers(source_lms)
    tgt_eye_centers = compute_eye_centers(target_lms)

    src_norm, src_ied = normalize_landmarks(src_pts, src_eye_centers)
    tgt_norm, _ = normalize_landmarks(tgt_pts, tgt_eye_centers)

    # 3. Interpolate by strength in normalized space
    morphed_norm = src_norm + strength * (tgt_norm - src_norm)

    # 4. Denormalize back to source pixel space
    left_eye, right_eye = src_eye_centers
    center = (left_eye + right_eye) / 2.0
    morphed_px = morphed_norm * src_ied + center

    # 5. Add boundary anchors (map to themselves)
    h, w = img_shape[:2]
    anchors = _get_boundary_anchors(w, h)
    src_with_anchors = np.vstack([src_pts, anchors])
    dst_with_anchors = np.vstack([morphed_px, anchors])

    # 5b. Remove near-duplicate source points (causes TPS numerical instability)
    # Keep the first occurrence of each unique position (within tolerance)
    keep_mask = np.ones(len(src_with_anchors), dtype=bool)
    for i in range(1, len(src_with_anchors)):
        if not keep_mask[i]:
            continue
        dists = np.linalg.norm(src_with_anchors[:i][keep_mask[:i]] - src_with_anchors[i], axis=1)
        if dists.min() < 1e-3:
            keep_mask[i] = False
    src_with_anchors = src_with_anchors[keep_mask]
    dst_with_anchors = dst_with_anchors[keep_mask]

    # 6. Estimate TPS: dst->src order because warp() uses inverse mapping
    tps = ThinPlateSplineTransform()
    success = tps.estimate(dst_with_anchors, src_with_anchors)

    if success is False:
        return None

    return tps


def generate_feathered_mask(landmarks_px, img_h, img_w):
    """Generate a soft-edged face mask from landmarks using Gaussian blur.

    Creates a binary face mask from the face oval and applies Gaussian
    smoothing to produce feathered edges suitable for compositing.

    Args:
        landmarks_px: numpy array (478, 2) with (x, y) pixel coordinates.
        img_h: Height of the output mask.
        img_w: Width of the output mask.

    Returns:
        numpy array of shape (img_h, img_w), dtype float32,
        with soft edges from Gaussian blur.
    """
    # Generate binary mask from face oval
    mask = generate_face_mask(landmarks_px, img_h, img_w)

    # Feather edges with Gaussian blur: sigma = ~7% of face size
    face_size = max(img_h, img_w)
    sigma = face_size * 0.07
    feathered = gaussian(mask, sigma=sigma)

    return feathered.astype(np.float32)
