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


class TestMorphWarp:
    """Test compute_morph_warp TPS pipeline."""

    @pytest.fixture
    def deterministic_landmarks_pair(self):
        """Create a pair of source/target 478-point landmarks for warp tests."""
        from tests.conftest import _make_deterministic_landmarks

        source = _make_deterministic_landmarks(128.0, 128.0, spread=30.0)
        # Target has slightly different proportions (wider jaw)
        target = _make_deterministic_landmarks(128.0, 128.0, spread=35.0)
        return source, target

    def test_identity_warp(self, deterministic_landmarks_pair):
        """Identical source/target produces identity-like TPS transform."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, _ = deterministic_landmarks_pair
        tps = compute_morph_warp(source, source, strength=1.0, img_shape=(256, 256))

        assert tps is not None
        # Applying the TPS to source control points should return ~same points
        src_pts = source[MORPH_CONTROL_INDICES]
        mapped = tps(src_pts)
        np.testing.assert_allclose(mapped, src_pts, atol=1.0)

    def test_different_landmarks_produces_movement(self, deterministic_landmarks_pair):
        """Different source/target with strength=1.0 moves source points toward target."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert tps is not None
        src_pts = source[MORPH_CONTROL_INDICES]
        mapped = tps(src_pts)
        # Mapped points should differ from source
        diff = np.linalg.norm(mapped - src_pts, axis=1)
        assert diff.max() > 0.5, "TPS should move at least some points"

    def test_strength_zero_near_identity(self, deterministic_landmarks_pair):
        """Strength 0.0 should produce near-identity transform."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps = compute_morph_warp(source, target, strength=0.0, img_shape=(256, 256))

        assert tps is not None
        src_pts = source[MORPH_CONTROL_INDICES]
        mapped = tps(src_pts)
        np.testing.assert_allclose(mapped, src_pts, atol=1.0)

    def test_strength_one_full_movement(self, deterministic_landmarks_pair):
        """Strength 1.0 moves source control points fully toward target positions."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert tps is not None

    def test_strength_half_intermediate(self, deterministic_landmarks_pair):
        """Strength 0.5 produces intermediate movement between 0 and 1."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps_half = compute_morph_warp(source, target, strength=0.5, img_shape=(256, 256))
        tps_full = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert tps_half is not None
        assert tps_full is not None

        src_pts = source[MORPH_CONTROL_INDICES]
        mapped_half = tps_half(src_pts)
        mapped_full = tps_full(src_pts)

        # Half-strength movement should be less than full-strength
        diff_half = np.linalg.norm(mapped_half - src_pts, axis=1).mean()
        diff_full = np.linalg.norm(mapped_full - src_pts, axis=1).mean()
        assert diff_half < diff_full * 0.8, "Half strength should produce less movement"


class TestFeatheredMask:
    """Test generate_feathered_mask soft-edged mask generation."""

    @pytest.fixture
    def face_landmarks(self):
        """Create landmarks for mask generation centered in a 256x256 image."""
        from tests.conftest import _make_deterministic_landmarks

        return _make_deterministic_landmarks(128.0, 128.0, spread=40.0)

    def test_feathered_mask_shape_and_dtype(self, face_landmarks):
        from comfyui_imgtools.utils.morph_utils import generate_feathered_mask

        mask = generate_feathered_mask(face_landmarks, 256, 256)
        assert mask.shape == (256, 256)
        assert mask.dtype == np.float32

    def test_feathered_mask_value_range(self, face_landmarks):
        from comfyui_imgtools.utils.morph_utils import generate_feathered_mask

        mask = generate_feathered_mask(face_landmarks, 256, 256)
        assert mask.min() >= 0.0
        assert mask.max() <= 1.0

    def test_feathered_mask_has_soft_edges(self, face_landmarks):
        """Mask should have intermediate values (not all 0/1) from Gaussian blur."""
        from comfyui_imgtools.utils.morph_utils import generate_feathered_mask

        mask = generate_feathered_mask(face_landmarks, 256, 256)
        # Find values between 0.05 and 0.95 (soft edge region)
        intermediate = ((mask > 0.05) & (mask < 0.95)).sum()
        assert intermediate > 0, "Feathered mask should have intermediate values"

    def test_feathered_mask_center_near_one(self, face_landmarks):
        """Center region (inside face oval) should be close to 1.0."""
        from comfyui_imgtools.utils.morph_utils import generate_feathered_mask

        mask = generate_feathered_mask(face_landmarks, 256, 256)
        # The face center at (128, 128) should have high mask value
        center_val = mask[128, 128]
        assert center_val > 0.8, f"Center mask value {center_val} should be near 1.0"
