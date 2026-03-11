"""Tests for utils/pose_utils.py — pose extraction, frontalization, normalization."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation


def make_rotation_matrix(pitch=0.0, yaw=0.0, roll=0.0, scale=1.0):
    """Build a 4x4 transformation matrix from Euler angles (degrees) and uniform scale."""
    r = Rotation.from_euler("XYZ", [pitch, yaw, roll], degrees=True)
    rot3 = r.as_matrix() * scale
    mat = np.eye(4)
    mat[:3, :3] = rot3
    return mat


def make_synthetic_landmarks_3d(n=478):
    """Create synthetic 3D landmarks with known iris positions.

    Iris centers are placed at indices 468 (left) and 473 (right)
    with a known inter-pupillary distance.
    """
    rng = np.random.RandomState(99)
    lms = rng.randn(n, 3).astype(np.float64)
    # Set iris centers with known positions (IPD ~ 0.6 in x)
    lms[468] = np.array([0.3, 0.0, 0.0])   # left iris
    lms[473] = np.array([-0.3, 0.0, 0.0])  # right iris
    return lms


# ─── POSE-01: extract_pose_angles ───────────────────────────────────────────


class TestExtractPoseAngles:
    """Tests for extract_pose_angles (POSE-01)."""

    def test_identity_matrix_returns_zeros(self):
        from utils.pose_utils import extract_pose_angles

        result = extract_pose_angles(np.eye(4))
        assert abs(result["pitch"]) < 1e-6
        assert abs(result["yaw"]) < 1e-6
        assert abs(result["roll"]) < 1e-6

    def test_identity_returns_matrix_key(self):
        from utils.pose_utils import extract_pose_angles

        mat = np.eye(4)
        result = extract_pose_angles(mat)
        assert "matrix" in result
        np.testing.assert_array_equal(result["matrix"], mat)

    def test_known_30deg_yaw(self):
        from utils.pose_utils import extract_pose_angles

        mat = make_rotation_matrix(yaw=30.0)
        result = extract_pose_angles(mat)
        assert abs(result["yaw"] - 30.0) < 1.0

    def test_known_45deg_yaw(self):
        from utils.pose_utils import extract_pose_angles

        mat = make_rotation_matrix(yaw=45.0)
        result = extract_pose_angles(mat)
        assert abs(result["yaw"] - 45.0) < 1.0

    def test_known_20deg_pitch(self):
        from utils.pose_utils import extract_pose_angles

        mat = make_rotation_matrix(pitch=20.0)
        result = extract_pose_angles(mat)
        assert abs(result["pitch"] - 20.0) < 1.0

    def test_uniform_scale_same_angles(self):
        from utils.pose_utils import extract_pose_angles

        mat_noscale = make_rotation_matrix(yaw=30.0, pitch=15.0)
        mat_scaled = make_rotation_matrix(yaw=30.0, pitch=15.0, scale=2.0)
        r1 = extract_pose_angles(mat_noscale)
        r2 = extract_pose_angles(mat_scaled)
        assert abs(r1["pitch"] - r2["pitch"]) < 1e-4
        assert abs(r1["yaw"] - r2["yaw"]) < 1e-4
        assert abs(r1["roll"] - r2["roll"]) < 1e-4


# ─── POSE-02: frontalize_landmarks ──────────────────────────────────────────


class TestFrontalizeLandmarks:
    """Tests for frontalize_landmarks (POSE-02)."""

    def test_identity_rotation_unchanged(self):
        from utils.pose_utils import frontalize_landmarks

        lms = make_synthetic_landmarks_3d()
        mat = np.eye(4)
        result = frontalize_landmarks(lms, mat)
        np.testing.assert_allclose(result, lms, atol=1e-10)

    def test_30deg_yaw_frontalized(self):
        from utils.pose_utils import frontalize_landmarks

        lms_frontal = make_synthetic_landmarks_3d()
        mat = make_rotation_matrix(yaw=30.0)
        # Rotate landmarks as if the head was turned 30 deg
        r = Rotation.from_euler("XYZ", [0, 30, 0], degrees=True)
        centroid = lms_frontal.mean(axis=0)
        lms_rotated = r.apply(lms_frontal - centroid) + centroid
        # Frontalize should recover original
        result = frontalize_landmarks(lms_rotated, mat)
        # Error in IPD units
        ipd = np.linalg.norm(lms_frontal[468] - lms_frontal[473])
        mean_error = np.mean(np.linalg.norm(result - lms_frontal, axis=1)) / ipd
        assert mean_error < 0.03, f"Mean error {mean_error:.4f} exceeds 3% IPD"

    def test_45deg_yaw_frontalized(self):
        from utils.pose_utils import frontalize_landmarks

        lms_frontal = make_synthetic_landmarks_3d()
        mat = make_rotation_matrix(yaw=45.0)
        r = Rotation.from_euler("XYZ", [0, 45, 0], degrees=True)
        centroid = lms_frontal.mean(axis=0)
        lms_rotated = r.apply(lms_frontal - centroid) + centroid
        result = frontalize_landmarks(lms_rotated, mat)
        ipd = np.linalg.norm(lms_frontal[468] - lms_frontal[473])
        mean_error = np.mean(np.linalg.norm(result - lms_frontal, axis=1)) / ipd
        assert mean_error < 0.03, f"Mean error {mean_error:.4f} exceeds 3% IPD"

    def test_combined_pitch_yaw_frontalized(self):
        from utils.pose_utils import frontalize_landmarks

        lms_frontal = make_synthetic_landmarks_3d()
        mat = make_rotation_matrix(pitch=15.0, yaw=25.0)
        r = Rotation.from_euler("XYZ", [15, 25, 0], degrees=True)
        centroid = lms_frontal.mean(axis=0)
        lms_rotated = r.apply(lms_frontal - centroid) + centroid
        result = frontalize_landmarks(lms_rotated, mat)
        ipd = np.linalg.norm(lms_frontal[468] - lms_frontal[473])
        mean_error = np.mean(np.linalg.norm(result - lms_frontal, axis=1)) / ipd
        assert mean_error < 0.03, f"Mean error {mean_error:.4f} exceeds 3% IPD"


# ─── POSE-03: normalize_landmarks_3d ────────────────────────────────────────


class TestNormalizeLandmarks3D:
    """Tests for normalize_landmarks_3d (POSE-03)."""

    def test_output_ipd_equals_one(self):
        from utils.pose_utils import normalize_landmarks_3d

        lms = make_synthetic_landmarks_3d()
        normed, orig_ipd = normalize_landmarks_3d(lms)
        result_ipd = np.linalg.norm(normed[468] - normed[473])
        assert abs(result_ipd - 1.0) < 1e-10

    def test_scaled_landmarks_normalize_same(self):
        from utils.pose_utils import normalize_landmarks_3d

        lms = make_synthetic_landmarks_3d()
        lms_scaled = lms * 2.0
        normed1, _ = normalize_landmarks_3d(lms)
        normed2, _ = normalize_landmarks_3d(lms_scaled)
        np.testing.assert_allclose(normed1, normed2, atol=1e-10)

    def test_near_zero_ipd_returns_copy(self):
        from utils.pose_utils import normalize_landmarks_3d

        lms = make_synthetic_landmarks_3d()
        # Put both iris at the same point
        lms[468] = lms[473] = np.array([0.0, 0.0, 0.0])
        normed, ipd = normalize_landmarks_3d(lms)
        assert ipd == 1.0
        np.testing.assert_array_equal(normed, lms)

    def test_returns_original_ipd(self):
        from utils.pose_utils import normalize_landmarks_3d

        lms = make_synthetic_landmarks_3d()
        expected_ipd = np.linalg.norm(lms[468] - lms[473])
        _, orig_ipd = normalize_landmarks_3d(lms)
        assert abs(orig_ipd - expected_ipd) < 1e-10


# ─── Head Dimensions ────────────────────────────────────────────────────────


class TestComputeHeadDimensions:
    """Tests for compute_head_dimensions."""

    def test_returns_width_height_depth(self):
        from utils.pose_utils import compute_head_dimensions

        lms = make_synthetic_landmarks_3d()
        ipd = np.linalg.norm(lms[468] - lms[473])
        result = compute_head_dimensions(lms, ipd)
        assert "width" in result
        assert "height" in result
        assert "depth" in result
        assert all(v > 0 for v in result.values())

    def test_near_zero_ipd_uses_fallback(self):
        from utils.pose_utils import compute_head_dimensions

        lms = make_synthetic_landmarks_3d()
        result = compute_head_dimensions(lms, 0.0)
        # Should not raise, should use ipd=1.0 fallback
        assert all(v > 0 for v in result.values())

    def test_dimensions_in_ipd_units(self):
        from utils.pose_utils import compute_head_dimensions

        lms = make_synthetic_landmarks_3d()
        ipd = np.linalg.norm(lms[468] - lms[473])
        result = compute_head_dimensions(lms, ipd)
        # Width should be bounding-box x-range / ipd
        expected_width = (lms[:, 0].max() - lms[:, 0].min()) / ipd
        assert abs(result["width"] - expected_width) < 1e-10


# ─── Constants ───────────────────────────────────────────────────────────────


class TestConstants:
    """Verify exported constants."""

    def test_iris_center_constants(self):
        from utils.pose_utils import LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER

        assert LEFT_IRIS_CENTER == 468
        assert RIGHT_IRIS_CENTER == 473
