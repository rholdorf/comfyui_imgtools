"""Tests for face model builder pipeline (utils/model_builder.py)."""

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_face(yaw=0.0, pitch=0.0, roll=0.0, has_pose=True):
    """Create a synthetic face dict like extract_landmarks() returns.

    landmarks_3d: (478, 3) with distinct left/right iris positions so
    normalize_landmarks_3d can compute a nonzero IPD.
    """
    rng = np.random.default_rng(42)
    lm3d = rng.random((478, 3)).astype(np.float64)
    # Ensure non-zero IPD: set iris centers apart
    lm3d[468] = [0.4, 0.5, 0.0]  # left iris
    lm3d[473] = [0.6, 0.5, 0.0]  # right iris

    if has_pose:
        pose = {
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "matrix": np.eye(4, dtype=np.float64),
        }
    else:
        pose = None

    return {
        "landmarks": rng.random((478, 2)).astype(np.float64),
        "landmarks_3d": lm3d,
        "pose": pose,
    }


# ---------------------------------------------------------------------------
# TestScanImages
# ---------------------------------------------------------------------------

class TestScanImages:
    """scan_images: directory scanning and filtering."""

    def test_returns_sorted_image_paths(self, tmp_path):
        """Returns sorted list of supported image paths."""
        from utils.model_builder import scan_images

        (tmp_path / "c.png").write_bytes(b"fake")
        (tmp_path / "a.jpg").write_bytes(b"fake")
        (tmp_path / "b.jpeg").write_bytes(b"fake")
        result = scan_images(str(tmp_path))
        assert [p.name for p in result] == ["a.jpg", "b.jpeg", "c.png"]

    def test_filters_by_extension(self, tmp_path):
        """Skips non-image files."""
        from utils.model_builder import scan_images

        (tmp_path / "photo.jpg").write_bytes(b"fake")
        (tmp_path / "readme.txt").write_bytes(b"fake")
        (tmp_path / "data.csv").write_bytes(b"fake")
        result = scan_images(str(tmp_path))
        assert len(result) == 1
        assert result[0].name == "photo.jpg"

    def test_raises_for_nonexistent_directory(self):
        """Raises ValueError for non-existent directory."""
        from utils.model_builder import scan_images

        with pytest.raises(ValueError, match="not found"):
            scan_images("/nonexistent/path/to/nowhere")

    def test_returns_empty_for_no_images(self, tmp_path):
        """Returns empty list if directory has no image files."""
        from utils.model_builder import scan_images

        (tmp_path / "notes.txt").write_bytes(b"fake")
        result = scan_images(str(tmp_path))
        assert result == []

    def test_supports_all_extensions(self, tmp_path):
        """Supports jpg, jpeg, png, webp, bmp."""
        from utils.model_builder import scan_images

        for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            (tmp_path / f"img{ext}").write_bytes(b"fake")
        result = scan_images(str(tmp_path))
        assert len(result) == 5


# ---------------------------------------------------------------------------
# TestProcessImage
# ---------------------------------------------------------------------------

