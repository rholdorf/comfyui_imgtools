"""FaceModelMorph ComfyUI node for model-based face shape morphing.

Applies a pre-built canonical face model (FACE_MODEL) to a source face,
morphing the source face shape toward the model's proportions using
Thin Plate Spline warping. Supports pose-aware delta computation with
cosine attenuation and Procrustes fallback for faces without pose data.

Uses scikit-image only (no OpenCV).
"""

import math

import numpy as np
import torch
from skimage.transform import ThinPlateSplineTransform, warp

from .utils.alignment import compute_eye_centers
from .utils.morph_utils import (
    MORPH_CONTROL_INDICES,
    _MORPH_MIDLINE_INDICES,
    _MORPH_MIRROR_PAIRS,
    _get_boundary_anchors,
    _symmetrize_delta,
    generate_feathered_mask,
    procrustes_align,
)
from .utils.pose_utils import (
    compute_head_dimensions,
    frontalize_landmarks,
    normalize_landmarks_3d,
)


def _symmetrize_model(canonical_2d):
    """Force canonical landmarks to bilateral symmetry.

    For each mirror pair, averages their X-distances from the midline
    and Y positions. For midline points, snaps X to the midline.

    Args:
        canonical_2d: numpy array (478, 2) of IPD-normalized 2D landmarks.

    Returns:
        numpy array (478, 2) with bilateral symmetry enforced.
    """
    sym = canonical_2d.copy()

    # Compute midline X from midline landmarks
    midline_x = np.mean([sym[idx, 0] for idx in _MORPH_MIDLINE_INDICES])

    for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
        # Average distance from midline
        dist_a = abs(sym[lm_a, 0] - midline_x)
        dist_b = abs(sym[lm_b, 0] - midline_x)
        avg_dist = (dist_a + dist_b) / 2

        # Assign: left of midline gets -avg_dist, right gets +avg_dist
        if sym[lm_a, 0] < sym[lm_b, 0]:
            sym[lm_a, 0] = midline_x - avg_dist
            sym[lm_b, 0] = midline_x + avg_dist
        else:
            sym[lm_a, 0] = midline_x + avg_dist
            sym[lm_b, 0] = midline_x - avg_dist

        # Average Y
        avg_y = (sym[lm_a, 1] + sym[lm_b, 1]) / 2
        sym[lm_a, 1] = avg_y
        sym[lm_b, 1] = avg_y

    # Midline points: snap to midline X
    for idx in _MORPH_MIDLINE_INDICES:
        sym[idx, 0] = midline_x

    return sym


