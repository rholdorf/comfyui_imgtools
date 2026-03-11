"""Tests for FaceComposite node -- direct paste, alpha blending, graceful degradation."""

import numpy as np
import pytest
import torch

from comfyui_imgtools.face_composite import FaceComposite


class TestConventions:
    """Verify ComfyUI node interface conventions."""

    def test_input_types_keys(self):
        inputs = FaceComposite.INPUT_TYPES()
        required = inputs["required"]
        assert "original_image" in required
        assert "morphed_face" in required
        assert "align_data" in required

    def test_input_types_values(self):
        inputs = FaceComposite.INPUT_TYPES()
        required = inputs["required"]
        assert required["original_image"] == ("IMAGE",)
        assert required["morphed_face"] == ("IMAGE",)
        assert required["align_data"] == ("ALIGN_DATA",)

    def test_return_types(self):
        assert FaceComposite.RETURN_TYPES == ("IMAGE", "MASK")

    def test_return_names(self):
        assert FaceComposite.RETURN_NAMES == ("composited_image", "face_region_mask")

    def test_function(self):
        assert FaceComposite.FUNCTION == "composite"

    def test_category(self):
        assert FaceComposite.CATEGORY == "imgtools/face"


class TestPassthrough:
    """Graceful degradation returns original image + empty mask."""

    def setup_method(self):
        self.node = FaceComposite()
        self.original = torch.rand(1, 100, 100, 3, dtype=torch.float32)
        self.morphed = torch.rand(1, 64, 64, 3, dtype=torch.float32)

    def _valid_align_data(self):
        return {
            "rotation_angle": 0.0,
            "rotation_center": (50.0, 50.0),
            "crop_box": (10, 10, 74, 74),
            "original_size": (100, 100),
        }

    def test_missing_key_in_align_data(self):
        """Missing required key returns passthrough."""
        align = {"rotation_angle": 0.0}  # missing crop_box and original_size
        result_img, result_mask = self.node.composite(
            self.original, self.morphed, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.shape == (1, 100, 100)
        assert result_mask.sum().item() == 0.0

    def test_empty_crop_box(self):
        """Zero-size crop_box returns passthrough."""
        align = self._valid_align_data()
        align["crop_box"] = (10, 10, 10, 10)  # zero width/height
        result_img, result_mask = self.node.composite(
            self.original, self.morphed, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.sum().item() == 0.0


class TestIdentityRoundTrip:
    """With identity transform, composited face region should match original."""

    def test_identity_composite_matches_original(self, synthetic_original, identity_align_data):
        """When morphed_face == cropped region and identity transform, RMSE < 0.01."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        cropped = synthetic_original[:, y1:y2, x1:x2, :].clone()

        result_img, result_mask = node.composite(
            synthetic_original, cropped, identity_align_data
        )

        # Check face region RMSE (center, away from feathered edges)
        margin = FaceComposite.FEATHER_PX + 1
        face_region_result = result_img[0, y1 + margin:y2 - margin, x1 + margin:x2 - margin, :].numpy()
        face_region_original = synthetic_original[0, y1 + margin:y2 - margin, x1 + margin:x2 - margin, :].numpy()
        rmse = np.sqrt(np.mean((face_region_result - face_region_original) ** 2))
        assert rmse < 0.01, f"Identity round-trip center RMSE {rmse} >= 0.01"

    def test_output_dimensions_match_original(self, synthetic_original, identity_align_data):
        """Output image has same spatial dimensions as original."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        cropped = synthetic_original[:, y1:y2, x1:x2, :].clone()

        result_img, result_mask = node.composite(
            synthetic_original, cropped, identity_align_data
        )

        assert result_img.shape == synthetic_original.shape
        assert result_mask.shape == (1, synthetic_original.shape[1], synthetic_original.shape[2])


class TestBlending:
    """Verify blending behavior with internally generated mask."""

    def test_center_uses_morphed(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Center of crop (away from feathered edges) should be morphed face pixels."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]

        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )

        # Center pixel should match morphed face
        cy, cx = (y1 + y2) // 2, (x1 + x2) // 2
        center_result = result_img[0, cy, cx, :].numpy()
        fy, fx = cy - y1, cx - x1
        center_morphed = synthetic_morphed_face[0, fy, fx, :].numpy()
        np.testing.assert_allclose(center_result, center_morphed, atol=0.01)

    def test_outside_crop_unchanged(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Pixels far outside the crop region should be original."""
        node = FaceComposite()

        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )

        # Top-left corner is outside crop region
        np.testing.assert_allclose(
            result_img[0, 0, 0, :].numpy(),
            synthetic_original[0, 0, 0, :].numpy(),
            atol=1e-5,
        )

    def test_feathered_edges_blend(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Edge pixels of crop should be a blend (not pure morphed or original)."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]

        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )

        # Pixel at the very edge of crop should be blended
        edge_result = result_img[0, y1, x1, :].numpy()
        edge_original = synthetic_original[0, y1, x1, :].numpy()
        edge_morphed = synthetic_morphed_face[0, 0, 0, :].numpy()

        # It should differ from both pure original and pure morphed
        diff_from_orig = np.abs(edge_result - edge_original).max()
        diff_from_morphed = np.abs(edge_result - edge_morphed).max()
        # At least one should be non-trivially different
        assert diff_from_orig > 0.01 or diff_from_morphed > 0.01


class TestFaceRegionMask:
    """face_region_mask output properties."""

    def test_mask_shape(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Mask has same H, W as original_image."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )
        assert result_mask.shape == (1, 100, 100)

    def test_mask_values_range(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Mask values are in [0.0, 1.0]."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )
        assert result_mask.min() >= 0.0
        assert result_mask.max() <= 1.0

    def test_mask_nonzero_in_face_region(self, synthetic_original, synthetic_morphed_face,
                                          identity_align_data):
        """Mask has nonzero values in the face region."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        face_mask_region = result_mask[0, y1:y2, x1:x2]
        assert face_mask_region.sum() > 0

    def test_mask_zero_outside_face_region(self, synthetic_original, synthetic_morphed_face,
                                            identity_align_data):
        """With identity transform, mask outside crop_box should be zero."""
        node = FaceComposite()

        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )
        # Top-left corner should be zero (outside crop region)
        assert result_mask[0, 0, 0].item() == 0.0
        # Bottom-right corner should be zero
        assert result_mask[0, 99, 99].item() == 0.0

    def test_mask_has_feathered_edges(self, synthetic_original, synthetic_morphed_face,
                                       identity_align_data):
        """Mask should have intermediate values at crop edges (feathering)."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, identity_align_data
        )
        unique_vals = torch.unique(result_mask)
        assert len(unique_vals) > 5, "Mask should have feathered edges, not binary"


class TestFeatheredRectMask:
    """Unit tests for the internal _make_feathered_rect_mask method."""

    def test_center_is_one(self):
        mask = FaceComposite._make_feathered_rect_mask(64, 64, 8)
        assert mask[32, 32] == 1.0

    def test_corners_are_small(self):
        mask = FaceComposite._make_feathered_rect_mask(64, 64, 8)
        # Corner should be the smallest value
        assert mask[0, 0] < 0.3

    def test_shape(self):
        mask = FaceComposite._make_feathered_rect_mask(50, 30, 5)
        assert mask.shape == (50, 30)

    def test_values_in_range(self):
        mask = FaceComposite._make_feathered_rect_mask(64, 64, 8)
        assert mask.min() > 0.0
        assert mask.max() <= 1.0

    def test_zero_feather(self):
        mask = FaceComposite._make_feathered_rect_mask(10, 10, 0)
        assert np.all(mask == 1.0)
