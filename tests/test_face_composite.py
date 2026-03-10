"""Tests for FaceComposite node -- reverse transform, alpha blending, graceful degradation."""

import numpy as np
import pytest
import torch
from skimage.transform import AffineTransform

from comfyui_imgtools.face_composite import FaceComposite


class TestConventions:
    """Verify ComfyUI node interface conventions."""

    def test_input_types_keys(self):
        inputs = FaceComposite.INPUT_TYPES()
        required = inputs["required"]
        assert "original_image" in required
        assert "morphed_face" in required
        assert "warp_mask" in required
        assert "align_data" in required

    def test_input_types_values(self):
        inputs = FaceComposite.INPUT_TYPES()
        required = inputs["required"]
        assert required["original_image"] == ("IMAGE",)
        assert required["morphed_face"] == ("IMAGE",)
        assert required["warp_mask"] == ("MASK",)
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
        self.mask = torch.ones(1, 64, 64, dtype=torch.float32)

    def _valid_align_data(self):
        t = AffineTransform()
        return {
            "rotation_angle": 0.0,
            "rotation_center": (50.0, 50.0),
            "crop_box": (10, 10, 74, 74),
            "original_size": (100, 100),
            "transform_matrix": t.params.copy(),
        }

    def test_missing_key_in_align_data(self):
        """Missing required key returns passthrough."""
        align = {"rotation_angle": 0.0}  # missing keys
        result_img, result_mask = self.node.composite(
            self.original, self.morphed, self.mask, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.shape == (1, 100, 100)
        assert result_mask.sum().item() == 0.0

    def test_singular_transform_matrix(self):
        """Singular (non-invertible) matrix returns passthrough."""
        align = self._valid_align_data()
        align["transform_matrix"] = np.zeros((3, 3))  # singular
        result_img, result_mask = self.node.composite(
            self.original, self.morphed, self.mask, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.sum().item() == 0.0

    def test_dimension_mismatch(self):
        """morphed_face dimensions != crop_box dimensions returns passthrough."""
        align = self._valid_align_data()
        wrong_size_morphed = torch.rand(1, 32, 32, 3, dtype=torch.float32)
        result_img, result_mask = self.node.composite(
            self.original, wrong_size_morphed, self.mask, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.sum().item() == 0.0

    def test_empty_crop_box(self):
        """Zero-size crop_box returns passthrough."""
        align = self._valid_align_data()
        align["crop_box"] = (10, 10, 10, 10)  # zero width/height
        result_img, result_mask = self.node.composite(
            self.original, self.morphed, self.mask, align
        )
        assert torch.equal(result_img, self.original)
        assert result_mask.sum().item() == 0.0


class TestIdentityRoundTrip:
    """With identity transform, composited face region should match original."""

    def test_identity_composite_matches_original(self, synthetic_original, identity_align_data):
        """When morphed_face == cropped region and identity transform, RMSE < 0.001."""
        node = FaceComposite()
        # Extract the crop region from original to use as morphed_face
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        cropped = synthetic_original[:, y1:y2, x1:x2, :].clone()
        # Full mask (ones)
        h, w = y2 - y1, x2 - x1
        mask = torch.ones(1, h, w, dtype=torch.float32)

        result_img, result_mask = node.composite(
            synthetic_original, cropped, mask, identity_align_data
        )

        # Check face region RMSE
        face_region_result = result_img[0, y1:y2, x1:x2, :].numpy()
        face_region_original = synthetic_original[0, y1:y2, x1:x2, :].numpy()
        rmse = np.sqrt(np.mean((face_region_result - face_region_original) ** 2))
        assert rmse < 0.001, f"Identity round-trip RMSE {rmse} >= 0.001"

    def test_output_dimensions_match_original(self, synthetic_original, identity_align_data):
        """Output image has same spatial dimensions as original."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        cropped = synthetic_original[:, y1:y2, x1:x2, :].clone()
        h, w = y2 - y1, x2 - x1
        mask = torch.ones(1, h, w, dtype=torch.float32)

        result_img, result_mask = node.composite(
            synthetic_original, cropped, mask, identity_align_data
        )

        assert result_img.shape == synthetic_original.shape
        assert result_mask.shape == (1, synthetic_original.shape[1], synthetic_original.shape[2])


class TestRotatedRoundTrip:
    """With rotated transform, composited face should be close to original."""

    def test_rotated_composite_close_to_original(self, synthetic_original, rotated_align_data):
        """Rotated transform round-trip RMSE < 0.25 (double interpolation loss)."""
        node = FaceComposite()
        x1, y1, x2, y2 = rotated_align_data["crop_box"]
        h, w = y2 - y1, x2 - x1

        # Simulate a forward-then-reverse by using the crop region as morphed face
        # (strength=0 morph equivalent)
        from skimage.transform import warp as sk_warp

        img_np = synthetic_original[0].numpy().astype(np.float64)
        transform = AffineTransform(matrix=rotated_align_data["transform_matrix"])
        aligned = sk_warp(
            img_np, inverse_map=transform.inverse,
            output_shape=img_np.shape[:2], order=1,
            mode="constant", cval=0.0, preserve_range=True,
        )
        cropped = aligned[y1:y2, x1:x2].astype(np.float32)
        morphed = torch.from_numpy(cropped).unsqueeze(0)
        mask = torch.ones(1, h, w, dtype=torch.float32)

        result_img, _ = node.composite(
            synthetic_original, morphed, mask, rotated_align_data
        )

        # Check face region RMSE -- allows for double interpolation loss
        face_result = result_img[0, y1:y2, x1:x2, :].numpy()
        face_orig = synthetic_original[0, y1:y2, x1:x2, :].numpy()
        rmse = np.sqrt(np.mean((face_result - face_orig) ** 2))
        assert rmse < 0.25, f"Rotated round-trip RMSE {rmse} >= 0.25"


class TestAlphaBlending:
    """Alpha blend correctness with warp_mask."""

    def test_mask_one_uses_morphed(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Where mask == 1.0, result should be morphed face pixels."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        h, w = y2 - y1, x2 - x1
        mask = torch.ones(1, h, w, dtype=torch.float32)

        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, mask, identity_align_data
        )

        face_result = result_img[0, y1:y2, x1:x2, :].numpy()
        morphed_val = synthetic_morphed_face[0].numpy()
        # With identity transform and full mask, face region should be morphed face
        rmse = np.sqrt(np.mean((face_result - morphed_val) ** 2))
        assert rmse < 0.001, f"Mask=1 region RMSE {rmse}: should match morphed face"

    def test_mask_zero_uses_original(self, synthetic_original, synthetic_morphed_face, identity_align_data):
        """Where mask == 0.0, result should be original image pixels."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        h, w = y2 - y1, x2 - x1
        mask = torch.zeros(1, h, w, dtype=torch.float32)

        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, mask, identity_align_data
        )

        # Entire image should be original since mask is zero everywhere
        assert torch.allclose(result_img, synthetic_original, atol=1e-5)

    def test_feathered_mask_blend(self, synthetic_original, synthetic_morphed_face,
                                  synthetic_warp_mask, identity_align_data):
        """Feathered mask produces weighted blend in transition region."""
        node = FaceComposite()
        result_img, _ = node.composite(
            synthetic_original, synthetic_morphed_face, synthetic_warp_mask, identity_align_data
        )

        # Result should differ from both original and full-morphed in the feathered region
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        face_result = result_img[0, y1:y2, x1:x2, :].numpy()
        face_orig = synthetic_original[0, y1:y2, x1:x2, :].numpy()
        morphed_val = synthetic_morphed_face[0].numpy()

        # At edges (mask < 1), result should differ from morphed
        edge_result = face_result[0, :, :]  # top row (mask ~0.2)
        edge_morphed = morphed_val[0, :, :]
        assert not np.allclose(edge_result, edge_morphed, atol=0.01)

        # Center (mask == 1) should match morphed
        center_result = face_result[32, 32, :]
        center_morphed = morphed_val[32, 32, :]
        np.testing.assert_allclose(center_result, center_morphed, atol=0.01)


class TestFaceRegionMask:
    """face_region_mask output is reverse-transformed warp_mask in original space."""

    def test_mask_shape(self, synthetic_original, synthetic_morphed_face,
                        synthetic_warp_mask, identity_align_data):
        """Mask has same H, W as original_image."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, synthetic_warp_mask, identity_align_data
        )
        assert result_mask.shape == (1, 100, 100)

    def test_mask_values_range(self, synthetic_original, synthetic_morphed_face,
                               synthetic_warp_mask, identity_align_data):
        """Mask values are in [0.0, 1.0]."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, synthetic_warp_mask, identity_align_data
        )
        assert result_mask.min() >= 0.0
        assert result_mask.max() <= 1.0

    def test_mask_nonzero_in_face_region(self, synthetic_original, synthetic_morphed_face,
                                          synthetic_warp_mask, identity_align_data):
        """Mask has nonzero values in the face region."""
        node = FaceComposite()
        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face, synthetic_warp_mask, identity_align_data
        )
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        face_mask_region = result_mask[0, y1:y2, x1:x2]
        assert face_mask_region.sum() > 0

    def test_mask_zero_outside_face_region(self, synthetic_original, synthetic_morphed_face,
                                            identity_align_data):
        """With identity transform and ones mask, mask outside crop_box should be zero."""
        node = FaceComposite()
        x1, y1, x2, y2 = identity_align_data["crop_box"]
        h, w = y2 - y1, x2 - x1
        mask = torch.ones(1, h, w, dtype=torch.float32)

        _, result_mask = node.composite(
            synthetic_original, synthetic_morphed_face[:, :h, :w, :], mask, identity_align_data
        )
        # Top-left corner should be zero (outside crop region)
        assert result_mask[0, 0, 0].item() == 0.0
        # Bottom-right corner should be zero
        assert result_mask[0, 99, 99].item() == 0.0