class TestProcessImage:
    """process_image: per-image face detection and pose filtering."""

    @patch("utils.model_builder.extract_landmarks")
    @patch("utils.model_builder.mp")
    @patch("utils.model_builder.Image")
    def test_accepted_face(self, mock_pil, mock_mp, mock_extract, tmp_path):
        """Face with mild pose is accepted with correct weight."""
        from utils.model_builder import process_image

        face = _make_synthetic_face(yaw=10.0, pitch=5.0)
        mock_extract.return_value = [face]

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.__array__ = lambda s, dtype=None: np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pil.open.return_value = mock_img
        mock_mp.Image.return_value = MagicMock()

        mock_lm = MagicMock()
        mock_lm.detect.return_value = MagicMock()

        img_path = tmp_path / "face.jpg"
        img_path.write_bytes(b"fake")

        result = process_image(img_path, mock_lm)
        assert result["status"] == "ACCEPTED"
        expected_weight = math.cos(math.radians(10.0)) * math.cos(math.radians(5.0))
        assert abs(result["weight"] - expected_weight) < 1e-6
        assert result["normalized_3d"].shape == (478, 3)

    @patch("utils.model_builder.extract_landmarks")
    @patch("utils.model_builder.mp")
    @patch("utils.model_builder.Image")
    def test_rejected_extreme_yaw(self, mock_pil, mock_mp, mock_extract, tmp_path):
        """Face with |yaw| > 45 is rejected."""
        from utils.model_builder import process_image

        face = _make_synthetic_face(yaw=50.0, pitch=0.0)
        mock_extract.return_value = [face]

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.__array__ = lambda s, dtype=None: np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pil.open.return_value = mock_img
        mock_mp.Image.return_value = MagicMock()

        mock_lm = MagicMock()
        mock_lm.detect.return_value = MagicMock()

        img_path = tmp_path / "face.jpg"
        img_path.write_bytes(b"fake")

        result = process_image(img_path, mock_lm)
        assert result["status"] == "REJECTED"

    @patch("utils.model_builder.extract_landmarks")
    @patch("utils.model_builder.mp")
    @patch("utils.model_builder.Image")
    def test_rejected_extreme_pitch(self, mock_pil, mock_mp, mock_extract, tmp_path):
        """Face with |pitch| > 30 is rejected."""
        from utils.model_builder import process_image

        face = _make_synthetic_face(yaw=0.0, pitch=35.0)
        mock_extract.return_value = [face]

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.__array__ = lambda s, dtype=None: np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pil.open.return_value = mock_img
        mock_mp.Image.return_value = MagicMock()

        mock_lm = MagicMock()
        mock_lm.detect.return_value = MagicMock()

        img_path = tmp_path / "face.jpg"
        img_path.write_bytes(b"fake")

        result = process_image(img_path, mock_lm)
        assert result["status"] == "REJECTED"

    @patch("utils.model_builder.extract_landmarks")
    @patch("utils.model_builder.mp")
    @patch("utils.model_builder.Image")
    def test_no_face_detected(self, mock_pil, mock_mp, mock_extract, tmp_path):
        """Image with no face returns NO FACE status."""
        from utils.model_builder import process_image

        mock_extract.return_value = []

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.__array__ = lambda s, dtype=None: np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pil.open.return_value = mock_img
        mock_mp.Image.return_value = MagicMock()

        mock_lm = MagicMock()
        mock_lm.detect.return_value = MagicMock()

        img_path = tmp_path / "noface.jpg"
        img_path.write_bytes(b"fake")

        result = process_image(img_path, mock_lm)
        assert result["status"] == "NO FACE"

    @patch("utils.model_builder.extract_landmarks")
    @patch("utils.model_builder.mp")
    @patch("utils.model_builder.Image")
    def test_no_pose_fallback(self, mock_pil, mock_mp, mock_extract, tmp_path):
        """Face with pose=None falls back to weight=1.0, no frontalization."""
        from utils.model_builder import process_image

        face = _make_synthetic_face(has_pose=False)
        mock_extract.return_value = [face]

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.__array__ = lambda s, dtype=None: np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pil.open.return_value = mock_img
        mock_mp.Image.return_value = MagicMock()

        mock_lm = MagicMock()
        mock_lm.detect.return_value = MagicMock()

        img_path = tmp_path / "face.jpg"
        img_path.write_bytes(b"fake")

        result = process_image(img_path, mock_lm)
        assert result["status"] == "ACCEPTED"
        assert result["weight"] == 1.0
        assert result["normalized_3d"].shape == (478, 3)


# ---------------------------------------------------------------------------
# TestComputeWeightedAverage
# ---------------------------------------------------------------------------

