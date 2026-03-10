import numpy as np
import pytest

from utils.face_mask import FACE_OVAL_INDICES, generate_face_mask


class TestFaceOvalIndices:
    def test_face_oval_indices_count(self):
        """FACE_OVAL_INDICES has exactly 36 entries."""
        assert len(FACE_OVAL_INDICES) == 36

    def test_face_oval_indices_in_range(self):
        """All indices are valid for a 478-landmark array."""
        for idx in FACE_OVAL_INDICES:
            assert 0 <= idx < 478


class TestGenerateFaceMask:
    def test_mask_shape(self, mock_deterministic_landmarks):
        """Output shape is (H, W), dtype float32."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        mask = generate_face_mask(landmarks, 256, 256)
        assert mask.shape == (256, 256)
        assert mask.dtype == np.float32

    def test_mask_values_binary(self, mock_deterministic_landmarks):
        """All values are either 0.0 or 1.0."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        mask = generate_face_mask(landmarks, 256, 256)
        unique_values = np.unique(mask)
        for v in unique_values:
            assert v in (0.0, 1.0)

    def test_mask_has_nonzero_region(self, mock_deterministic_landmarks):
        """Mask has some 1.0 pixels (face region is not empty)."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        mask = generate_face_mask(landmarks, 256, 256)
        assert mask.sum() > 0

    def test_mask_different_dimensions(self, mock_deterministic_landmarks):
        """Mask shape matches the given dimensions, not the landmark range."""
        landmarks = mock_deterministic_landmarks[0]["landmarks"]
        mask = generate_face_mask(landmarks, 512, 384)
        assert mask.shape == (512, 384)
