"""Tests for LoadFaceModel ComfyUI node."""

import numpy as np
import pytest

from comfyui_imgtools.face_model_loader import LoadFaceModel
from comfyui_imgtools.utils.model_io import save_face_model


def _make_test_model_data():
    """Create valid face model data for test fixtures."""
    return {
        "canonical_landmarks": np.random.rand(478, 2).astype(np.float64),
        "head_dimensions": {"width": 14.5, "height": 20.0, "depth": 18.3},
        "control_indices": np.array([0, 1, 10, 50, 100], dtype=np.int64),
        "landmark_stddev": np.random.rand(478, 3).astype(np.float64),
    }


class TestLoadFaceModel:
    def test_load_valid_model(self, tmp_path):
        """Load a valid .facemodel.npz and verify all expected keys."""
        model_data = _make_test_model_data()
        model_path = tmp_path / "test.facemodel.npz"
        save_face_model(model_path, **model_data)

        node = LoadFaceModel()
        result = node.load_model(file_path=str(model_path))

        assert isinstance(result, tuple)
        assert len(result) == 1
        model = result[0]
        assert isinstance(model, dict)
        for key in ("version", "canonical_landmarks", "head_dimensions",
                     "control_indices", "landmark_stddev"):
            assert key in model, f"Missing key: {key}"

    def test_round_trip_fidelity(self, tmp_path):
        """Saved and loaded model data must match."""
        model_data = _make_test_model_data()
        model_path = tmp_path / "roundtrip.facemodel.npz"
        save_face_model(model_path, **model_data)

        node = LoadFaceModel()
        (model,) = node.load_model(file_path=str(model_path))

        np.testing.assert_allclose(
            model["canonical_landmarks"], model_data["canonical_landmarks"]
        )
        assert model["head_dimensions"] == model_data["head_dimensions"]

    def test_empty_path(self):
        """Empty file path returns ({},) tuple."""
        node = LoadFaceModel()
        result = node.load_model(file_path="")
        assert result == ({},)

    def test_missing_file(self):
        """Non-existent path returns ({},) tuple (no exception raised)."""
        node = LoadFaceModel()
        result = node.load_model(file_path="/nonexistent/path.facemodel.npz")
        assert result == ({},)

    def test_invalid_file(self, tmp_path):
        """File with invalid content returns ({},) tuple."""
        bad_file = tmp_path / "bad.facemodel.npz"
        bad_file.write_text("not a valid npz file")

        node = LoadFaceModel()
        result = node.load_model(file_path=str(bad_file))
        assert result == ({},)

    def test_node_metadata(self):
        """Verify ComfyUI node metadata."""
        input_types = LoadFaceModel.INPUT_TYPES()
        assert "required" in input_types
        assert "file_path" in input_types["required"]
        assert input_types["required"]["file_path"][0] == "STRING"

        assert LoadFaceModel.RETURN_TYPES == ("FACE_MODEL",)
        assert LoadFaceModel.FUNCTION == "load_model"
        assert LoadFaceModel.CATEGORY == "imgtools/face"
