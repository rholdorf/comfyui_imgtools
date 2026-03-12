"""FaceCropAlign ComfyUI node for face cropping and alignment.

Takes an IMAGE and FACE_LANDMARKS from FaceDetect, produces a cropped/aligned
face image, alignment transform data for reversal, and a face mask.
Uses scikit-image only (no OpenCV).
"""

import numpy as np
import torch
from skimage.transform import AffineTransform

from .utils.alignment import (
    apply_alignment,
    build_alignment_transform,
    compute_eye_centers,
    compute_padded_crop_box,
)
from .utils.face_mask import generate_face_mask


class FaceCropAlign:
    """Crop and align a face from an image using MediaPipe landmarks."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "landmarks": ("FACE_LANDMARKS",),
            },
            "optional": {
                "face_index": ("INT", {"default": 0, "min": 0, "max": 9}),
                "padding": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
                "align": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "ALIGN_DATA", "MASK", "FACE_LANDMARKS")
    RETURN_NAMES = ("cropped_face", "align_data", "face_mask", "crop_landmarks")
    FUNCTION = "crop_and_align"
    CATEGORY = "imgtools/face"

    def crop_and_align(self, image, landmarks, face_index=0, padding=0.3, align=True):
        # Clamp face_index to valid range
        idx = min(face_index, len(landmarks) - 1)

        # Get selected face landmarks
        landmarks_px = landmarks[idx]["landmarks"]

        # Convert image tensor to numpy: (H, W, 3) float64
        img_np = image[0].cpu().numpy().astype(np.float64)
        h, w = img_np.shape[:2]

        if align:
            transform, angle = build_alignment_transform(landmarks_px, w, h)
            aligned = apply_alignment(img_np, transform)
        else:
            transform = AffineTransform()  # identity
            angle = 0.0
            aligned = img_np

        # Compute padded crop box
        x1, y1, x2, y2 = compute_padded_crop_box(landmarks_px, transform, padding, w, h)

        # Defensive: ensure non-zero crop dimensions
        if x2 <= x1 or y2 <= y1:
            cropped = np.zeros((1, 1, 3), dtype=np.float32)
            mask_np = np.zeros((1, 1), dtype=np.float32)
            crop_landmarks_out = []
        else:
            # Crop aligned image
            cropped = aligned[y1:y2, x1:x2]

            # Transform landmarks to crop space for mask generation
            aligned_landmarks = transform(landmarks_px)
            crop_landmarks = aligned_landmarks.copy()
            crop_landmarks[:, 0] -= x1
            crop_landmarks[:, 1] -= y1

            crop_h = y2 - y1
            crop_w = x2 - x1
            mask_np = generate_face_mask(crop_landmarks, crop_h, crop_w)

            # Package crop-space landmarks in FACE_LANDMARKS format
            crop_landmarks_out = [{
                "landmarks": crop_landmarks,
                "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
                "pose": landmarks[idx].get("pose"),
            }]

        # Compute rotation center (eye midpoint)
        left_eye, right_eye = compute_eye_centers(landmarks_px)
        rotation_center = tuple(((left_eye + right_eye) / 2.0).tolist())

        # Build align_data dict for Phase 4 reversal
        align_data = {
            "rotation_angle": float(angle),
            "rotation_center": rotation_center,
            "crop_box": (x1, y1, x2, y2),
            "original_size": (w, h),
            "transform_matrix": transform.params,
        }

        # Convert outputs to tensors
        cropped_tensor = torch.from_numpy(cropped.astype(np.float32)).unsqueeze(0)
        mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)

        return (cropped_tensor, align_data, mask_tensor, crop_landmarks_out)
