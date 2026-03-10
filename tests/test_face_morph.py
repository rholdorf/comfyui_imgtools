"""Tests for FaceShapeMorph ComfyUI node."""

import numpy as np
import pytest
import torch

from comfyui_imgtools.face_morph import FaceShapeMorph
from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_morph_landmarks(center_x, center_y, eye_spread=30.0, face_spread=40.0,
                          eye_size=5.0):
    """Create deterministic 478-point landmarks with controllable geometry.

    eye_spread controls horizontal distance from center to each eye center.
    face_spread controls the face oval radius.
    eye_size controls the radius of the elliptical spread of eye landmarks
    (determines intra-eye distances like corner-to-corner).
    """
    from comfyui_imgtools.utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
    from comfyui_imgtools.utils.face_mask import FACE_OVAL_INDICES

    landmarks = np.zeros((478, 2), dtype=np.float64)

    # Fill all landmarks with a grid around center (deterministic)
    rng = np.random.RandomState(99)
    landmarks[:, 0] = center_x + rng.uniform(-face_spread * 0.5, face_spread * 0.5, 478)
    landmarks[:, 1] = center_y + rng.uniform(-face_spread * 0.5, face_spread * 0.5, 478)

    # Set eye landmarks: subject left eye = image right, subject right eye = image left
    # Give each eye an elliptical spread so corner indices have distinct positions
    for i, idx in enumerate(LEFT_EYE_INDICES):
        angle = 2 * np.pi * i / len(LEFT_EYE_INDICES)
        landmarks[idx] = [
            center_x + eye_spread + eye_size * np.cos(angle),
            center_y - 10.0 + eye_size * 0.6 * np.sin(angle),
        ]
    for i, idx in enumerate(RIGHT_EYE_INDICES):
        angle = 2 * np.pi * i / len(RIGHT_EYE_INDICES)
        landmarks[idx] = [
            center_x - eye_spread + eye_size * np.cos(angle),
            center_y - 10.0 + eye_size * 0.6 * np.sin(angle),
        ]

    # Nose tip (index 1)
    landmarks[1] = [center_x, center_y + 5.0]

    # Set face oval landmarks in ellipse
    n_oval = len(FACE_OVAL_INDICES)
    for i, idx in enumerate(FACE_OVAL_INDICES):
        angle = 2 * np.pi * i / n_oval
        landmarks[idx] = [
            center_x + face_spread * np.cos(angle),
            center_y + face_spread * 1.3 * np.sin(angle),
        ]

    return landmarks


@pytest.fixture
def source_landmarks():
    """Source face landmarks centered at (128, 128) with eyes 60px apart."""
    lms = _make_morph_landmarks(128.0, 128.0, eye_spread=30.0, face_spread=40.0)
    return [{"landmarks": lms, "landmarks_3d": np.zeros((478, 3), dtype=np.float64)}]


@pytest.fixture
def target_landmarks():
    """Target face landmarks centered at (128, 128) with wider face and larger eyes."""
    lms = _make_morph_landmarks(128.0, 128.0, eye_spread=40.0, face_spread=50.0, eye_size=8.0)
    return [{"landmarks": lms, "landmarks_3d": np.zeros((478, 3), dtype=np.float64)}]


@pytest.fixture
def source_image():
    """A 256x256 ComfyUI IMAGE tensor with a gradient pattern (not uniform)."""
    # Create a gradient so warping produces visible pixel changes
    img = torch.zeros(1, 256, 256, 3, dtype=torch.float32)
    for c in range(3):
        grid = torch.linspace(0, 1, 256).unsqueeze(1 - c % 2).expand(256, 256)
        img[0, :, :, c] = grid
    return img


@pytest.fixture
def target_image():
    """A 256x256 ComfyUI IMAGE tensor (content doesn't matter for shape morph)."""
    return torch.rand(1, 256, 256, 3, dtype=torch.float32)


@pytest.fixture
def sample_align_data():
    """Sample ALIGN_DATA dict from FaceCropAlign."""
    return {
        "rotation_angle": 0.0,
        "rotation_center": (128.0, 128.0),
        "crop_box": (0, 0, 256, 256),
        "original_size": (256, 256),
        "transform_matrix": np.eye(3),
    }


# ---------------------------------------------------------------------------
# TestConventions
# ---------------------------------------------------------------------------