class FaceModelMorph:
    """Morph source face shape toward a canonical face model's proportions."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "face_model": ("FACE_MODEL",),
                "source_landmarks": ("FACE_LANDMARKS",),
                "source_align_data": ("ALIGN_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
            },
            "optional": {
                "symmetrize": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "ALIGN_DATA")
    RETURN_NAMES = ("morphed_face", "warp_mask", "align_data")
    FUNCTION = "morph"
    CATEGORY = "imgtools/face"

    def morph(self, source_image, face_model, source_landmarks,
              source_align_data, strength=0.5, symmetrize=False):
        """Morph source face shape toward a canonical face model.

        Args:
            source_image: ComfyUI IMAGE tensor [1, H, W, 3] float32.
            face_model: FACE_MODEL dict with canonical_landmarks, head_dimensions.
            source_landmarks: FACE_LANDMARKS list of dicts.
            source_align_data: ALIGN_DATA dict to pass through.
            strength: float in [0.0, 1.0], morph intensity.
            symmetrize: bool, if True force model to bilateral symmetry.

        Returns:
            Tuple of (morphed_face IMAGE, warp_mask MASK, align_data ALIGN_DATA).
        """
        h, w = source_image.shape[1], source_image.shape[2]

        # Validate face_model
        if not face_model or not isinstance(face_model, dict):
            print("[FaceModelMorph] Warning: empty or invalid face_model, returning passthrough")
            return self._passthrough(source_image, h, w, source_align_data)

        required_keys = ("canonical_landmarks", "head_dimensions")
        missing = [k for k in required_keys if k not in face_model]
        if missing:
            print(f"[FaceModelMorph] Warning: face_model missing keys: {missing}, returning passthrough")
            return self._passthrough(source_image, h, w, source_align_data)

        if face_model["canonical_landmarks"].shape != (478, 2):
            print(f"[FaceModelMorph] Warning: canonical_landmarks shape mismatch: "
                  f"expected (478, 2), got {face_model['canonical_landmarks'].shape}, returning passthrough")
            return self._passthrough(source_image, h, w, source_align_data)

        try:
            # 1. Validate landmarks
            if (not source_landmarks or len(source_landmarks) == 0):
                return self._passthrough(source_image, h, w, source_align_data)

            face = source_landmarks[0]
            src_lms_px = face["landmarks"]       # (478, 2) pixel coords
            src_3d = face["landmarks_3d"]         # (478, 3)
            pose = face.get("pose")               # dict or None

            # 2. IED check
            src_eye_centers = compute_eye_centers(src_lms_px)
            src_ied = float(np.linalg.norm(
                src_eye_centers[0] - src_eye_centers[1]
            ))
            if src_ied < 1e-6:
                return self._passthrough(source_image, h, w, source_align_data)

            # 3. Get model canonical landmarks
            model_canonical = face_model["canonical_landmarks"]  # (478, 2)
            if symmetrize:
                model_canonical = _symmetrize_model(model_canonical)

            # 4. Compute delta (pose-aware or fallback)
            if pose is not None:
                px_delta, effective_strength, head_scale = (
                    self._compute_pose_aware_delta(
                        src_lms_px, src_3d, pose, model_canonical,
                        face_model, strength, src_ied, src_eye_centers
                    )
                )
            else:
                px_delta, effective_strength, head_scale = (
                    self._compute_fallback_delta(
                        src_lms_px, src_3d, model_canonical,
                        face_model, strength, src_ied, src_eye_centers
                    )
                )

            # 5. Apply delta to source control points
            src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]
            morphed_ctrl = src_ctrl_px + effective_strength * px_delta

            # 6. Add boundary anchors
            anchors = _get_boundary_anchors(w, h)
            src_with_anchors = np.vstack([src_ctrl_px, anchors])
            dst_with_anchors = np.vstack([morphed_ctrl, anchors])

            # 7. Remove near-duplicate source points (TPS stability)
            keep_mask = np.ones(len(src_with_anchors), dtype=bool)
            for i in range(1, len(src_with_anchors)):
                if not keep_mask[i]:
                    continue
                dists = np.linalg.norm(
                    src_with_anchors[:i][keep_mask[:i]] - src_with_anchors[i],
                    axis=1,
                )
                if dists.min() < 1e-3:
                    keep_mask[i] = False
            src_with_anchors = src_with_anchors[keep_mask]
            dst_with_anchors = dst_with_anchors[keep_mask]

            # 8. Estimate TPS (dst->src for inverse mapping)
            tps = ThinPlateSplineTransform()
            success = tps.estimate(dst_with_anchors, src_with_anchors)
            if success is False:
                return self._passthrough(source_image, h, w, source_align_data)

            # 9. Apply warp
            img_np = source_image[0].cpu().numpy().astype(np.float64)
            warped = warp(
                img_np, inverse_map=tps,
                output_shape=(h, w),
                order=1, mode="constant", cval=0.0,
                preserve_range=True,
            )

            # 10. Generate feathered mask from morphed landmarks
            morphed_full_lms = src_lms_px.copy()
            for i, ctrl_idx in enumerate(MORPH_CONTROL_INDICES):
                morphed_full_lms[ctrl_idx] = morphed_ctrl[i]
            mask_np = generate_feathered_mask(morphed_full_lms, h, w)

            # 11. Store head_scale in align_data
            out_align_data = dict(source_align_data)
            out_align_data["head_scale"] = float(head_scale)

            # 12. Convert to tensors
            morphed_tensor = torch.from_numpy(
                warped.astype(np.float32)
            ).unsqueeze(0)
            mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)

            return (morphed_tensor, mask_tensor, out_align_data)

        except Exception as e:
            print(f"[FaceModelMorph] Warning: morph failed: {e}")
            return self._passthrough(source_image, h, w, source_align_data)

    def _compute_pose_aware_delta(
        self, src_lms_px, src_3d, pose, model_canonical,
        face_model, strength, src_ied, src_eye_centers
    ):
        """Compute pixel-space delta using pose-aware frontalization.

        Pipeline: frontalize source 3D -> normalize by IPD -> project to 2D
        -> delta vs model canonical -> scale by source IED -> symmetrize
        -> attenuate by pose.

        Returns:
            Tuple of (px_delta, effective_strength, head_scale).
        """
        # 1. Frontalize source 3D landmarks
        src_front = frontalize_landmarks(src_3d, pose["matrix"])

        # 2. Normalize by IPD
        src_norm, src_ipd = normalize_landmarks_3d(src_front)

        # 3. Project to 2D
        src_norm_2d = src_norm[:, :2]  # (478, 2)

        # 4. Extract control points
        model_ctrl = model_canonical[MORPH_CONTROL_INDICES]   # (42, 2)
        src_ctrl = src_norm_2d[MORPH_CONTROL_INDICES]          # (42, 2)

        # 5. Delta in normalized space
        norm_delta = model_ctrl - src_ctrl  # (42, 2)

        # 6. Scale delta back to pixel space using source IED
        px_delta = norm_delta * src_ied  # (42, 2)

        # 7. Symmetrize delta
        src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]
        px_delta = _symmetrize_delta(px_delta, src_ctrl_px)

        # 8. Pose attenuation
        yaw = pose.get("yaw", 0.0)
        pitch = pose.get("pitch", 0.0)
        attenuation = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
        effective_strength = strength * attenuation

        # 9. Head scale
        head_scale = self._compute_head_scale(
            src_3d, src_ipd, face_model, effective_strength
        )

        return px_delta, effective_strength, head_scale

    def _compute_fallback_delta(
        self, src_lms_px, src_3d, model_canonical,
        face_model, strength, src_ied, src_eye_centers
    ):
        """Compute pixel-space delta using Procrustes fallback (no pose data).

        Returns:
            Tuple of (px_delta, strength, head_scale).
        """
        # 1. Scale model control points to source pixel space via IED
        model_ctrl = model_canonical[MORPH_CONTROL_INDICES]  # (42, 2)
        src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]      # (42, 2)

        # Eye midpoint for translation
        eye_midpoint = (src_eye_centers[0] + src_eye_centers[1]) / 2.0
        model_scaled = model_ctrl * src_ied + eye_midpoint

        # 2. Procrustes align model to source
        aligned_model, scale_ratio = procrustes_align(src_ctrl_px, model_scaled)

        # 3. Delta and symmetrize
        delta = aligned_model - src_ctrl_px
        delta = _symmetrize_delta(delta, src_ctrl_px)

        # 4. Head scale (use raw 3D landmarks)
        head_scale = self._compute_head_scale(
            src_3d, None, face_model, strength
        )

        return delta, strength, head_scale

    def _compute_head_scale(self, src_3d, src_ipd, face_model, effective_strength):
        """Compute head scale ratio from model vs source head dimensions.

        Args:
            src_3d: (478, 3) source 3D landmarks.
            src_ipd: float IPD from normalization, or None for fallback.
            face_model: FACE_MODEL dict with head_dimensions.
            effective_strength: float, strength after attenuation.

        Returns:
            float head_scale interpolated by effective_strength.
        """
        # Check for synthetic/degenerate 3D landmarks
        if np.allclose(src_3d, 0.0):
            return 1.0

        # Get source IPD if not provided
        if src_ipd is None:
            _, src_ipd = normalize_landmarks_3d(src_3d)

        # Source head dimensions
        src_head_dims = compute_head_dimensions(src_3d, src_ipd)
        model_head_dims = face_model["head_dimensions"]

        # Avoid division by zero
        if src_head_dims["width"] < 1e-8:
            return 1.0

        head_scale_raw = model_head_dims["width"] / src_head_dims["width"]
        head_scale = 1.0 + effective_strength * (head_scale_raw - 1.0)
        return head_scale

    @staticmethod
    def _passthrough(source_image, h, w, align_data):
        """Return source image unmodified with a full (ones) mask."""
        full_mask = torch.ones(1, h, w, dtype=torch.float32)
        return (source_image, full_mask, align_data)
