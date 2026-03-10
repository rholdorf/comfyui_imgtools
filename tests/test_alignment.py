import numpy as np
import pytest

from utils.alignment import (
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
    apply_alignment,
    build_alignment_transform,
    compute_alignment_angle,
    compute_eye_centers,
    compute_padded_crop_box,
)


class TestComputeEyeCenters:
    def test_compute_eye_centers(self, mock_deterministic_landmarks):
        """Eye centers are the mean of their respective landmark indices."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        left_eye, right_eye = compute_eye_centers(landmarks)

        expected_left = landmarks[LEFT_EYE_INDICES].mean(axis=0)
        expected_right = landmarks[RIGHT_EYE_INDICES].mean(axis=0)

        np.testing.assert_allclose(left_eye, expected_left)
        np.testing.assert_allclose(right_eye, expected_right)

    def test_eye_centers_are_2d(self, mock_deterministic_landmarks):
        """Each eye center is a (x, y) pair."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        left_eye, right_eye = compute_eye_centers(landmarks)
        assert left_eye.shape == (2,)
        assert right_eye.shape == (2,)


class TestComputeAlignmentAngle:
    def test_alignment_angle_horizontal(self):
        """Eyes at the same y-coordinate yield angle ~0."""
        left_eye = np.array([100.0, 100.0])
        right_eye = np.array([200.0, 100.0])
        angle = compute_alignment_angle(left_eye, right_eye)
        assert abs(angle) < 1e-10

    def test_alignment_angle_tilted(self):
        """Known tilt: dy=10, dx=40 -> arctan2(10, 40) ~ 0.245 rad."""
        left_eye = np.array([108.0, 118.0])
        right_eye = np.array([148.0, 128.0])
        angle = compute_alignment_angle(left_eye, right_eye)
        expected = np.arctan2(10.0, 40.0)
        np.testing.assert_allclose(angle, expected, atol=1e-10)

    def test_alignment_angle_negative_tilt(self):
        """Right eye higher than left eye gives negative angle."""
        left_eye = np.array([100.0, 120.0])
        right_eye = np.array([200.0, 110.0])
        angle = compute_alignment_angle(left_eye, right_eye)
        assert angle < 0


class TestBuildAlignmentTransform:
    def test_zero_angle_no_rotation(self, mock_deterministic_landmarks):
        """Horizontal eyes produce a transform with ~0 rotation."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        transform, angle = build_alignment_transform(landmarks, 256, 256)
        assert abs(angle) < 1e-10

    def test_returns_tuple(self, mock_landmarks_tilted):
        """Returns (AffineTransform, float) tuple."""
        from skimage.transform import AffineTransform

        landmarks = mock_landmarks_tilted[0]["landmarks"]
        result = build_alignment_transform(landmarks, 256, 256)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], AffineTransform)
        assert isinstance(result[1], float)


class TestComputePaddedCropBox:
    def test_padded_crop_box_tight(self, mock_deterministic_landmarks):
        """padding=0 gives tight bounding box of (transformed) landmarks."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        transform, _ = build_alignment_transform(landmarks, 256, 256)
        box = compute_padded_crop_box(landmarks, transform, 0.0, 256, 256)

        assert len(box) == 4
        x1, y1, x2, y2 = box
        assert x1 >= 0
        assert y1 >= 0
        assert x2 <= 256
        assert y2 <= 256
        assert x2 > x1
        assert y2 > y1

    def test_padded_crop_box_expanded(self, mock_deterministic_landmarks):
        """padding=0.3 yields a larger box than padding=0."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        transform, _ = build_alignment_transform(landmarks, 256, 256)

        tight = compute_padded_crop_box(landmarks, transform, 0.0, 256, 256)
        padded = compute_padded_crop_box(landmarks, transform, 0.3, 256, 256)

        tight_area = (tight[2] - tight[0]) * (tight[3] - tight[1])
        padded_area = (padded[2] - padded[0]) * (padded[3] - padded[1])
        assert padded_area > tight_area

    def test_padded_crop_box_clamped(self):
        """Large padding near image edge clamps to image bounds."""
        # Place landmarks near top-left corner
        landmarks = np.zeros((478, 2), dtype=np.float64)
        landmarks[:, 0] = 10.0  # x near left edge
        landmarks[:, 1] = 10.0  # y near top edge

        from skimage.transform import AffineTransform

        identity = AffineTransform()
        box = compute_padded_crop_box(landmarks, identity, 1.0, 100, 100)
        x1, y1, x2, y2 = box
        assert x1 >= 0
        assert y1 >= 0
        assert x2 <= 100
        assert y2 <= 100


class TestApplyAlignment:
    def test_apply_alignment_shape(self, mock_deterministic_landmarks):
        """Output shape matches input shape."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        transform, _ = build_alignment_transform(landmarks, 256, 256)

        img = np.random.rand(256, 256, 3).astype(np.float64)
        result = apply_alignment(img, transform)
        assert result.shape == img.shape

    def test_apply_alignment_preserves_range(self, mock_deterministic_landmarks):
        """Output values stay in [0, 1] range for [0, 1] input."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        transform, _ = build_alignment_transform(landmarks, 256, 256)

        img = np.random.rand(256, 256, 3).astype(np.float64)
        result = apply_alignment(img, transform)
        assert result.min() >= 0.0
        assert result.max() <= 1.0
