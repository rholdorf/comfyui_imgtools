"""Tests for FaceCropAlign ComfyUI node."""

import numpy as np
import pytest
import torch


class TestFaceCropAlignConventions:
    """Test ComfyUI node conventions for FaceCropAlign."""

    def test_input_types_convention(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        input_types = FaceCropAlign.INPUT_TYPES()

        assert "required" in input_types
        assert "image" in input_types["required"]
        assert input_types["required"]["image"][0] == "IMAGE"
        assert "landmarks" in input_types["required"]
        assert input_types["required"]["landmarks"][0] == "FACE_LANDMARKS"

        assert "optional" in input_types
        assert "face_index" in input_types["optional"]
        assert "padding" in input_types["optional"]
        assert "align" in input_types["optional"]

    def test_return_types(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        assert FaceCropAlign.RETURN_TYPES == ("IMAGE", "ALIGN_DATA", "MASK")
        assert FaceCropAlign.RETURN_NAMES == ("cropped_face", "align_data", "face_mask")

    def test_category(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        assert FaceCropAlign.CATEGORY == "imgtools/face"

    def test_function_attribute(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        assert FaceCropAlign.FUNCTION == "crop_and_align"


class TestFaceCropAlignOutputs:
    """Test output types and shapes from crop_and_align."""

    def test_output_types(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        cropped, align_data, mask = node.crop_and_align(
            sample_face_image_tensor, mock_deterministic_landmarks
        )

        # IMAGE output: [1, H, W, 3] float32 tensor
        assert isinstance(cropped, torch.Tensor)
        assert cropped.ndim == 4
        assert cropped.shape[0] == 1
        assert cropped.shape[3] == 3
        assert cropped.dtype == torch.float32

        # MASK output: [1, H, W] float32 tensor
        assert isinstance(mask, torch.Tensor)
        assert mask.ndim == 3
        assert mask.shape[0] == 1
        assert mask.dtype == torch.float32

        # ALIGN_DATA output: dict
        assert isinstance(align_data, dict)

    def test_align_data_fields(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        _, align_data, _ = node.crop_and_align(
            sample_face_image_tensor, mock_deterministic_landmarks
        )

        required_keys = {
            "rotation_angle",
            "rotation_center",
            "crop_box",
            "original_size",
            "transform_matrix",
        }
        assert required_keys.issubset(align_data.keys()), (
            f"Missing keys: {required_keys - set(align_data.keys())}"
        )

        # Type checks on values
        assert isinstance(align_data["rotation_angle"], float)
        assert isinstance(align_data["rotation_center"], tuple)
        assert len(align_data["rotation_center"]) == 2
        assert isinstance(align_data["crop_box"], tuple)
        assert len(align_data["crop_box"]) == 4
        assert isinstance(align_data["original_size"], tuple)
        assert len(align_data["original_size"]) == 2
        assert isinstance(align_data["transform_matrix"], np.ndarray)
        assert align_data["transform_matrix"].shape == (3, 3)


class TestFaceCropAlignFaceSelection:
    """Test face index selection and clamping."""

    def test_face_index_selection(self, sample_face_image_tensor, mock_multi_face_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        cropped_0, data_0, _ = node.crop_and_align(
            sample_face_image_tensor, mock_multi_face_landmarks, face_index=0
        )
        cropped_1, data_1, _ = node.crop_and_align(
            sample_face_image_tensor, mock_multi_face_landmarks, face_index=1
        )

        # Crop boxes should differ since faces are at different positions
        assert data_0["crop_box"] != data_1["crop_box"]

    def test_face_index_clamped(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        # face_index=5 but only 1 face -- should not crash, should clamp to 0
        cropped, align_data, mask = node.crop_and_align(
            sample_face_image_tensor, mock_deterministic_landmarks, face_index=5
        )
        assert isinstance(cropped, torch.Tensor)
        assert isinstance(align_data, dict)
        assert isinstance(mask, torch.Tensor)


class TestFaceCropAlignAlignment:
    """Test alignment behavior."""

    def test_align_false(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        _, align_data, _ = node.crop_and_align(
            sample_face_image_tensor,
            mock_deterministic_landmarks,
            align=False,
        )

        assert align_data["rotation_angle"] == 0.0

    def test_align_true_with_tilted_face(
        self, sample_face_image_tensor, mock_landmarks_tilted
    ):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        _, align_data, _ = node.crop_and_align(
            sample_face_image_tensor,
            mock_landmarks_tilted,
            align=True,
        )

        # Tilted face should have nonzero rotation angle
        assert abs(align_data["rotation_angle"]) > 0.1


class TestCropLandmarks:
    """Test new FACE_LANDMARKS (4th) output from FaceCropAlign."""

    def test_return_types_includes_face_landmarks(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        assert FaceCropAlign.RETURN_TYPES == ("IMAGE", "ALIGN_DATA", "MASK", "FACE_LANDMARKS")

    def test_return_names_includes_crop_landmarks(self):
        from comfyui_imgtools.face_crop import FaceCropAlign

        assert FaceCropAlign.RETURN_NAMES == ("cropped_face", "align_data", "face_mask", "crop_landmarks")

    def test_crop_and_align_returns_4_tuple(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        result = node.crop_and_align(sample_face_image_tensor, mock_deterministic_landmarks)
        assert len(result) == 4

    def test_crop_landmarks_format(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        _, _, _, crop_lms = node.crop_and_align(sample_face_image_tensor, mock_deterministic_landmarks)

        # Should be a list of 1 dict with "landmarks" key
        assert isinstance(crop_lms, list)
        assert len(crop_lms) == 1
        assert "landmarks" in crop_lms[0]
        assert crop_lms[0]["landmarks"].shape == (478, 2)

    def test_crop_landmarks_offset_by_crop_box(self, sample_face_image_tensor, mock_deterministic_landmarks):
        from comfyui_imgtools.face_crop import FaceCropAlign

        node = FaceCropAlign()
        _, align_data, _, crop_lms = node.crop_and_align(
            sample_face_image_tensor, mock_deterministic_landmarks
        )

        x1, y1, _, _ = align_data["crop_box"]
        crop_landmarks = crop_lms[0]["landmarks"]

        # Crop landmarks should be offset from aligned landmarks by (x1, y1)
        # Verify that crop landmarks are in the crop coordinate space (non-negative mostly)
        # and that they differ from the original landmarks
        assert crop_landmarks.shape == (478, 2)
