"""Morph utility functions for face shape morphing.

Provides control point selection, Procrustes alignment for pose-invariant
shape comparison, boundary anchor generation, TPS warp computation,
and feathered mask generation. Uses scikit-image only (no OpenCV).
"""

import numpy as np
from skimage.filters import gaussian
from skimage.transform import ThinPlateSplineTransform

from .face_mask import FACE_OVAL_INDICES, generate_face_mask

# Curated subset of 42 MediaPipe face mesh landmark indices for TPS warping.
# Uses face oval (36) + eyebrow endpoints (6) for face SHAPE morphing.
# Interior features (eyes, nose, lips) are intentionally excluded so TPS
# changes the overall face shape without distorting individual features.
MORPH_CONTROL_INDICES = sorted(set(
    FACE_OVAL_INDICES  # 36 contour
    + [46, 55, 107, 276, 285, 336]  # eyebrow key points
))


# Left-right symmetric pairs in MORPH_CONTROL_INDICES.
# Derived from MediaPipe face mesh topology: the face oval traces a contour
# from forehead (10) clockwise to chin (152) and back, with symmetric pairs
# at equal distances from the midline.
_MORPH_MIRROR_PAIRS = [
    # Face oval (17 pairs)
    (338, 109), (297, 67), (332, 103), (284, 54), (251, 21),
    (389, 162), (356, 127), (454, 234), (323, 93), (361, 132),
    (288, 58), (397, 172), (365, 136), (379, 150), (378, 149),
    (400, 176), (377, 148),
    # Eyebrows (3 pairs)
    (46, 276), (55, 285), (107, 336),
]

# Midline landmarks: on or very near the face vertical axis.
_MORPH_MIDLINE_INDICES = [10, 152]


def procrustes_align(source_pts, target_pts):
    """Align target landmarks to source using Procrustes with scale normalization.

    Finds the optimal rotation to align target points onto source points,
    removing pose rotation AND normalizing scale. The delta after alignment
    captures pure shape differences. The scale ratio is returned separately
    so it can be applied as uniform resize during compositing.

    Args:
        source_pts: numpy array (N, 2) source control points.
        target_pts: numpy array (N, 2) target control points.

    Returns:
        Tuple of (aligned_target, scale_ratio) where:
        - aligned_target: (N, 2) target points rotated and scaled to source's
          orientation and size, centered on source.
        - scale_ratio: float, tgt_scale / src_scale (>1 = target head bigger).
    """
    src_center = source_pts.mean(axis=0)
    tgt_center = target_pts.mean(axis=0)

    src_c = source_pts - src_center
    tgt_c = target_pts - tgt_center

    # Frobenius norms
    src_scale = np.sqrt((src_c ** 2).sum())
    tgt_scale = np.sqrt((tgt_c ** 2).sum())

    if src_scale < 1e-10 or tgt_scale < 1e-10:
        return target_pts.copy(), 1.0

    scale_ratio = tgt_scale / src_scale

    # Normalize for robust rotation estimation
    src_n = src_c / src_scale
    tgt_n = tgt_c / tgt_scale

    # Optimal rotation via SVD of cross-covariance matrix
    M = tgt_n.T @ src_n  # (2, 2)
    U, S, Vt = np.linalg.svd(M)

    # Handle reflection (ensure proper rotation, not reflection)
    d = np.linalg.det(U @ Vt)
    D = np.diag([1.0, np.sign(d)])
    R = U @ D @ Vt

    # Rotate target at SOURCE scale (normalized), re-center on source
    aligned = (tgt_c / tgt_scale * src_scale) @ R + src_center

    return aligned, scale_ratio


