"""Tests for face model NPZ persistence (utils/model_io.py)."""

import numpy as np
import pytest


def _make_model_data():
    """Create valid synthetic model data for testing."""
    rng = np.random.default_rng(42)
    return {
        "canonical_landmarks": rng.random((478, 2)).astype(np.float64),
        "head_dimensions": {"width": 1.85, "height": 2.4, "depth": 1.1},
        "control_indices": np.array([10, 21, 54, 67, 93, 107, 276], dtype=np.int64),
        "landmark_stddev": rng.random((478, 2)).astype(np.float64),
    }


class TestRoundTrip:
    """Round-trip fidelity: save then load produces identical data."""

    def test_round_trip_arrays_identical(self, tmp_path):
        """Save and load must produce bit-identical arrays."""
        from utils.model_io import MODEL_VERSION, load_face_model, save_face_model

        path = tmp_path / "test.facemodel.npz"
        data = _make_model_data()

        save_face_model(
            path,
            canonical_landmarks=data["canonical_landmarks"],
            head_dimensions=data["head_dimensions"],
            control_indices=data["control_indices"],
            landmark_stddev=data["landmark_stddev"],
        )

        loaded = load_face_model(path)

        np.testing.assert_array_equal(
            loaded["canonical_landmarks"], data["canonical_landmarks"]
        )
        np.testing.assert_array_equal(
            loaded["control_indices"], data["control_indices"]
        )
        np.testing.assert_array_equal(
            loaded["landmark_stddev"], data["landmark_stddev"]
        )
        assert loaded["head_dimensions"] == data["head_dimensions"]
        assert loaded["version"] == MODEL_VERSION

    def test_round_trip_dtypes_preserved(self, tmp_path):
        """Loaded arrays must have the exact dtypes from save."""
        from utils.model_io import load_face_model, save_face_model

        path = tmp_path / "dtypes.facemodel.npz"
        data = _make_model_data()

        save_face_model(path, **data)
        loaded = load_face_model(path)

        assert loaded["canonical_landmarks"].dtype == np.float64
        assert loaded["control_indices"].dtype == np.int64
        assert loaded["landmark_stddev"].dtype == np.float64


class TestValidationErrors:
    """load_face_model raises clear errors for invalid files."""

    def test_file_not_found(self, tmp_path):
        """Nonexistent path raises FileNotFoundError."""
        from utils.model_io import load_face_model

        with pytest.raises(FileNotFoundError):
            load_face_model(tmp_path / "nope.facemodel.npz")

    def test_missing_fields_raises(self, tmp_path):
        """File with missing NPZ keys raises ValueError mentioning 'missing fields'."""
        from utils.model_io import load_face_model

        path = tmp_path / "bad.facemodel.npz"
        np.savez_compressed(path, version=np.array("1"))

        with pytest.raises(ValueError, match="missing fields"):
            load_face_model(path)

    def test_wrong_version_raises(self, tmp_path):
        """File with version != MODEL_VERSION raises ValueError."""
        from utils.model_io import load_face_model

        path = tmp_path / "old.facemodel.npz"
        np.savez_compressed(
            path,
            version=np.array("99"),
            canonical_landmarks=np.zeros((478, 2)),
            head_dimensions=np.zeros(3),
            control_indices=np.zeros(5, dtype=np.int64),
            landmark_stddev=np.zeros((478, 2)),
        )

        with pytest.raises(ValueError, match="Unsupported model version"):
            load_face_model(path)

    def test_wrong_shape_raises(self, tmp_path):
        """File with wrong array shape raises ValueError mentioning 'expected shape'."""
        from utils.model_io import load_face_model

        path = tmp_path / "shape.facemodel.npz"
        np.savez_compressed(
            path,
            version=np.array("1"),
            canonical_landmarks=np.zeros((100, 2)),  # wrong: should be (478, 2)
            head_dimensions=np.zeros(3),
            control_indices=np.zeros(5, dtype=np.int64),
            landmark_stddev=np.zeros((478, 2)),
        )

        with pytest.raises(ValueError, match="expected shape"):
            load_face_model(path)


class TestFileSize:
    """Saved file must be compact."""

    def test_file_size_under_15kb(self, tmp_path):
        """Standard 478-landmark model file should be under 15 KB."""
        from utils.model_io import save_face_model

        path = tmp_path / "size.facemodel.npz"
        data = _make_model_data()

        save_face_model(path, **data)

        size_kb = path.stat().st_size / 1024
        assert size_kb < 15, f"File too large: {size_kb:.1f} KB (expected < 15 KB)"
