"""Tests for FaceShapeMorph ComfyUI node."""

import numpy as np
import pytest
import torch

from comfyui_imgtools.face_morph import FaceShapeMorph
from comfyui_imgtools.utils.morph_utils import MORPH_CONTROL_INDICES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_morph_landmarks(center_x, center_y, eye_spread=30.0, face_width=40.0,
                          face_height_ratio=1.3, eye_size=5.0):
    """Create deterministic 478-point landmarks with controllable geometry.

    eye_spread controls horizontal distance from center to each eye center.
    face_width controls the face oval horizontal radius.
    face_height_ratio controls height/width ratio of the face oval (>1 = taller).
    eye_size controls the radius of the elliptical spread of eye landmarks.
    """
    from comfyui_imgtools.utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
    from comfyui_imgtools.utils.face_mask import FACE_OVAL_INDICES

    landmarks = np.zeros((478, 2), dtype=np.float64)

    # Fill all landmarks with a grid around center (deterministic)
    rng = np.random.RandomState(99)
    landmarks[:, 0] = center_x + rng.uniform(-face_width * 0.5, face_width * 0.5, 478)
    landmarks[:, 1] = center_y + rng.uniform(-face_width * 0.5, face_width * 0.5, 478)

    # Set eye landmarks
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

    # Set face oval landmarks in ellipse with controllable width and height
    n_oval = len(FACE_OVAL_INDICES)
    for i, idx in enumerate(FACE_OVAL_INDICES):
        angle = 2 * np.pi * i / n_oval
        landmarks[idx] = [
            center_x + face_width * np.cos(angle),
            center_y + face_width * face_height_ratio * np.sin(angle),
        ]

    return landmarks


@pytest.fixture
def source_landmarks():
    """Source face landmarks centered at (128, 128) — round face shape."""
    lms = _make_morph_landmarks(128.0, 128.0, eye_spread=30.0, face_width=40.0,
                                face_height_ratio=1.3)
    return [{"landmarks": lms, "landmarks_3d": np.zeros((478, 3), dtype=np.float64)}]


@pytest.fixture
def target_landmarks():
    """Target face landmarks centered at (128, 128) — narrower, taller face shape."""
    lms = _make_morph_landmarks(128.0, 128.0, eye_spread=30.0, face_width=30.0,
                                face_height_ratio=1.8, eye_size=5.0)
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
        assert rmse > 0.001, f"Strength 1.0 should produce visible change, RMSE={rmse}"


# ---------------------------------------------------------------------------
# TestAlignDataPassthrough
# ---------------------------------------------------------------------------

class TestAlignDataPassthrough:
    """Verify ALIGN_DATA is passed through with head_scale added."""

    def test_align_data_preserves_fields(self, source_image, target_image,
                                          source_landmarks, target_landmarks,
                                          sample_align_data):
        node = FaceShapeMorph()
        _, _, align = node.morph(source_image, target_image, source_landmarks,
                                  target_landmarks, sample_align_data, strength=0.5)
        # Original fields preserved
        for key in ("transform_matrix", "crop_box", "original_size"):
            assert key in align

    def test_align_data_has_head_scale(self, source_image, target_image,
                                        source_landmarks, target_landmarks,
                                        sample_align_data):
        node = FaceShapeMorph()
        _, _, align = node.morph(source_image, target_image, source_landmarks,
                                  target_landmarks, sample_align_data, strength=0.5)
        assert "head_scale" in align
        assert isinstance(align["head_scale"], float)


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
        assert rmse > 0.001, f"Features should move at strength=1.0, RMSE={rmse}"

    def test_morphed_shape_differs_from_source(self, source_landmarks, target_landmarks):
        """At strength=1.0, morphed control points should differ from source."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        src_lms = source_landmarks[0]["landmarks"]
        tgt_lms = target_landmarks[0]["landmarks"]

        src_pts = src_lms[MORPH_CONTROL_INDICES]

        _, morphed_pts, _ = compute_morph_warp(src_lms, tgt_lms, strength=1.0, img_shape=(256, 256))
        assert morphed_pts is not None

        # Morphed control points should have moved from source positions
        max_displacement = np.linalg.norm(morphed_pts - src_pts, axis=1).max()
        assert max_displacement > 1.0, (
            f"Morphed points should differ from source, max displacement={max_displacement:.4f}"
        )

    def test_shape_change_without_uniform_scale(self, source_landmarks, target_landmarks):
        """Morph should change shape proportions without uniform scaling."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        src_lms = source_landmarks[0]["landmarks"]
        tgt_lms = target_landmarks[0]["landmarks"]

        src_pts = src_lms[MORPH_CONTROL_INDICES]

        _, morphed_pts, _ = compute_morph_warp(src_lms, tgt_lms, strength=1.0, img_shape=(256, 256))
        assert morphed_pts is not None

        # Morph should change shape (some distances change) but not apply
        # uniform scaling (overall spread stays similar to source).
        src_spread = np.linalg.norm(src_pts - src_pts.mean(axis=0), axis=1).mean()
        morphed_spread = np.linalg.norm(morphed_pts - morphed_pts.mean(axis=0), axis=1).mean()
        scale_change = abs(morphed_spread / src_spread - 1.0)
        # Allow some change from shape morphing, but not a large uniform scale
        assert scale_change < 0.3, (
            f"Spread changed by {scale_change:.1%}, expected shape change without "
            f"large uniform scaling"
        )

    def test_relative_spacing_preserved(self, source_landmarks, target_landmarks):
        """Neighboring contour point ratios should stay proportional after morph."""
        from comfyui_imgtools.utils.morph_utils import compute_morph_warp, MORPH_CONTROL_INDICES

        src_lms = source_landmarks[0]["landmarks"]
        tgt_lms = target_landmarks[0]["landmarks"]

        src_pts = src_lms[MORPH_CONTROL_INDICES]
        _, morphed_px, _ = compute_morph_warp(src_lms, tgt_lms, strength=1.0, img_shape=(256, 256))
        assert morphed_px is not None

        # Use three face oval points: forehead (10), chin (152), side (234)
        idx_10 = MORPH_CONTROL_INDICES.index(10)
        idx_152 = MORPH_CONTROL_INDICES.index(152)
        idx_234 = MORPH_CONTROL_INDICES.index(234)

        def _spacing_ratio(pts, i1, i2, i3):
            d1 = np.linalg.norm(pts[i1] - pts[i2])
            d2 = np.linalg.norm(pts[i2] - pts[i3])
            if d2 < 1e-6:
                return float("inf")
            return d1 / d2

        src_ratio = _spacing_ratio(src_pts, idx_10, idx_152, idx_234)
        morphed_ratio = _spacing_ratio(morphed_px, idx_10, idx_152, idx_234)

        if src_ratio > 0 and src_ratio != float("inf"):
            deviation = abs(morphed_ratio - src_ratio) / src_ratio
            assert deviation < 0.30, (
                f"Contour spacing ratio deviation {deviation:.2%} exceeds 30% "
                f"(source={src_ratio:.3f}, morphed={morphed_ratio:.3f})"
            )