def _symmetrize_delta(delta, src_pts):
    """Remove asymmetric horizontal component from shape delta.

    3D head yaw creates left-right asymmetry in 2D landmarks that Procrustes
    cannot fully remove. This function decomposes each mirrored pair's delta
    into symmetric (width change) and asymmetric (lateral shift) components,
    keeping only the symmetric part.

    For mirrored pairs: preserves width change, removes lateral shift.
    For midline points: zeroes horizontal delta, keeps vertical.

    Args:
        delta: numpy array (N, 2) shape delta for each control point.
        src_pts: numpy array (N, 2) source control point positions.

    Returns:
        numpy array (N, 2) symmetrized delta.
    """
    sym_delta = delta.copy()

    # Build lookup: landmark_id -> index in MORPH_CONTROL_INDICES
    ctrl_pos = {lm_id: i for i, lm_id in enumerate(MORPH_CONTROL_INDICES)}

    # Midline points: zero horizontal delta
    for lm_id in _MORPH_MIDLINE_INDICES:
        if lm_id in ctrl_pos:
            sym_delta[ctrl_pos[lm_id], 0] = 0.0

    # Mirrored pairs: preserve width change, remove lateral shift
    for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
        if lm_a not in ctrl_pos or lm_b not in ctrl_pos:
            continue

        ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
        dx_a, dy_a = delta[ia]
        dx_b, dy_b = delta[ib]

        # Determine which point is on the left vs right of midline
        if src_pts[ia, 0] < src_pts[ib, 0]:
            left_i, right_i = ia, ib
            dx_left, dx_right = dx_a, dx_b
        else:
            left_i, right_i = ib, ia
            dx_left, dx_right = dx_b, dx_a

        # Width change (positive = face getting wider)
        # = how much the right point moved right minus how much the left moved right
        width_change = dx_right - dx_left

        # Symmetric: distribute width change equally to both sides
        sym_delta[left_i, 0] = -width_change / 2
        sym_delta[right_i, 0] = width_change / 2

        # Symmetric vertical: average both sides
        dy_sym = (dy_a + dy_b) / 2
        sym_delta[ia, 1] = dy_sym
        sym_delta[ib, 1] = dy_sym

    return sym_delta


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

    Uses Procrustes alignment to remove pose differences (rotation) and
    normalize scale between source and target. The TPS handles pure shape
    changes, while head size difference is returned separately for uniform
    resize during compositing.

    Args:
        source_lms: numpy array (478, 2) source face landmarks in pixel coords.
        target_lms: numpy array (478, 2) target face landmarks in pixel coords.
        strength: float in [0.0, 1.0], morph intensity.
        img_shape: tuple (H, W) of the image dimensions.

    Returns:
        Tuple of (tps, morphed_ctrl_px, head_scale) where:
        - tps: ThinPlateSplineTransform instance, or None if estimation fails.
        - morphed_ctrl_px: (N, 2) morphed control point positions, or None.
        - head_scale: float, effective scale to apply (interpolated by strength).
          1.0 means no size change.
    """
    # 1. Select control points
    src_pts = source_lms[MORPH_CONTROL_INDICES]
    tgt_pts = target_lms[MORPH_CONTROL_INDICES]

    # 2. Procrustes-align target to source (rotation + scale normalization)
    tgt_aligned, scale_ratio = procrustes_align(src_pts, tgt_pts)

    # 3. Head scale interpolated by strength
    head_scale = 1.0 + strength * (scale_ratio - 1.0)

    # 4. Shape delta (pose-free, scale-normalized = pure shape change)
    shape_delta = tgt_aligned - src_pts

    # 3b. Symmetrize delta to remove 3D yaw artifacts
    # Procrustes removes 2D rotation but not perspective foreshortening from yaw.
    # Symmetrization preserves bilateral width/height changes (real shape) while
    # removing unilateral shifts (yaw artifact).
    shape_delta = _symmetrize_delta(shape_delta, src_pts)

    # 4. Apply shape morph with strength
    morphed_pts = src_pts + strength * shape_delta

    # 7. Add boundary anchors (map to themselves)
    h, w = img_shape[:2]
    anchors = _get_boundary_anchors(w, h)
    src_with_anchors = np.vstack([src_pts, anchors])
    dst_with_anchors = np.vstack([morphed_pts, anchors])

    # 7b. Remove near-duplicate source points (causes TPS numerical instability)
    keep_mask = np.ones(len(src_with_anchors), dtype=bool)
    for i in range(1, len(src_with_anchors)):
        if not keep_mask[i]:
            continue
        dists = np.linalg.norm(src_with_anchors[:i][keep_mask[:i]] - src_with_anchors[i], axis=1)
        if dists.min() < 1e-3:
            keep_mask[i] = False
    src_with_anchors = src_with_anchors[keep_mask]
    dst_with_anchors = dst_with_anchors[keep_mask]

    # 8. Estimate TPS: dst->src order because warp() uses inverse mapping
    tps = ThinPlateSplineTransform()
    success = tps.estimate(dst_with_anchors, src_with_anchors)

    if success is False:
        return None, None, 1.0

    return tps, morphed_pts, head_scale


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

    # Feather edges with Gaussian blur: sigma = ~2% of face size
    # Very tight feathering minimizes ghosting in the composite blend zone.
    face_size = max(img_h, img_w)
    sigma = max(face_size * 0.02, 5.0)
    feathered = gaussian(mask, sigma=sigma)

    return feathered.astype(np.float32)