class TestComputeWeightedAverage:
    """compute_weighted_average: weighted mean and stddev of landmarks."""

    def test_equal_weights_produce_mean(self):
        """Two faces with equal weight produce arithmetic mean."""
        from utils.model_builder import compute_weighted_average

        rng = np.random.default_rng(123)
        lm1 = rng.random((478, 3))
        lm2 = rng.random((478, 3))

        data = [
            {"normalized_3d": lm1, "weight": 1.0},
            {"normalized_3d": lm2, "weight": 1.0},
        ]
        mean, stddev = compute_weighted_average(data)
        np.testing.assert_allclose(mean, (lm1 + lm2) / 2, atol=1e-12)

    def test_unequal_weights_skew_result(self):
        """Higher weight skews result toward that face."""
        from utils.model_builder import compute_weighted_average

        lm1 = np.ones((478, 3)) * 0.0
        lm2 = np.ones((478, 3)) * 1.0

        data = [
            {"normalized_3d": lm1, "weight": 3.0},
            {"normalized_3d": lm2, "weight": 1.0},
        ]
        mean, stddev = compute_weighted_average(data)
        # Expected: (3*0 + 1*1) / 4 = 0.25
        np.testing.assert_allclose(mean, np.full((478, 3), 0.25), atol=1e-12)

    def test_returns_stddev_shape(self):
        """stddev has shape (478, 3)."""
        from utils.model_builder import compute_weighted_average

        rng = np.random.default_rng(456)
        data = [
            {"normalized_3d": rng.random((478, 3)), "weight": 1.0},
            {"normalized_3d": rng.random((478, 3)), "weight": 1.0},
        ]
        mean, stddev = compute_weighted_average(data)
        assert stddev.shape == (478, 3)

    def test_single_face_zero_stddev(self):
        """Single face produces zero stddev."""
        from utils.model_builder import compute_weighted_average

        lm = np.random.default_rng(42).random((478, 3))
        data = [{"normalized_3d": lm, "weight": 1.0}]
        mean, stddev = compute_weighted_average(data)
        np.testing.assert_array_equal(mean, lm)
        np.testing.assert_allclose(stddev, 0.0, atol=1e-15)


# ---------------------------------------------------------------------------
# TestBuildFaceModel
# ---------------------------------------------------------------------------

class TestBuildFaceModel:
    """build_face_model: end-to-end orchestration."""

    @patch("utils.model_builder.process_image")
    @patch("utils.model_builder.scan_images")
    def test_orchestrates_full_pipeline(self, mock_scan, mock_process, tmp_path):
        """build_face_model scans, processes, averages, and saves."""
        from utils.model_builder import build_face_model

        rng = np.random.default_rng(42)

        # Setup mock scan
        img1 = tmp_path / "img1.jpg"
        img2 = tmp_path / "img2.jpg"
        img1.write_bytes(b"fake")
        img2.write_bytes(b"fake")
        mock_scan.return_value = [img1, img2]

        # Setup mock process to return accepted faces
        lm1 = rng.random((478, 3))
        lm1[468] = [0.4, 0.5, 0.0]
        lm1[473] = [0.6, 0.5, 0.0]
        lm2 = rng.random((478, 3))
        lm2[468] = [0.4, 0.5, 0.0]
        lm2[473] = [0.6, 0.5, 0.0]

        mock_process.side_effect = [
            {
                "filename": "img1.jpg",
                "status": "ACCEPTED",
                "yaw": 5.0,
                "pitch": 3.0,
                "roll": 1.0,
                "confidence": 0.95,
                "weight": 0.99,
                "normalized_3d": lm1,
                "head_dims": {"width": 1.8, "height": 2.3, "depth": 1.0},
            },
            {
                "filename": "img2.jpg",
                "status": "ACCEPTED",
                "yaw": -10.0,
                "pitch": 2.0,
                "roll": -1.0,
                "confidence": 0.90,
                "weight": 0.97,
                "normalized_3d": lm2,
                "head_dims": {"width": 1.9, "height": 2.5, "depth": 1.1},
            },
        ]

        save_path = str(tmp_path / "model.facemodel.npz")
        model_dict, results, actual_path = build_face_model(
            str(tmp_path), save_path=save_path
        )

        assert len(results) == 2
        assert model_dict["canonical_landmarks"].shape == (478, 2)
        assert model_dict["landmark_stddev"].shape == (478, 3)
        assert "width" in model_dict["head_dimensions"]
        assert Path(actual_path).exists()

    @patch("utils.model_builder.process_image")
    @patch("utils.model_builder.scan_images")
    def test_raises_if_no_accepted(self, mock_scan, mock_process, tmp_path):
        """Raises ValueError if no images are accepted."""
        from utils.model_builder import build_face_model

        mock_scan.return_value = [tmp_path / "img.jpg"]
        mock_process.return_value = {
            "filename": "img.jpg",
            "status": "REJECTED",
            "yaw": 60.0,
            "pitch": 0.0,
            "roll": 0.0,
            "confidence": 0.9,
            "weight": 0.0,
            "normalized_3d": None,
            "head_dims": None,
        }

        with pytest.raises(ValueError, match="No accepted"):
            build_face_model(str(tmp_path))