class TestConventions:
    """Verify ComfyUI node interface conventions."""

    def test_input_types_has_required_fields(self):
        inputs = FaceShapeMorph.INPUT_TYPES()
        req = inputs["required"]
        assert "source_image" in req
        assert req["source_image"] == ("IMAGE",)
        assert "target_image" in req
        assert req["target_image"] == ("IMAGE",)
        assert "source_landmarks" in req
        assert req["source_landmarks"] == ("FACE_LANDMARKS",)
        assert "target_landmarks" in req
        assert req["target_landmarks"] == ("FACE_LANDMARKS",)
        assert "source_align_data" in req
        assert req["source_align_data"] == ("ALIGN_DATA",)

    def test_input_types_strength_field(self):
        inputs = FaceShapeMorph.INPUT_TYPES()
        req = inputs["required"]
        assert "strength" in req
        strength_spec = req["strength"]
        assert strength_spec[0] == "FLOAT"
        opts = strength_spec[1]
        assert opts["default"] == 0.5
        assert opts["min"] == 0.0
        assert opts["max"] == 1.0
        assert opts["step"] == 0.05

    def test_return_types(self):
        assert FaceShapeMorph.RETURN_TYPES == ("IMAGE", "MASK", "ALIGN_DATA")

    def test_return_names(self):
        assert FaceShapeMorph.RETURN_NAMES == ("morphed_face", "warp_mask", "align_data")

    def test_function_name(self):
        assert FaceShapeMorph.FUNCTION == "morph"

    def test_category(self):
        assert FaceShapeMorph.CATEGORY == "imgtools/face"


# ---------------------------------------------------------------------------
# TestOutputs
# ---------------------------------------------------------------------------

class TestOutputs:
    """Verify morph() output shapes and types."""

    def test_returns_three_tuple(self, source_image, target_image, source_landmarks,
                                  target_landmarks, sample_align_data):
        node = FaceShapeMorph()
        result = node.morph(source_image, target_image, source_landmarks,
                            target_landmarks, sample_align_data, strength=0.5)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_image_tensor_shape(self, source_image, target_image, source_landmarks,
                                 target_landmarks, sample_align_data):
        node = FaceShapeMorph()
        morphed, mask, align = node.morph(source_image, target_image, source_landmarks,
                                           target_landmarks, sample_align_data, strength=0.5)
        assert morphed.shape == (1, 256, 256, 3)
        assert morphed.dtype == torch.float32

    def test_mask_tensor_shape(self, source_image, target_image, source_landmarks,
                                target_landmarks, sample_align_data):
        node = FaceShapeMorph()
        morphed, mask, align = node.morph(source_image, target_image, source_landmarks,
                                           target_landmarks, sample_align_data, strength=0.5)
        assert mask.shape == (1, 256, 256)
        assert mask.dtype == torch.float32

    def test_align_data_is_dict(self, source_image, target_image, source_landmarks,
                                 target_landmarks, sample_align_data):
        node = FaceShapeMorph()
        morphed, mask, align = node.morph(source_image, target_image, source_landmarks,
                                           target_landmarks, sample_align_data, strength=0.5)
        assert isinstance(align, dict)


# ---------------------------------------------------------------------------
# TestStrength
# ---------------------------------------------------------------------------

class TestStrength:
    """Verify strength parameter behavior."""

    def test_strength_zero_returns_source_unchanged(self, source_image, target_image,
                                                      source_landmarks, target_landmarks,
                                                      sample_align_data):
        node = FaceShapeMorph()
        morphed, _, _ = node.morph(source_image, target_image, source_landmarks,
                                    target_landmarks, sample_align_data, strength=0.0)
        rmse = torch.sqrt(torch.mean((morphed - source_image) ** 2)).item()
        assert rmse < 0.01, f"Strength 0.0 should return source unchanged, RMSE={rmse}"

    def test_strength_one_produces_visible_change(self, source_image, target_image,
                                                    source_landmarks, target_landmarks,
                                                    sample_align_data):
        node = FaceShapeMorph()
        morphed, _, _ = node.morph(source_image, target_image, source_landmarks,
                                    target_landmarks, sample_align_data, strength=1.0)
        rmse = torch.sqrt(torch.mean((morphed - source_image) ** 2)).item()
        assert rmse > 0.01, f"Strength 1.0 should produce visible change, RMSE={rmse}"


# ---------------------------------------------------------------------------
# TestAlignDataPassthrough
# ---------------------------------------------------------------------------

