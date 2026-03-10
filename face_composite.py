"""FaceComposite ComfyUI node for compositing morphed face back into original image.

Reverses the affine alignment transform and alpha-blends the morphed face
into the original image using the warp_mask from FaceShapeMorph.
Uses scikit-image only (no OpenCV).
"""

import numpy as np
import torch
from skimage.transform import AffineTransform, warp


class FaceComposite:
    """Composite morphed face back into original image with reverse transform."""

    MARGIN_PX = 5  # Expansion margin for interpolation safety at crop edges

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "morphed_face": ("IMAGE",),
                "warp_mask": ("MASK",),
                "align_data": ("ALIGN_DATA",),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("composited_image", "face_region_mask")
    FUNCTION = "composite"
    CATEGORY = "imgtools/face"

    @staticmethod
    def _passthrough(original_image, orig_h, orig_w):
        """Return original image unmodified with an empty (zeros) mask."""
        empty_mask = torch.zeros(1, orig_h, orig_w, dtype=torch.float32)
        return (original_image, empty_mask)

    def composite(self, original_image, morphed_face, warp_mask, align_data):
        """Composite morphed face back into original image.

        Args:
            original_image: ComfyUI IMAGE tensor [1, H, W, 3] float32.
            morphed_face: ComfyUI IMAGE tensor [1, crop_h, crop_w, 3] float32.
            warp_mask: ComfyUI MASK tensor [1, crop_h, crop_w] float32.
            align_data: dict with transform_matrix, crop_box, original_size.

        Returns:
            Tuple of (composited_image IMAGE, face_region_mask MASK).
        """
        orig_h, orig_w = original_image.shape[1], original_image.shape[2]

        try:
            # Validate align_data has required keys
            required_keys = ("transform_matrix", "crop_box", "original_size")
            for key in required_keys:
                if key not in align_data:
                    return self._passthrough(original_image, orig_h, orig_w)

            transform_matrix = np.asarray(align_data["transform_matrix"], dtype=np.float64)
            crop_box = align_data["crop_box"]
            x1, y1, x2, y2 = crop_box

            # Validate crop_box is non-degenerate
            crop_h = y2 - y1
            crop_w = x2 - x1
            if crop_h <= 0 or crop_w <= 0:
                return self._passthrough(original_image, orig_h, orig_w)

            # Validate morphed_face dimensions match crop_box
            face_h, face_w = morphed_face.shape[1], morphed_face.shape[2]
            if face_h != crop_h or face_w != crop_w:
                return self._passthrough(original_image, orig_h, orig_w)

            # Validate transform_matrix is invertible
            transform = AffineTransform(matrix=transform_matrix)
            det = np.linalg.det(transform_matrix)
            if abs(det) < 1e-10:
                return self._passthrough(original_image, orig_h, orig_w)

            # Convert tensors to numpy float64
            orig_np = original_image[0].cpu().numpy().astype(np.float64)
            face_np = morphed_face[0].cpu().numpy().astype(np.float64)
            mask_np = warp_mask[0].cpu().numpy().astype(np.float64)

            # Create full-size canvases in aligned space
            # Expand crop region by margin for interpolation safety, clamped to bounds
            # We need to know the aligned space dimensions (same as original for our transforms)
            aligned_h, aligned_w = orig_h, orig_w

            ex1 = max(0, x1 - self.MARGIN_PX)
            ey1 = max(0, y1 - self.MARGIN_PX)
            ex2 = min(aligned_w, x2 + self.MARGIN_PX)
            ey2 = min(aligned_h, y2 + self.MARGIN_PX)

            # Place morphed face in expanded canvas
            face_canvas = np.zeros((ey2 - ey1, ex2 - ex1, 3), dtype=np.float64)
            mask_canvas = np.zeros((ey2 - ey1, ex2 - ex1), dtype=np.float64)

            # Offsets within expanded canvas
            off_x = x1 - ex1
            off_y = y1 - ey1
            face_canvas[off_y:off_y + crop_h, off_x:off_x + crop_w, :] = face_np
            mask_canvas[off_y:off_y + crop_h, off_x:off_x + crop_w] = mask_np

            # Place expanded canvas into full-size aligned-space canvas
            full_face_canvas = np.zeros((aligned_h, aligned_w, 3), dtype=np.float64)
            full_mask_canvas = np.zeros((aligned_h, aligned_w), dtype=np.float64)
            full_face_canvas[ey1:ey2, ex1:ex2, :] = face_canvas
            full_mask_canvas[ey1:ey2, ex1:ex2] = mask_canvas

            # Reverse warp: transform maps original->aligned, so passing it as
            # inverse_map means warp maps output(original) coords -> input(aligned) coords
            reversed_face = warp(
                full_face_canvas, inverse_map=transform,
                output_shape=(orig_h, orig_w),
                order=1, mode="constant", cval=0.0,
                preserve_range=True,
            )
            reversed_mask = warp(
                full_mask_canvas, inverse_map=transform,
                output_shape=(orig_h, orig_w),
                order=1, mode="constant", cval=0.0,
                preserve_range=True,
            )

            # Alpha blend: result = original * (1 - mask) + reversed_face * mask
            mask_3ch = reversed_mask[:, :, np.newaxis]  # (H, W, 1)
            result = orig_np * (1.0 - mask_3ch) + reversed_face * mask_3ch

            # Clamp to valid range
            result = np.clip(result, 0.0, 1.0)
            reversed_mask = np.clip(reversed_mask, 0.0, 1.0)

            # Convert to tensors
            result_tensor = torch.from_numpy(result.astype(np.float32)).unsqueeze(0)
            mask_tensor = torch.from_numpy(reversed_mask.astype(np.float32)).unsqueeze(0)

            return (result_tensor, mask_tensor)

        except Exception:
            return self._passthrough(original_image, orig_h, orig_w)