# ---------------------------------------------------------------------------
# TestQualityReport
# ---------------------------------------------------------------------------

class TestQualityReport:
    """format_quality_report: text table formatting and sort order."""

    def _make_results(self):
        """Build a sample results list with all three statuses."""
        return [
            {"filename": "a.jpg", "status": "ACCEPTED", "yaw": 5.0, "pitch": 3.0,
             "roll": 1.0, "confidence": 0.95, "weight": 0.99},
            {"filename": "b.jpg", "status": "ACCEPTED", "yaw": -10.0, "pitch": 2.0,
             "roll": -1.0, "confidence": 0.90, "weight": 0.97},
            {"filename": "c.jpg", "status": "REJECTED", "yaw": 50.0, "pitch": 5.0,
             "roll": 2.0, "confidence": 0.85, "weight": 0.0},
            {"filename": "d.jpg", "status": "REJECTED", "yaw": 60.0, "pitch": 3.0,
             "roll": -2.0, "confidence": 0.80, "weight": 0.0},
            {"filename": "e.jpg", "status": "NO FACE", "yaw": 0.0, "pitch": 0.0,
             "roll": 0.0, "confidence": 0.0, "weight": 0.0},
        ]

    def test_accepted_sorted_by_weight_descending(self):
        """ACCEPTED images appear first, sorted by weight descending."""
        from comfyui_imgtools.face_model_builder import format_quality_report

        results = self._make_results()
        report = format_quality_report(results, "/tmp/model.npz", 45.0, 30.0)
        lines = report.strip().split("\n")
        # Skip header and separator (lines 0, 1)
        data_lines = [l for l in lines[2:] if l.strip() and "|" in l
                       and "Total:" not in l and "Thresholds:" not in l
                       and "Model saved" not in l]
        # First two data lines should be ACCEPTED
        assert "ACCEPTED" in data_lines[0]
        assert "ACCEPTED" in data_lines[1]
        # a.jpg (weight 0.99) before b.jpg (weight 0.97)
        assert "a.jpg" in data_lines[0]
        assert "b.jpg" in data_lines[1]

    def test_rejected_sorted_by_yaw_ascending(self):
        """REJECTED images sorted by |yaw| ascending after ACCEPTED."""
        from comfyui_imgtools.face_model_builder import format_quality_report

        results = self._make_results()
        report = format_quality_report(results, "/tmp/model.npz", 45.0, 30.0)
        lines = report.strip().split("\n")
        data_lines = [l for l in lines[2:] if "REJECTED" in l]
        # c.jpg (yaw=50) before d.jpg (yaw=60)
        assert "c.jpg" in data_lines[0]
        assert "d.jpg" in data_lines[1]

    def test_no_face_shows_na(self):
        """NO FACE rows show N/A for angle/confidence/weight columns."""
        from comfyui_imgtools.face_model_builder import format_quality_report

        results = self._make_results()
        report = format_quality_report(results, "/tmp/model.npz", 45.0, 30.0)
        lines = report.strip().split("\n")
        no_face_lines = [l for l in lines if "NO FACE" in l]
        assert len(no_face_lines) == 1
        assert "N/A" in no_face_lines[0]

    def test_summary_line_correct_counts(self):
        """Summary line contains correct total/accepted/rejected/no face counts."""
        from comfyui_imgtools.face_model_builder import format_quality_report

        results = self._make_results()
        report = format_quality_report(results, "/tmp/model.npz", 45.0, 30.0)
        assert "Total: 5" in report
        assert "Accepted: 2" in report
        assert "Rejected: 2" in report
        assert "No face: 1" in report

    def test_last_line_contains_save_path(self):
        """Last line shows the model save path."""
        from comfyui_imgtools.face_model_builder import format_quality_report

        results = self._make_results()
        report = format_quality_report(results, "/tmp/my_model.npz", 45.0, 30.0)
        last_line = report.strip().split("\n")[-1]
        assert "/tmp/my_model.npz" in last_line