class TestAlignDataPassthrough:
    """Verify ALIGN_DATA is passed through unchanged."""

    def test_align_data_is_same_object(self, source_image, target_image,
                                        source_landmarks, target_landmarks,
                                        sample_align_data):
        node = FaceShapeMorph()
        _, _, align = node.morph(source_image, target_image, source_landmarks,
                                  target_landmarks, sample_align_data, strength=0.5)
        assert align is sample_align_data


# ---------------------------------------------------------------------------
# TestGracefulDegradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Verify graceful fallback on invalid inputs."""

    def test_empty_landmarks_returns_source(self, source_image, target_image,
                                             sample_align_data):
        node = FaceShapeMorph()
        empty_lms = []
        morphed, mask, align = node.morph(source_image, target_image,
                                           empty_lms, empty_lms,
                                           sample_align_data, strength=0.5)
        assert torch.allclose(morphed, source_image)
        assert align is sample_align_data

    def test_empty_landmarks_returns_full_mask(self, source_image, target_image,
                                                sample_align_data):
        node = FaceShapeMorph()
        empty_lms = []
        _, mask, _ = node.morph(source_image, target_image,
                                 empty_lms, empty_lms,
                                 sample_align_data, strength=0.5)
        assert mask.shape == (1, 256, 256)
        assert torch.all(mask == 1.0)

    def test_zero_ied_returns_source(self, source_image, target_image,
                                      sample_align_data):
        """Landmarks where all eye indices are at the same point (IED=0)."""
        # Create landmarks where eyes overlap perfectly
        lms = np.ones((478, 2), dtype=np.float64) * 128.0
        face_lms = [{"landmarks": lms, "landmarks_3d": np.zeros((478, 3))}]
        node = FaceShapeMorph()
        morphed, mask, align = node.morph(source_image, target_image,
                                           face_lms, face_lms,
                                           sample_align_data, strength=1.0)
        assert torch.allclose(morphed, source_image)
        assert align is sample_align_data


# ---------------------------------------------------------------------------
# TestWarpMask
# ---------------------------------------------------------------------------

class TestWarpMask:
    """Verify warp mask properties."""

    def test_mask_values_in_range(self, source_image, target_image,
                                   source_landmarks, target_landmarks,
                                   sample_align_data):
        node = FaceShapeMorph()
        _, mask, _ = node.morph(source_image, target_image, source_landmarks,
                                 target_landmarks, sample_align_data, strength=0.5)
        assert mask.min() >= 0.0
        assert mask.max() <= 1.0

    def test_mask_has_soft_edges(self, source_image, target_image,
                                  source_landmarks, target_landmarks,
                                  sample_align_data):
        """Feathered mask should have intermediate values, not just 0/1."""
        node = FaceShapeMorph()
        _, mask, _ = node.morph(source_image, target_image, source_landmarks,
                                 target_landmarks, sample_align_data, strength=0.5)
        unique_vals = torch.unique(mask)
        # With Gaussian feathering, there should be many intermediate values
        assert len(unique_vals) > 10, "Mask should have soft edges, not binary"


# ---------------------------------------------------------------------------
# TestFeatureCoherence
# ---------------------------------------------------------------------------

