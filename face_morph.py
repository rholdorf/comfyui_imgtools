"""FaceShapeMorph ComfyUI node for face shape morphing.

Takes two cropped/aligned faces and morphs the source face shape toward
the target face shape using Thin Plate Spline warping.
Uses scikit-image only (no OpenCV).
"""

import numpy as np
import torch
from skimage.transform import warp

from .utils.alignment import compute_eye_centers
from .utils.morph_utils import (
    MORPH_CONTROL_INDICES,
    compute_morph_warp,
    generate_feathered_mask,
)


class FaceShapeMorph:
    """Morph source face shape toward target face proportions."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "target_image": ("IMAGE",),
                "source_landmarks": ("FACE_LANDMARKS",),
                "target_landmarks": ("FACE_LANDMARKS",),
                "source_align_data": ("ALIGN_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "ALIGN_DATA")
    RETURN_NAMES = ("morphed_face", "warp_mask", "align_data")
    FUNCTION = "morph"
    CATEGORY = "imgtools/face"

    def morph(self, source_image, target_image, source_landmarks, target_landmarks,
              source_align_data, strength=0.5):
        """Morph source face shape toward target face shape.

        Args:
            source_image: ComfyUI IMAGE tensor [1, H, W, 3] float32.
            target_image: ComfyUI IMAGE tensor [1, H, W, 3] float32 (unused for warp).
            source_landmarks: FACE_LANDMARKS list of dicts with 'landmarks' (478,2).
            target_landmarks: FACE_LANDMARKS list of dicts with 'landmarks' (478,2).
            source_align_data: ALIGN_DATA dict to pass through.
            strength: float in [0.0, 1.0], morph intensity.

        Returns:
            Tuple of (morphed_face IMAGE, warp_mask MASK, align_data ALIGN_DATA).
        """
        h, w = source_image.shape[1], source_image.shape[2]

        try:
            # 1. Validate landmarks
            if (not source_landmarks or not target_landmarks
                    or len(source_landmarks) == 0 or len(target_landmarks) == 0):
                return self._passthrough(source_image, h, w, source_align_data)

            src_lms = source_landmarks[0]["landmarks"]
            tgt_lms = target_landmarks[0]["landmarks"]

            # 2. Check for degenerate landmarks (zero inter-eye distance)
            src_eye_centers = compute_eye_centers(src_lms)
            left_eye, right_eye = src_eye_centers
            ied = float(np.linalg.norm(left_eye - right_eye))
            if ied < 1e-6:
                return self._passthrough(source_image, h, w, source_align_data)

            # 3. Convert source image to numpy
            img_np = source_image[0].cpu().numpy().astype(np.float64)

            # 4. Compute TPS transform (Procrustes-aligned, pose-invariant)
            tps, morphed_ctrl_px, head_scale = compute_morph_warp(src_lms, tgt_lms, strength, (h, w))
            if tps is None:
                return self._passthrough(source_image, h, w, source_align_data)

            # 5. Apply warp
            warped = warp(
                img_np, inverse_map=tps,
                output_shape=(h, w),
                order=1, mode="constant", cval=0.0,
                preserve_range=True,
            )

            # 6. Generate feathered mask from morphed landmark positions.
            # Uses ONLY the morphed oval (not source) to avoid showing
            # TPS-stretched background between the shrunk face and crop edge.
            morphed_full_lms = src_lms.copy()
            for i, ctrl_idx in enumerate(MORPH_CONTROL_INDICES):
                morphed_full_lms[ctrl_idx] = morphed_ctrl_px[i]

            mask_np = generate_feathered_mask(morphed_full_lms, h, w)

            # 7. Store head_scale in align_data for composite scaling
            out_align_data = dict(source_align_data)
            out_align_data["head_scale"] = float(head_scale)

            # 8. Convert to tensors
            morphed_tensor = torch.from_numpy(
                warped.astype(np.float32)
            ).unsqueeze(0)
            mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)

            return (morphed_tensor, mask_tensor, out_align_data)

        except Exception:
            return self._passthrough(source_image, h, w, source_align_data)

    @staticmethod
    def _passthrough(source_image, h, w, align_data):
        """Return source image unmodified with a full (ones) mask."""
        full_mask = torch.ones(1, h, w, dtype=torch.float32)
        return (source_image, full_mask, align_data)