# ---------------------------------------------------------------------------
# TestPreviewImage
# ---------------------------------------------------------------------------

class TestPreviewImage:
    """render_preview: 512x512 canvas with control points and contour."""

    def _make_canonical_2d(self):
        """Create synthetic (478, 2) canonical landmarks."""
        rng = np.random.default_rng(42)
        return rng.random((478, 2)).astype(np.float64)

    def test_returns_correct_shape_and_dtype(self):
        """Preview is (512, 512, 3) uint8."""
        from comfyui_imgtools.face_model_builder import render_preview
        from utils.morph_utils import MORPH_CONTROL_INDICES
        from utils.face_mask import FACE_OVAL_INDICES

        lm2d = self._make_canonical_2d()
        result = render_preview(lm2d, MORPH_CONTROL_INDICES, FACE_OVAL_INDICES, 5)
        assert result.shape == (512, 512, 3)
        assert result.dtype == np.uint8

    def test_header_has_white_pixels(self):
        """Header area (top 30 rows) contains white text pixels."""
        from comfyui_imgtools.face_model_builder import render_preview
        from utils.morph_utils import MORPH_CONTROL_INDICES
        from utils.face_mask import FACE_OVAL_INDICES

        lm2d = self._make_canonical_2d()
        result = render_preview(lm2d, MORPH_CONTROL_INDICES, FACE_OVAL_INDICES, 5)
        header = result[:30, :, :]
        assert np.any(header > 200), "Header area should have white text pixels"

    def test_green_pixels_exist(self):
        """Green pixels present (control points drawn)."""
        from comfyui_imgtools.face_model_builder import render_preview
        from utils.morph_utils import MORPH_CONTROL_INDICES
        from utils.face_mask import FACE_OVAL_INDICES

        lm2d = self._make_canonical_2d()
        result = render_preview(lm2d, MORPH_CONTROL_INDICES, FACE_OVAL_INDICES, 5)
        # Green: high G channel, low R and B
        green_mask = (result[:, :, 1] > 200) & (result[:, :, 0] < 50) & (result[:, :, 2] < 50)
        assert np.any(green_mask), "Should have green control point pixels"

    def test_white_contour_below_header(self):
        """White pixels exist below header area (contour lines)."""
        from comfyui_imgtools.face_model_builder import render_preview
        from utils.morph_utils import MORPH_CONTROL_INDICES
        from utils.face_mask import FACE_OVAL_INDICES

        lm2d = self._make_canonical_2d()
        result = render_preview(lm2d, MORPH_CONTROL_INDICES, FACE_OVAL_INDICES, 5)
        below_header = result[40:, :, :]
        white_mask = (below_header[:, :, 0] > 200) & (below_header[:, :, 1] > 200) & (below_header[:, :, 2] > 200)
        assert np.any(white_mask), "Should have white contour lines below header"


# ---------------------------------------------------------------------------
# TestNodeRegistration
# ---------------------------------------------------------------------------

class TestNodeRegistration:
    """FaceModelBuilder: ComfyUI node registration and interface."""

    def test_appears_in_node_class_mappings(self):
        """FaceModelBuilder registered in NODE_CLASS_MAPPINGS."""
        import comfyui_imgtools
        assert "FaceModelBuilder" in comfyui_imgtools.NODE_CLASS_MAPPINGS

    def test_input_types_has_directory(self):
        """INPUT_TYPES has 'directory' in required."""
        from comfyui_imgtools.face_model_builder import FaceModelBuilder
        inputs = FaceModelBuilder.INPUT_TYPES()
        assert "directory" in inputs["required"]

    def test_return_types(self):
        """RETURN_TYPES includes FACE_MODEL, STRING, IMAGE."""
        from comfyui_imgtools.face_model_builder import FaceModelBuilder
        assert FaceModelBuilder.RETURN_TYPES == ("FACE_MODEL", "STRING", "IMAGE")
