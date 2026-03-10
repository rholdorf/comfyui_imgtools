"""Tests for morph utility functions."""

import numpy as np
import pytest


class TestControlPoints:
    """Test MORPH_CONTROL_INDICES curated landmark subset."""

    def test_control_indices_count(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        assert len(MORPH_CONTROL_INDICES) == 67

    def test_control_indices_unique_and_sorted(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        assert MORPH_CONTROL_INDICES == sorted(set(MORPH_CONTROL_INDICES))

    def test_control_indices_valid_range(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        assert all(0 <= idx <= 477 for idx in MORPH_CONTROL_INDICES)

    def test_control_indices_include_face_oval(self):
        from comfyui_imgtools.utils.face_mask import FACE_OVAL_INDICES
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        for idx in FACE_OVAL_INDICES:
            assert idx in MORPH_CONTROL_INDICES, f"FACE_OVAL index {idx} missing"

    def test_control_indices_include_eye_corners(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        eye_corners = [33, 133, 362, 263]
        for idx in eye_corners:
            assert idx in MORPH_CONTROL_INDICES, f"Eye corner {idx} missing"


class TestNormalization:
    """Test normalize_landmarks inter-eye distance scaling."""

    def test_normalize_landmarks_shape(self):
        from comfyui_imgtools.utils.morph_utils import normalize_landmarks

        landmarks = np.random.rand(67, 2) * 256
        eye_centers = (np.array([100.0, 100.0]), np.array([160.0, 100.0]))

        normalized, ied = normalize_landmarks(landmarks, eye_centers)
        assert normalized.shape == (67, 2)
        assert isinstance(ied, float)

    def test_normalize_landmarks_scales_by_ied(self):
        from comfyui_imgtools.utils.morph_utils import normalize_landmarks

        left_eye = np.array([100.0, 100.0])
        right_eye = np.array([160.0, 100.0])
        eye_centers = (left_eye, right_eye)
        ied_expected = 60.0  # distance between eyes

        center = (left_eye + right_eye) / 2.0  # (130, 100)
        # A point at (190, 100) is 60 pixels from center -> normalized to 1.0
        landmarks = np.array([[190.0, 100.0]])
        normalized, ied = normalize_landmarks(landmarks, eye_centers)

        assert abs(ied - ied_expected) < 1e-6
        assert abs(normalized[0, 0] - 1.0) < 1e-6
        assert abs(normalized[0, 1] - 0.0) < 1e-6

    def test_normalize_landmarks_returns_tuple(self):
        from comfyui_imgtools.utils.morph_utils import normalize_landmarks

        landmarks = np.random.rand(10, 2) * 256
        eye_centers = (np.array([100.0, 100.0]), np.array([160.0, 100.0]))

        result = normalize_landmarks(landmarks, eye_centers)
        assert len(result) == 2

    def test_normalize_landmarks_zero_ied_fallback(self):
        from comfyui_imgtools.utils.morph_utils import normalize_landmarks

        landmarks = np.array([[50.0, 50.0], [100.0, 100.0]])
        # Same position for both eyes -> zero IED
        eye_centers = (np.array([100.0, 100.0]), np.array([100.0, 100.0]))

        normalized, ied = normalize_landmarks(landmarks, eye_centers)
        # Should return original landmarks and ied=1.0 as fallback
        np.testing.assert_array_equal(normalized, landmarks)
        assert ied == 1.0


class TestBoundaryAnchors:
    """Test _get_boundary_anchors for TPS edge pinning."""

    def test_boundary_anchors_count(self):
        from comfyui_imgtools.utils.morph_utils import _get_boundary_anchors

        anchors = _get_boundary_anchors(256, 256)
        assert len(anchors) == 12

    def test_boundary_anchors_include_corners(self):
        from comfyui_imgtools.utils.morph_utils import _get_boundary_anchors

        anchors = _get_boundary_anchors(256, 256)
        anchors_list = [tuple(a) for a in anchors]

        assert (0.0, 0.0) in anchors_list
        assert (255.0, 0.0) in anchors_list
        assert (0.0, 255.0) in anchors_list
        assert (255.0, 255.0) in anchors_list

    def test_boundary_anchors_dtype(self):
        from comfyui_imgtools.utils.morph_utils import _get_boundary_anchors

        anchors = _get_boundary_anchors(256, 256)
        assert anchors.dtype == np.float64

    def test_boundary_anchors_shape(self):
        from comfyui_imgtools.utils.morph_utils import _get_boundary_anchors

        anchors = _get_boundary_anchors(512, 256)
        assert anchors.shape == (12, 2)
