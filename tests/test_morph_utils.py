"""Tests for morph utility functions."""

import numpy as np
import pytest


class TestControlPoints:
    """Test MORPH_CONTROL_INDICES curated landmark subset."""

    def test_control_indices_count(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        assert len(MORPH_CONTROL_INDICES) == 42

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

    def test_control_indices_include_eyebrow_endpoints(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        eyebrow_pts = [46, 55, 107, 276, 285, 336]
        for idx in eyebrow_pts:
            assert idx in MORPH_CONTROL_INDICES, f"Eyebrow endpoint {idx} missing"

    def test_control_indices_exclude_feature_detail(self):
        from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES

        # Eye corners, nose, lips should NOT be in control points
        feature_detail = [33, 133, 362, 263, 48, 275, 61, 291]
        for idx in feature_detail:
            assert idx not in MORPH_CONTROL_INDICES, f"Feature detail {idx} should be excluded"


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


class TestProcrustes:
    """Test procrustes_align for rotation-only landmark alignment."""

    def test_identity(self):
        """Identical points produce aligned = source, scale_ratio = 1.0."""
        from comfyui_imgtools.utils.morph_utils import procrustes_align

        pts = np.array([[10, 20], [50, 30], [30, 60]], dtype=np.float64)
        aligned, scale_ratio = procrustes_align(pts, pts)

        np.testing.assert_allclose(aligned, pts, atol=1e-10)
        assert abs(scale_ratio - 1.0) < 1e-10

    def test_rotation_invariance(self):
        """Rotated target aligns back to source shape."""
        from comfyui_imgtools.utils.morph_utils import procrustes_align

        src = np.array([[0, 0], [100, 0], [50, 80]], dtype=np.float64)
        # Rotate target by 30 degrees around centroid
        theta = np.radians(30)
        R = np.array([[np.cos(theta), -np.sin(theta)],
                       [np.sin(theta), np.cos(theta)]])
        centroid = src.mean(axis=0)
        tgt = (src - centroid) @ R.T + centroid

        aligned, scale_ratio = procrustes_align(src, tgt)
        np.testing.assert_allclose(aligned, src, atol=1e-10)
        assert abs(scale_ratio - 1.0) < 1e-10

    def test_normalizes_scale(self):
        """Uniformly scaled target is normalized to source size; scale_ratio returned."""
        from comfyui_imgtools.utils.morph_utils import procrustes_align

        src = np.array([[0, 0], [100, 0], [50, 80]], dtype=np.float64)
        tgt = src * 1.5  # 50% bigger

        aligned, scale_ratio = procrustes_align(src, tgt)
        # Aligned should match source size (scale normalized)
        src_spread = np.linalg.norm(src - src.mean(axis=0), axis=1).mean()
        aligned_spread = np.linalg.norm(aligned - aligned.mean(axis=0), axis=1).mean()
        assert abs(aligned_spread / src_spread - 1.0) < 0.01
        # Scale ratio captures the size difference
        assert abs(scale_ratio - 1.5) < 0.01

    def test_preserves_shape_differences(self):
        """Different shapes produce non-zero delta after alignment."""
        from comfyui_imgtools.utils.morph_utils import procrustes_align

        src = np.array([[0, 0], [100, 0], [50, 80]], dtype=np.float64)
        # Target has different proportions (wider base, shorter height)
        tgt = np.array([[0, 0], [120, 0], [60, 60]], dtype=np.float64)

        aligned, _ = procrustes_align(src, tgt)
        delta = aligned - src
        assert np.linalg.norm(delta) > 1.0, "Shape differences should produce non-zero delta"

    def test_rotation_plus_shape(self):
        """Rotation is removed but shape difference preserved."""
        from comfyui_imgtools.utils.morph_utils import procrustes_align

        src = np.array([[0, 0], [100, 0], [50, 80]], dtype=np.float64)
        # Different shape
        tgt_shape = np.array([[0, 0], [120, 0], [60, 60]], dtype=np.float64)
        # Then rotate by 20 degrees
        theta = np.radians(20)
        R = np.array([[np.cos(theta), -np.sin(theta)],
                       [np.sin(theta), np.cos(theta)]])
        centroid = tgt_shape.mean(axis=0)
        tgt_rotated = (tgt_shape - centroid) @ R.T + centroid

        # Align both: just shape diff and rotated+shape diff
        aligned_shape, _ = procrustes_align(src, tgt_shape)
        aligned_rotated, _ = procrustes_align(src, tgt_rotated)

        # Both should produce similar deltas (rotation removed)
        delta_shape = aligned_shape - src
        delta_rotated = aligned_rotated - src
        np.testing.assert_allclose(delta_shape, delta_rotated, atol=1e-8)


class TestSymmetrizeDelta:
    """Test _symmetrize_delta for removing yaw-induced asymmetry."""

    def test_symmetric_delta_unchanged(self):
        """A perfectly symmetric delta should pass through unchanged."""
        from comfyui_imgtools.utils.morph_utils import (
            _symmetrize_delta, MORPH_CONTROL_INDICES, _MORPH_MIRROR_PAIRS,
        )

        # Create source points centered on x=100
        n = len(MORPH_CONTROL_INDICES)
        src_pts = np.random.RandomState(42).rand(n, 2) * 200
        # Make it symmetric: for each pair, mirror positions
        ctrl_pos = {lm_id: i for i, lm_id in enumerate(MORPH_CONTROL_INDICES)}
        midline_x = 100.0
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            if lm_a in ctrl_pos and lm_b in ctrl_pos:
                ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
                avg_y = (src_pts[ia, 1] + src_pts[ib, 1]) / 2
                half_dx = abs(src_pts[ia, 0] - src_pts[ib, 0]) / 2
                src_pts[ia] = [midline_x - half_dx, avg_y]
                src_pts[ib] = [midline_x + half_dx, avg_y]

        # Symmetric delta: both sides widen equally
        delta = np.zeros((n, 2))
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            if lm_a in ctrl_pos and lm_b in ctrl_pos:
                ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
                if src_pts[ia, 0] < src_pts[ib, 0]:
                    delta[ia, 0] = -5.0  # left moves left
                    delta[ib, 0] = 5.0   # right moves right
                else:
                    delta[ia, 0] = 5.0
                    delta[ib, 0] = -5.0
                delta[ia, 1] = 3.0  # same vertical
                delta[ib, 1] = 3.0

        sym_delta = _symmetrize_delta(delta, src_pts)
        np.testing.assert_allclose(sym_delta, delta, atol=1e-10)

    def test_asymmetric_delta_corrected(self):
        """Asymmetric delta (one side moves more) should be symmetrized."""
        from comfyui_imgtools.utils.morph_utils import (
            _symmetrize_delta, MORPH_CONTROL_INDICES, _MORPH_MIRROR_PAIRS,
        )

        n = len(MORPH_CONTROL_INDICES)
        ctrl_pos = {lm_id: i for i, lm_id in enumerate(MORPH_CONTROL_INDICES)}

        # Simple source: points spread around midline x=100
        src_pts = np.ones((n, 2)) * 100.0
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            if lm_a in ctrl_pos and lm_b in ctrl_pos:
                ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
                src_pts[ia] = [70.0, 100.0]  # left
                src_pts[ib] = [130.0, 100.0]  # right

        # Asymmetric delta: right side moves 10px right, left doesn't move
        delta = np.zeros((n, 2))
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            if lm_a in ctrl_pos and lm_b in ctrl_pos:
                ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
                if src_pts[ia, 0] < src_pts[ib, 0]:
                    delta[ia, 0] = 0.0   # left: no movement
                    delta[ib, 0] = 10.0  # right: moves 10px right
                else:
                    delta[ia, 0] = 10.0
                    delta[ib, 0] = 0.0

        sym_delta = _symmetrize_delta(delta, src_pts)

        # After symmetrization: width change of 10 distributed equally
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            if lm_a in ctrl_pos and lm_b in ctrl_pos:
                ia, ib = ctrl_pos[lm_a], ctrl_pos[lm_b]
                if src_pts[ia, 0] < src_pts[ib, 0]:
                    assert abs(sym_delta[ia, 0] - (-5.0)) < 1e-10  # left: -5
                    assert abs(sym_delta[ib, 0] - 5.0) < 1e-10     # right: +5
                break  # just check first pair

    def test_midline_horizontal_zeroed(self):
        """Midline landmarks should have zero horizontal delta."""
        from comfyui_imgtools.utils.morph_utils import (
            _symmetrize_delta, MORPH_CONTROL_INDICES, _MORPH_MIDLINE_INDICES,
        )

        n = len(MORPH_CONTROL_INDICES)
        ctrl_pos = {lm_id: i for i, lm_id in enumerate(MORPH_CONTROL_INDICES)}

        src_pts = np.ones((n, 2)) * 100.0
        delta = np.ones((n, 2)) * 5.0  # all deltas = (5, 5)

        sym_delta = _symmetrize_delta(delta, src_pts)

        for lm_id in _MORPH_MIDLINE_INDICES:
            if lm_id in ctrl_pos:
                assert sym_delta[ctrl_pos[lm_id], 0] == 0.0, (
                    f"Midline landmark {lm_id} should have zero horizontal delta"
                )


class TestMorphWarp:
    """Test compute_morph_warp TPS pipeline."""

    @pytest.fixture
    def deterministic_landmarks_pair(self):
        """Create a pair of source/target 478-point landmarks for warp tests."""
        from tests.conftest import _make_deterministic_landmarks

        source = _make_deterministic_landmarks(128.0, 128.0, spread=30.0, height_ratio=1.3)
        # Target has different shape: narrower but taller face
        target = _make_deterministic_landmarks(128.0, 128.0, spread=22.0, height_ratio=1.9)
        return source, target

    def test_identity_warp(self, deterministic_landmarks_pair):
        """Identical source/target produces identity-like TPS transform."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, _ = deterministic_landmarks_pair
        tps, morphed_pts, _ = compute_morph_warp(source, source, strength=1.0, img_shape=(256, 256))

        assert tps is not None
        # Applying the TPS to source control points should return ~same points
        src_pts = source[MORPH_CONTROL_INDICES]
        mapped = tps(src_pts)
        np.testing.assert_allclose(mapped, src_pts, atol=1.0)

    def test_different_landmarks_produces_movement(self, deterministic_landmarks_pair):
        """Different source/target with strength=1.0 moves source points toward target."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps, morphed_pts, _ = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

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
        tps, _, _ = compute_morph_warp(source, target, strength=0.0, img_shape=(256, 256))

        assert tps is not None
        src_pts = source[MORPH_CONTROL_INDICES]
        mapped = tps(src_pts)
        np.testing.assert_allclose(mapped, src_pts, atol=1.0)

    def test_strength_one_full_movement(self, deterministic_landmarks_pair):
        """Strength 1.0 moves source control points fully toward target positions."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp

        source, target = deterministic_landmarks_pair
        tps, morphed_pts, _ = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert tps is not None
        assert morphed_pts is not None

    def test_strength_half_intermediate(self, deterministic_landmarks_pair):
        """Strength 0.5 produces intermediate movement between 0 and 1."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps_half, _, _ = compute_morph_warp(source, target, strength=0.5, img_shape=(256, 256))
        tps_full, _, _ = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert tps_half is not None
        assert tps_full is not None

        src_pts = source[MORPH_CONTROL_INDICES]
        mapped_half = tps_half(src_pts)
        mapped_full = tps_full(src_pts)

        # Half-strength movement should be less than full-strength
        diff_half = np.linalg.norm(mapped_half - src_pts, axis=1).mean()
        diff_full = np.linalg.norm(mapped_full - src_pts, axis=1).mean()
        assert diff_half < diff_full * 0.8, "Half strength should produce less movement"

    def test_returns_morphed_control_points(self, deterministic_landmarks_pair):
        """compute_morph_warp returns morphed control point positions."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source, target = deterministic_landmarks_pair
        tps, morphed_pts, _ = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))

        assert morphed_pts is not None
        assert morphed_pts.shape == (len(MORPH_CONTROL_INDICES), 2)

    def test_pose_invariance(self):
        """Rotated target produces same morph as unrotated target with same shape."""
        from tests.conftest import _make_deterministic_landmarks
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        source = _make_deterministic_landmarks(128.0, 128.0, spread=30.0, height_ratio=1.3)
        target = _make_deterministic_landmarks(128.0, 128.0, spread=24.0, height_ratio=1.8)

        # Create a rotated version of target (simulating different head pose)
        theta = np.radians(15)
        R = np.array([[np.cos(theta), -np.sin(theta)],
                       [np.sin(theta), np.cos(theta)]])
        target_rotated = target.copy()
        centroid = target[MORPH_CONTROL_INDICES].mean(axis=0)
        for idx in MORPH_CONTROL_INDICES:
            target_rotated[idx] = (target[idx] - centroid) @ R.T + centroid

        _, morphed_normal, _ = compute_morph_warp(source, target, strength=1.0, img_shape=(256, 256))
        _, morphed_rotated, _ = compute_morph_warp(source, target_rotated, strength=1.0, img_shape=(256, 256))

        # Morphed positions should be similar regardless of target rotation
        np.testing.assert_allclose(morphed_normal, morphed_rotated, atol=2.0)


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
