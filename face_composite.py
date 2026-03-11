"""FaceComposite ComfyUI node for compositing morphed face back into original image.

Pastes the morphed face as-is into the original image at the crop_box position
with feathered edge blending. No resize, no warp — morphed_face is used exactly
as received.
"""

import numpy as np
import torch


class FaceComposite:
    """Composite morphed face back into original image via direct paste."""

    FEATHER_PX = 8  # Feathering width in pixels at crop edges

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "morphed_face": ("IMAGE",),
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

    @staticmethod
    def _make_feathered_rect_mask(h, w, feather_px):
        """Create a rectangular mask with feathered edges.

        Center is 1.0, edges fade linearly to 0.0 over feather_px pixels.
        """
        mask = np.ones((h, w), dtype=np.float64)
        f = min(feather_px, h // 2, w // 2)
        if f <= 0:
            return mask
        for i in range(f):
            val = (i + 1) / (f + 1)
            mask[i, :] = np.minimum(mask[i, :], val)
            mask[h - 1 - i, :] = np.minimum(mask[h - 1 - i, :], val)
            mask[:, i] = np.minimum(mask[:, i], val)
            mask[:, w - 1 - i] = np.minimum(mask[:, w - 1 - i], val)
        return mask

    def composite(self, original_image, morphed_face, align_data):
        """Composite morphed face back into original image.

        Pastes morphed_face exactly as-is at the crop_box position with
        feathered edge blending. No resize, no warp.

        Args:
            original_image: ComfyUI IMAGE tensor [1, H, W, 3] float32.
            morphed_face: ComfyUI IMAGE tensor [1, face_h, face_w, 3] float32.
            align_data: dict with crop_box and original_size.

        Returns:
            Tuple of (composited_image IMAGE, face_region_mask MASK).
        """
        orig_h, orig_w = original_image.shape[1], original_image.shape[2]

        try:
            # Validate align_data has required keys
            required_keys = ("crop_box", "original_size")
            for key in required_keys:
                if key not in align_data:
                    return self._passthrough(original_image, orig_h, orig_w)

            crop_box = align_data["crop_box"]
            x1, y1, x2, y2 = crop_box

            # Validate crop_box is non-degenerate
            if y2 - y1 <= 0 or x2 - x1 <= 0:
                return self._passthrough(original_image, orig_h, orig_w)

            # Convert tensors to numpy float64
            orig_np = original_image[0].cpu().numpy().astype(np.float64)
            face_np = morphed_face[0].cpu().numpy().astype(np.float64)
            face_h, face_w = face_np.shape[:2]

            # Place at crop_box origin, using morphed_face dimensions as-is
            px1, py1 = x1, y1
            px2 = px1 + face_w
            py2 = py1 + face_h

            # Generate feathered rectangular mask matching morphed_face size
            mask_np = self._make_feathered_rect_mask(face_h, face_w, self.FEATHER_PX)

            # Compute overlap between placement rect and canvas bounds
            dst_y1 = max(0, py1)
            dst_x1 = max(0, px1)
            dst_y2 = min(orig_h, py2)
            dst_x2 = min(orig_w, px2)
            src_y1 = dst_y1 - py1
            src_x1 = dst_x1 - px1
            src_y2 = src_y1 + (dst_y2 - dst_y1)
            src_x2 = src_x1 + (dst_x2 - dst_x1)

            if dst_y2 <= dst_y1 or dst_x2 <= dst_x1:
                return self._passthrough(original_image, orig_h, orig_w)

            # Alpha blend directly into the original image
            result = orig_np.copy()
            full_mask = np.zeros((orig_h, orig_w), dtype=np.float64)

            region_face = face_np[src_y1:src_y2, src_x1:src_x2, :]
            region_mask = mask_np[src_y1:src_y2, src_x1:src_x2]
            mask_3ch = region_mask[:, :, np.newaxis]

            result[dst_y1:dst_y2, dst_x1:dst_x2, :] = (
                orig_np[dst_y1:dst_y2, dst_x1:dst_x2, :] * (1.0 - mask_3ch)
                + region_face * mask_3ch
            )
            full_mask[dst_y1:dst_y2, dst_x1:dst_x2] = region_mask

            # Clamp and convert to tensors
            result = np.clip(result, 0.0, 1.0)
            result_tensor = torch.from_numpy(result.astype(np.float32)).unsqueeze(0)
            mask_tensor = torch.from_numpy(full_mask.astype(np.float32)).unsqueeze(0)

            return (result_tensor, mask_tensor)

        except Exception:
            return self._passthrough(original_image, orig_h, orig_w)