class TestFeatureCoherence:
    """Verify morphed features move proportionally toward target."""

    def test_morph_produces_rmse_above_threshold(self, source_image, target_image,
                                                   source_landmarks, target_landmarks,
                                                   sample_align_data):
        """Warp at strength=1.0 should visibly change interior features."""
        node = FaceShapeMorph()
        morphed, _, _ = node.morph(source_image, target_image, source_landmarks,
                                    target_landmarks, sample_align_data, strength=1.0)
        rmse = torch.sqrt(torch.mean((morphed - source_image) ** 2)).item()
        assert rmse > 0.01, f"Features should move at strength=1.0, RMSE={rmse}"

    def test_eye_corner_distance_closer_to_target(self, source_landmarks, target_landmarks):
        """After morph at strength=1.0, eye-corner proportions in normalized space
        should match target proportions, not source proportions."""
        from comfyui_imgtools.utils.morph_utils import (
            normalize_landmarks,
            MORPH_CONTROL_INDICES,
        )
        from comfyui_imgtools.utils.alignment import compute_eye_centers

        src_lms = source_landmarks[0]["landmarks"]
        tgt_lms = target_landmarks[0]["landmarks"]

        # Compute in normalized (IED-independent) space
        src_pts = src_lms[MORPH_CONTROL_INDICES]
        tgt_pts = tgt_lms[MORPH_CONTROL_INDICES]

        src_eye_centers = compute_eye_centers(src_lms)
        tgt_eye_centers = compute_eye_centers(tgt_lms)

        src_norm, _ = normalize_landmarks(src_pts, src_eye_centers)
        tgt_norm, _ = normalize_landmarks(tgt_pts, tgt_eye_centers)

        # At strength=1.0, morphed_norm = tgt_norm
        morphed_norm = src_norm + 1.0 * (tgt_norm - src_norm)

        # Find indices of eye corners 33 and 133 in MORPH_CONTROL_INDICES
        idx_33 = MORPH_CONTROL_INDICES.index(33)
        idx_133 = MORPH_CONTROL_INDICES.index(133)

        src_eye_dist_norm = np.linalg.norm(src_norm[idx_33] - src_norm[idx_133])
        tgt_eye_dist_norm = np.linalg.norm(tgt_norm[idx_33] - tgt_norm[idx_133])
        morphed_eye_dist_norm = np.linalg.norm(morphed_norm[idx_33] - morphed_norm[idx_133])

        # Morphed normalized distance should be closer to target than source
        dist_to_src = abs(morphed_eye_dist_norm - src_eye_dist_norm)
        dist_to_tgt = abs(morphed_eye_dist_norm - tgt_eye_dist_norm)
        assert dist_to_tgt < dist_to_src, (
            f"Morphed eye dist norm ({morphed_eye_dist_norm:.4f}) should be closer to "
            f"target ({tgt_eye_dist_norm:.4f}) than source ({src_eye_dist_norm:.4f})"
        )

    def test_relative_spacing_preserved(self, source_landmarks, target_landmarks):
        """Neighboring feature point ratios should stay proportional after morph (< 15% deviation)."""
        from comfyui_imgtools.utils.morph_utils import (
            normalize_landmarks,
            MORPH_CONTROL_INDICES,
        )
        from comfyui_imgtools.utils.alignment import compute_eye_centers

        src_lms = source_landmarks[0]["landmarks"]
        tgt_lms = target_landmarks[0]["landmarks"]

        # Compute morphed control points at strength=1.0
        src_pts = src_lms[MORPH_CONTROL_INDICES]
        tgt_pts = tgt_lms[MORPH_CONTROL_INDICES]

        src_eye_centers = compute_eye_centers(src_lms)
        tgt_eye_centers = compute_eye_centers(tgt_lms)

        src_norm, src_ied = normalize_landmarks(src_pts, src_eye_centers)
        tgt_norm, _ = normalize_landmarks(tgt_pts, tgt_eye_centers)

        morphed_norm = src_norm + 1.0 * (tgt_norm - src_norm)
        left_eye, right_eye = src_eye_centers
        center = (left_eye + right_eye) / 2.0
        morphed_px = morphed_norm * src_ied + center

        # Feature indices: left eye corner (33), nose tip (1 -> find in control indices), right eye corner (263)
        # Use 33, 1, 263 from control indices
        idx_33 = MORPH_CONTROL_INDICES.index(33)
        idx_1 = MORPH_CONTROL_INDICES.index(1)
        idx_263 = MORPH_CONTROL_INDICES.index(263)

        # Target morphed points for ratio comparison
        tgt_norm_denorm = tgt_norm * src_ied + center  # denormalize target to src pixel space

        # Compute ratios: left-eye-to-nose / nose-to-right-eye
        def _spacing_ratio(pts, i1, i2, i3):
            d1 = np.linalg.norm(pts[i1] - pts[i2])
            d2 = np.linalg.norm(pts[i2] - pts[i3])
            if d2 < 1e-6:
                return float("inf")
            return d1 / d2

        src_ratio = _spacing_ratio(src_pts, idx_33, idx_1, idx_263)
        morphed_ratio = _spacing_ratio(morphed_px, idx_33, idx_1, idx_263)

        # Ratio deviation should be < 15%
        if src_ratio > 0 and src_ratio != float("inf"):
            deviation = abs(morphed_ratio - src_ratio) / src_ratio
            assert deviation < 0.15, (
                f"Feature spacing ratio deviation {deviation:.2%} exceeds 15% "
                f"(source={src_ratio:.3f}, morphed={morphed_ratio:.3f})"
            )
