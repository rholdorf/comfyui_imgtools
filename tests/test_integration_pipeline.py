"""E2E integration tests for the full model-based pipeline.

Pipeline: FaceModelBuilder -> FaceModelMorph -> FaceComposite

Validates that the full chain produces valid output tensors without
exceptions, and that error conditions degrade gracefully.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_process_result(rng):
    """Create a synthetic process_image result dict (ACCEPTED).

    Returns landmarks with distinct iris positions for nonzero IPD.
    """
    lm3d = rng.random((478, 3)).astype(np.float64)
    lm3d[468] = [0.4, 0.5, 0.0]  # left iris
    lm3d[473] = [0.6, 0.5, 0.0]  # right iris

    return {
        "filename": "img.jpg",
        "status": "ACCEPTED",
        "yaw": 5.0,
        "pitch": 3.0,
        "roll": 1.0,
        "confidence": 0.95,
        "weight": 0.99,
        "normalized_3d": lm3d,
        "head_dims": {"width": 1.8, "height": 2.3, "depth": 1.0},
    }


def _make_source_landmarks(canonical_2d):
    """Create source_landmarks list from canonical 2D landmarks.

    Builds a face dict compatible with FaceModelMorph input,
    using the canonical landmarks scaled to pixel space as the 2D landmarks,
    and synthetic 3D landmarks with valid iris positions for IPD.
    """
    rng = np.random.default_rng(77)

    # Scale canonical 2D to pixel coords in a 128x128 crop
    lm2d = canonical_2d.copy() * 40 + 64  # center in 128x128

    # Set eye landmarks for valid IED
    for idx in LEFT_EYE_INDICES:
        lm2d[idx] = [44.0, 50.0]
    for idx in RIGHT_EYE_INDICES:
        lm2d[idx] = [84.0, 50.0]

    # 3D landmarks with distinct iris positions
    lm3d = rng.random((478, 3)).astype(np.float64)
    lm3d[468] = [0.4, 0.5, 0.0]
    lm3d[473] = [0.6, 0.5, 0.0]

    return [{
        "landmarks": lm2d,
        "landmarks_3d": lm3d,
        "pose": {
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "matrix": np.eye(4, dtype=np.float64),
        },
    }]


# ---------------------------------------------------------------------------
# TestE2EPipeline
# ---------------------------------------------------------------------------

class TestE2EPipeline:
    """End-to-end integration tests for the full model-based pipeline."""

    @patch("comfyui_imgtools.face_model_builder.build_face_model")
    def test_full_pipeline_produces_valid_output(self, mock_build):
        """Chain FaceModelBuilder -> FaceModelMorph -> FaceComposite.

        Asserts: no exception, composited_image shape (1, 256, 256, 3),
        face_region_mask shape (1, 256, 256), all tensors float32.
        """
        from comfyui_imgtools.face_model_builder import FaceModelBuilder
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from comfyui_imgtools.face_composite import FaceComposite

        rng = np.random.default_rng(42)

        # --- Setup mock for build_face_model ---
        # Create a realistic model dict
        canonical_2d = rng.random((478, 2)).astype(np.float64) * 2 - 1
        canonical_2d[468] = [-0.5, 0.0]  # left iris
        canonical_2d[473] = [0.5, 0.0]   # right iris
        model_dict = {
            "version": 2,
            "canonical_landmarks": canonical_2d,
            "head_dimensions": {"width": 1.8, "height": 2.3, "depth": 1.0},
            "control_indices": np.array([10, 21, 54, 58, 67, 93, 103, 107,
                109, 127, 132, 136, 148, 149, 150, 152, 162, 172, 176,
                234, 251, 276, 284, 285, 288, 297, 323, 332, 336, 338,
                356, 361, 365, 377, 378, 379, 389, 397, 400, 454, 46, 55],
                dtype=np.int64),
            "landmark_stddev": np.zeros((478, 3), dtype=np.float64),
        }
        results = [{
            "filename": "img.jpg",
            "status": "ACCEPTED",
            "yaw": 5.0, "pitch": 3.0, "roll": 1.0,
            "confidence": 0.95, "weight": 0.99,
        }]
        mock_build.return_value = (model_dict, results, "/tmp/model.npz")

        # --- Step 1: FaceModelBuilder ---
        builder = FaceModelBuilder()
        face_model, quality_report, preview = builder.build_model(
            directory="/fake/dir"
        )

        # Validate model output
        assert isinstance(face_model, dict)
        assert len(face_model) > 0, "face_model should not be empty"
        assert "canonical_landmarks" in face_model
        assert face_model["canonical_landmarks"].shape == (478, 2)

        # --- Step 2: FaceModelMorph ---
        # Create synthetic source data
        original_image = torch.rand(1, 256, 256, 3, dtype=torch.float32)
        source_image = torch.rand(1, 128, 128, 3, dtype=torch.float32)
        source_landmarks = _make_source_landmarks(
            face_model["canonical_landmarks"]
        )
        source_align_data = {
            "crop_box": (64, 64, 192, 192),
            "original_size": (256, 256),
            "rotation_angle": 0.0,
            "rotation_center": (128, 128),
            "head_scale": 1.0,
        }

        morph_node = FaceModelMorph()
        morphed_face, warp_mask, align_data = morph_node.morph(
            source_image, face_model, source_landmarks,
            source_align_data, strength=0.5,
        )

        # Validate morph output
        assert morphed_face.shape == (1, 128, 128, 3)
        assert morphed_face.dtype == torch.float32
        assert warp_mask.shape == (1, 128, 128)
        assert isinstance(align_data, dict)

        # --- Step 3: FaceComposite ---
        composite_node = FaceComposite()
        composited_image, face_region_mask = composite_node.composite(
            original_image, morphed_face, align_data,
        )

        # Validate composite output
        assert composited_image.shape == (1, 256, 256, 3)
        assert composited_image.dtype == torch.float32
        assert face_region_mask.shape == (1, 256, 256)
        assert face_region_mask.dtype == torch.float32

    @patch("comfyui_imgtools.face_model_builder.build_face_model")
    def test_pipeline_with_error_model_graceful(self, mock_build):
        """Error model path degrades gracefully through the pipeline.

        FaceModelBuilder error -> empty model -> FaceModelMorph passthrough
        -> FaceComposite passthrough. No exception raised.
        """
        from comfyui_imgtools.face_model_builder import FaceModelBuilder
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from comfyui_imgtools.face_composite import FaceComposite

        # --- Step 1: FaceModelBuilder with error ---
        mock_build.side_effect = ValueError("No accepted images")
        builder = FaceModelBuilder()
        face_model, quality_report, preview = builder.build_model(
            directory="/nonexistent"
        )

        assert face_model == {}
        assert "ERROR" in quality_report

        # --- Step 2: FaceModelMorph with empty model ---
        source_image = torch.rand(1, 128, 128, 3, dtype=torch.float32)
        original_image = torch.rand(1, 256, 256, 3, dtype=torch.float32)

        rng = np.random.default_rng(42)
        lm2d = rng.random((478, 2)).astype(np.float64) * 60 + 2
        lm3d = rng.random((478, 3)).astype(np.float64)
        lm3d[468] = [0.4, 0.5, 0.0]
        lm3d[473] = [0.6, 0.5, 0.0]
        source_landmarks = [{
            "landmarks": lm2d,
            "landmarks_3d": lm3d,
            "pose": None,
        }]
        source_align_data = {
            "crop_box": (64, 64, 192, 192),
            "original_size": (256, 256),
            "rotation_angle": 0.0,
            "rotation_center": (128, 128),
            "head_scale": 1.0,
        }

        morph_node = FaceModelMorph()
        morphed_face, warp_mask, align_data = morph_node.morph(
            source_image, face_model, source_landmarks,
            source_align_data, strength=0.5,
        )

        # Should be passthrough (source_image unchanged)
        assert torch.equal(morphed_face, source_image)
        assert morphed_face.shape == source_image.shape

        # --- Step 3: FaceComposite with passthrough data ---
        composite_node = FaceComposite()
        composited_image, face_region_mask = composite_node.composite(
            original_image, morphed_face, align_data,
        )

        # Should not crash; output should have correct shapes
        assert composited_image.shape == (1, 256, 256, 3)
        assert composited_image.dtype == torch.float32
        assert face_region_mask.shape == (1, 256, 256)
        assert face_region_mask.dtype == torch.float32


# ---------------------------------------------------------------------------
# TestPoseAwarePipeline
# ---------------------------------------------------------------------------

class TestPoseAwarePipeline:
    """Integration tests verifying pose-aware vs fallback morph paths."""

    def _make_model_and_inputs(self):
        """Create a face model and source inputs for morph testing."""
        rng = np.random.default_rng(42)

        canonical_2d = rng.random((478, 2)).astype(np.float64) * 2 - 1
        canonical_2d[468] = [-0.5, 0.0]  # left iris
        canonical_2d[473] = [0.5, 0.0]   # right iris

        face_model = {
            "version": 2,
            "canonical_landmarks": canonical_2d,
            "head_dimensions": {"width": 1.8, "height": 2.3, "depth": 1.0},
            "control_indices": np.array([10, 21, 54, 58, 67, 93, 103, 107,
                109, 127, 132, 136, 148, 149, 150, 152, 162, 172, 176,
                234, 251, 276, 284, 285, 288, 297, 323, 332, 336, 338,
                356, 361, 365, 377, 378, 379, 389, 397, 400, 454, 46, 55],
                dtype=np.int64),
            "landmark_stddev": np.zeros((478, 3), dtype=np.float64),
        }

        source_image = torch.rand(1, 128, 128, 3, dtype=torch.float32)
        source_align_data = {
            "crop_box": (64, 64, 192, 192),
            "original_size": (256, 256),
            "rotation_angle": 0.0,
            "rotation_center": (128, 128),
            "head_scale": 1.0,
        }

        return face_model, source_image, source_align_data, canonical_2d

    def test_pose_aware_delta_path_exercised(self):
        """When pose data is present, _compute_pose_aware_delta is called."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        face_model, source_image, source_align_data, canonical_2d = (
            self._make_model_and_inputs()
        )
        source_landmarks = _make_source_landmarks(canonical_2d)

        morph_node = FaceModelMorph()

        with patch.object(
            FaceModelMorph, "_compute_pose_aware_delta",
            wraps=morph_node._compute_pose_aware_delta,
        ) as spy:
            morphed_face, warp_mask, align_data = morph_node.morph(
                source_image, face_model, source_landmarks,
                source_align_data, strength=0.5,
            )
            spy.assert_called_once()

        assert morphed_face.shape == (1, 128, 128, 3)
        assert warp_mask.shape == (1, 128, 128)

    def test_procrustes_fallback_when_no_pose(self):
        """When pose is None, _compute_fallback_delta is called."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        face_model, source_image, source_align_data, canonical_2d = (
            self._make_model_and_inputs()
        )
        source_landmarks = _make_source_landmarks(canonical_2d)
        # Set pose to None to trigger fallback path
        source_landmarks[0]["pose"] = None

        morph_node = FaceModelMorph()

        with patch.object(
            FaceModelMorph, "_compute_fallback_delta",
            wraps=morph_node._compute_fallback_delta,
        ) as spy:
            morphed_face, warp_mask, align_data = morph_node.morph(
                source_image, face_model, source_landmarks,
                source_align_data, strength=0.5,
            )
            spy.assert_called_once()

        assert morphed_face.shape == (1, 128, 128, 3)
        assert warp_mask.shape == (1, 128, 128)
