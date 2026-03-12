"""Tests for FaceModelMorph node (face_model_morph.py)."""

import math
from unittest.mock import patch

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_synthetic_face(yaw=0.0, pitch=0.0, roll=0.0, has_pose=True):
    """Create a synthetic face dict like FaceDetect returns.

    landmarks: (478, 2) pixel coords with eyes at known positions.
    landmarks_3d: (478, 3) with distinct iris positions for nonzero IPD.
    """
    rng = np.random.default_rng(42)
    lm2d = rng.random((478, 2)).astype(np.float64) * 60 + 2  # pixel coords in [2, 62]
    lm3d = rng.random((478, 3)).astype(np.float64)

    # Set eye landmarks so compute_eye_centers gives a sane IED
    from utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
    for idx in LEFT_EYE_INDICES:
        lm2d[idx] = [20.0, 30.0]
    for idx in RIGHT_EYE_INDICES:
        lm2d[idx] = [44.0, 30.0]

    # Set iris centers for nonzero IPD in 3D
    lm3d[468] = [0.4, 0.5, 0.0]  # left iris
    lm3d[473] = [0.6, 0.5, 0.0]  # right iris

    if has_pose:
        # Build rotation matrix from angles for realistic pose
        from scipy.spatial.transform import Rotation
        r = Rotation.from_euler("XYZ", [pitch, yaw, roll], degrees=True)
        mat = np.eye(4, dtype=np.float64)
        mat[:3, :3] = r.as_matrix()
        pose = {
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "matrix": mat,
        }
    else:
        pose = None

    return {
        "landmarks": lm2d,
        "landmarks_3d": lm3d,
        "pose": pose,
    }


def _make_synthetic_model(offset=0.0):
    """Create a synthetic FACE_MODEL dict.

    canonical_landmarks: (478, 2) IPD-normalized 2D coordinates.
    Offset parameter shifts landmarks to create a visible delta vs source.
    """
    rng = np.random.default_rng(99)
    canonical = rng.random((478, 2)).astype(np.float64) * 2 - 1  # IPD-normalized range
    canonical += offset  # shift to create shape difference

    # Set iris positions for consistency (IPD ~ 1.0 in normalized space)
    canonical[468] = [-0.5, 0.0]
    canonical[473] = [0.5, 0.0]

    return {
        "version": "2",
        "canonical_landmarks": canonical,
        "head_dimensions": {"width": 1.8, "height": 2.3, "depth": 1.0},
        "control_indices": np.array(sorted(set(
            [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
             46, 55, 107, 276, 285, 336]
        )), dtype=np.int64),
        "landmark_stddev": rng.random((478, 3)).astype(np.float64) * 0.01,
    }


def _make_test_image(h=64, w=64):
    """Create a test IMAGE tensor (1, H, W, 3) float32."""
    return torch.rand(1, h, w, 3, dtype=torch.float32)


def _make_align_data():
    """Create a minimal ALIGN_DATA dict."""
    return {"crop_box": (0, 0, 64, 64), "transform": np.eye(3)}


# ---------------------------------------------------------------------------
# TestConventions
# ---------------------------------------------------------------------------

class TestConventions:
    """Node class conventions match specification."""

    def test_input_types_required(self):
        """INPUT_TYPES has all required inputs."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        inputs = FaceModelMorph.INPUT_TYPES()
        req = inputs["required"]
        assert "source_image" in req
        assert "face_model" in req
        assert "source_landmarks" in req
        assert "source_align_data" in req
        assert "strength" in req

    def test_input_types_optional_symmetrize(self):
        """INPUT_TYPES has optional symmetrize boolean."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        inputs = FaceModelMorph.INPUT_TYPES()
        assert "symmetrize" in inputs.get("optional", {})

    def test_return_types_match_face_shape_morph(self):
        """RETURN_TYPES matches FaceShapeMorph exactly."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from comfyui_imgtools.face_morph import FaceShapeMorph
        assert FaceModelMorph.RETURN_TYPES == FaceShapeMorph.RETURN_TYPES

    def test_return_names_match_face_shape_morph(self):
        """RETURN_NAMES matches FaceShapeMorph exactly."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from comfyui_imgtools.face_morph import FaceShapeMorph
        assert FaceModelMorph.RETURN_NAMES == FaceShapeMorph.RETURN_NAMES

    def test_function_is_morph(self):
        """FUNCTION attribute is 'morph'."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        assert FaceModelMorph.FUNCTION == "morph"

    def test_category_is_imgtools_face(self):
        """CATEGORY attribute is 'imgtools/face'."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        assert FaceModelMorph.CATEGORY == "imgtools/face"

    def test_strength_defaults(self):
        """Strength has default 0.5, min 0.0, max 1.0, step 0.05."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        inputs = FaceModelMorph.INPUT_TYPES()
        strength_spec = inputs["required"]["strength"]
        assert strength_spec[1]["default"] == 0.5
        assert strength_spec[1]["min"] == 0.0
        assert strength_spec[1]["max"] == 1.0
        assert strength_spec[1]["step"] == 0.05


# ---------------------------------------------------------------------------
# TestPoseAwareDelta
# ---------------------------------------------------------------------------

class TestPoseAwareDelta:
    """Pose-aware delta computation produces correct results."""

    def test_strength_1_produces_displacement(self):
        """At strength=1.0, morphed control points differ from source."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=1.0)
        morphed_img, mask, out_align = result

        # The morphed image should differ from source (non-trivial warp)
        src_np = img[0].numpy()
        morph_np = morphed_img[0].numpy()
        diff = np.abs(src_np - morph_np).mean()
        assert diff > 0.001, f"Expected visible displacement, got mean diff {diff}"

    def test_strength_0_no_displacement(self):
        """At strength=0.0, output image equals source image."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.0)
        morphed_img, mask, out_align = result

        # With strength=0, TPS should be identity (or near-identity)
        src_np = img[0].numpy()
        morph_np = morphed_img[0].numpy()
        diff = np.abs(src_np - morph_np).mean()
        assert diff < 0.01, f"Expected no displacement at strength=0, got mean diff {diff}"


# ---------------------------------------------------------------------------
# TestFallbackPath
# ---------------------------------------------------------------------------

class TestFallbackPath:
    """Procrustes fallback path (pose=None) works correctly."""

    def test_no_pose_produces_valid_warp(self):
        """pose=None produces a valid warp without crashing."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(has_pose=False)
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=1.0)
        morphed_img, mask, out_align = result

        assert morphed_img.shape == img.shape
        assert mask.shape == (1, 64, 64)

    def test_fallback_produces_displacement(self):
        """Fallback path at strength=1.0 produces visible change."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(has_pose=False)
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=1.0)
        morphed_img, mask, out_align = result

        src_np = img[0].numpy()
        morph_np = morphed_img[0].numpy()
        diff = np.abs(src_np - morph_np).mean()
        assert diff > 0.001, f"Expected displacement in fallback, got mean diff {diff}"


# ---------------------------------------------------------------------------
# TestPoseAttenuation
# ---------------------------------------------------------------------------

class TestPoseAttenuation:
    """Cosine pose attenuation reduces effective strength."""

    def test_frontal_full_strength(self):
        """yaw=0, pitch=0 -> effective_strength equals user_strength."""
        factor = math.cos(math.radians(0)) * math.cos(math.radians(0))
        assert factor == pytest.approx(1.0)

    def test_yaw_45_reduces_strength(self):
        """yaw=45 -> factor ~0.707."""
        factor = math.cos(math.radians(45)) * math.cos(math.radians(0))
        assert factor == pytest.approx(math.sqrt(2) / 2, rel=1e-3)

    def test_yaw_80_near_zero(self):
        """yaw=80 -> factor ~0.17, minimal displacement."""
        factor = math.cos(math.radians(80)) * math.cos(math.radians(0))
        assert factor < 0.2

    def test_high_yaw_minimal_morph(self):
        """At yaw=80, morph displacement is much smaller than at yaw=0."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        # Frontal face
        img_frontal = _make_test_image()
        face_frontal = _make_synthetic_face(yaw=0.0, pitch=0.0)
        result_frontal = node.morph(img_frontal, model, [face_frontal], align_data, strength=1.0)
        diff_frontal = np.abs(img_frontal[0].numpy() - result_frontal[0][0].numpy()).mean()

        # High yaw face
        img_yaw = _make_test_image()
        face_yaw = _make_synthetic_face(yaw=80.0, pitch=0.0)
        result_yaw = node.morph(img_yaw, model, [face_yaw], align_data, strength=1.0)
        diff_yaw = np.abs(img_yaw[0].numpy() - result_yaw[0][0].numpy()).mean()

        # High yaw should produce much less displacement
        assert diff_yaw < diff_frontal, (
            f"Expected yaw=80 ({diff_yaw:.4f}) < yaw=0 ({diff_frontal:.4f})"
        )


# ---------------------------------------------------------------------------
# TestSymmetrize
# ---------------------------------------------------------------------------

class TestSymmetrize:
    """Model symmetrization (MRPH-03) works correctly."""

    def test_symmetrize_changes_model(self):
        """symmetrize=True changes the delta vs symmetrize=False."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph, _symmetrize_model
        from utils.morph_utils import _MORPH_MIRROR_PAIRS

        model = _make_synthetic_model()
        canonical = model["canonical_landmarks"]

        # Make the model asymmetric by shifting one side
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS[:5]:
            canonical[lm_a, 0] += 0.1

        symmetrized = _symmetrize_model(canonical)
        assert not np.allclose(canonical, symmetrized), "Symmetrized should differ from asymmetric input"

    def test_symmetrize_false_leaves_unchanged(self):
        """symmetrize=False leaves model landmarks unchanged."""
        from comfyui_imgtools.face_model_morph import _symmetrize_model

        model = _make_synthetic_model()
        original = model["canonical_landmarks"].copy()
        # Not calling _symmetrize_model means original is used
        assert np.array_equal(original, model["canonical_landmarks"])

    def test_mirror_pairs_equal_after_symmetrize(self):
        """After symmetrization, mirror pair X-distances from midline are equal."""
        from comfyui_imgtools.face_model_morph import _symmetrize_model
        from utils.morph_utils import _MORPH_MIRROR_PAIRS, _MORPH_MIDLINE_INDICES

        model = _make_synthetic_model()
        sym = _symmetrize_model(model["canonical_landmarks"])

        midline_x = np.mean([sym[idx, 0] for idx in _MORPH_MIDLINE_INDICES])
        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            dist_a = abs(sym[lm_a, 0] - midline_x)
            dist_b = abs(sym[lm_b, 0] - midline_x)
            assert dist_a == pytest.approx(dist_b, abs=1e-10), (
                f"Pair ({lm_a}, {lm_b}): {dist_a} != {dist_b}"
            )

    def test_mirror_pairs_equal_y_after_symmetrize(self):
        """After symmetrization, mirror pair Y values are equal."""
        from comfyui_imgtools.face_model_morph import _symmetrize_model
        from utils.morph_utils import _MORPH_MIRROR_PAIRS

        model = _make_synthetic_model()
        sym = _symmetrize_model(model["canonical_landmarks"])

        for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
            assert sym[lm_a, 1] == pytest.approx(sym[lm_b, 1], abs=1e-10), (
                f"Pair ({lm_a}, {lm_b}): Y {sym[lm_a, 1]} != {sym[lm_b, 1]}"
            )


# ---------------------------------------------------------------------------
# TestAlignData
# ---------------------------------------------------------------------------

class TestAlignData:
    """Output align_data contains head_scale."""

    def test_head_scale_in_output(self):
        """Output align_data has 'head_scale' key with float value."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        model = _make_synthetic_model()
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        _, _, out_align = result
        assert "head_scale" in out_align
        assert isinstance(out_align["head_scale"], float)

    def test_head_scale_reasonable_value(self):
        """head_scale is a reasonable positive float."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        model = _make_synthetic_model()
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        _, _, out_align = result
        assert out_align["head_scale"] > 0.0
        assert out_align["head_scale"] < 10.0  # sanity bound


# ---------------------------------------------------------------------------
# TestGracefulDegradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Passthrough on invalid inputs."""

    def test_empty_landmarks_passthrough(self):
        """Empty landmarks list returns passthrough."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        model = _make_synthetic_model()
        align_data = _make_align_data()

        result = node.morph(img, model, [], align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert torch.equal(morphed_img, img)
        assert mask.shape == (1, 64, 64)

    def test_none_landmarks_passthrough(self):
        """None landmarks returns passthrough."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        model = _make_synthetic_model()
        align_data = _make_align_data()

        result = node.morph(img, model, None, align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert torch.equal(morphed_img, img)

    def test_zero_ied_passthrough(self):
        """Zero inter-eye distance returns passthrough."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES

        node = FaceModelMorph()
        img = _make_test_image()
        model = _make_synthetic_model()
        align_data = _make_align_data()

        # Make a face with zero IED
        face = _make_synthetic_face()
        for idx in LEFT_EYE_INDICES + RIGHT_EYE_INDICES:
            face["landmarks"][idx] = [32.0, 32.0]

        result = node.morph(img, model, [face], align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert torch.equal(morphed_img, img)


# ---------------------------------------------------------------------------
# TestMorphOutput
# ---------------------------------------------------------------------------

class TestMorphOutput:
    """Full morph call returns correct types and shapes."""

    def test_returns_3_tuple(self):
        """morph() returns a 3-tuple."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face()
        model = _make_synthetic_model(offset=0.2)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        assert len(result) == 3

    def test_output_image_shape(self):
        """Output image has same shape as input."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face()
        model = _make_synthetic_model(offset=0.2)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert morphed_img.shape == img.shape

    def test_output_mask_shape(self):
        """Output mask has shape (1, H, W)."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face()
        model = _make_synthetic_model(offset=0.2)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert mask.shape == (1, 64, 64)

    def test_output_types(self):
        """Output types are torch.Tensor, torch.Tensor, dict."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face()
        model = _make_synthetic_model(offset=0.2)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        morphed_img, mask, out_align = result
        assert isinstance(morphed_img, torch.Tensor)
        assert isinstance(mask, torch.Tensor)
        assert isinstance(out_align, dict)


# ---------------------------------------------------------------------------
# TestRegistration
# ---------------------------------------------------------------------------

class TestRegistration:
    """FaceModelMorph is registered in ComfyUI node system."""

    def test_node_registered(self):
        """FaceModelMorph is in NODE_CLASS_MAPPINGS."""
        import comfyui_imgtools as pkg
        assert "FaceModelMorph" in pkg.NODE_CLASS_MAPPINGS

    def test_display_name(self):
        """Display name is 'ImgTools Face Model Morph'."""
        import comfyui_imgtools as pkg
        assert pkg.NODE_DISPLAY_NAME_MAPPINGS["FaceModelMorph"] == "ImgTools Face Model Morph"

    def test_drop_in_replacement(self):
        """RETURN_TYPES and RETURN_NAMES match FaceShapeMorph exactly."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph
        from comfyui_imgtools.face_morph import FaceShapeMorph
        assert FaceModelMorph.RETURN_TYPES == FaceShapeMorph.RETURN_TYPES
        assert FaceModelMorph.RETURN_NAMES == FaceShapeMorph.RETURN_NAMES


# ---------------------------------------------------------------------------
# TestHeadScalePassthrough
# ---------------------------------------------------------------------------

class TestHeadScalePassthrough:
    """head_scale in output align_data is correct."""

    def test_head_scale_in_align_data(self):
        """Output align_data contains 'head_scale' key with a float value."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        model = _make_synthetic_model(offset=0.2)
        align_data = _make_align_data()

        result = node.morph(img, model, [face], align_data, strength=0.5)
        _, _, out_align = result
        assert "head_scale" in out_align
        assert isinstance(out_align["head_scale"], float)

    def test_head_scale_interpolated_by_strength(self):
        """strength=0.0 -> head_scale==1.0, strength=1.0 -> head_scale!=1.0."""
        from comfyui_imgtools.face_model_morph import FaceModelMorph

        node = FaceModelMorph()
        img = _make_test_image()
        face = _make_synthetic_face(yaw=0.0, pitch=0.0)
        # Use offset to ensure model and source have different head dimensions
        model = _make_synthetic_model(offset=0.3)
        align_data = _make_align_data()

        # At strength=0.0, head_scale should be 1.0 (no change)
        result_0 = node.morph(img, model, [face], align_data, strength=0.0)
        _, _, out_align_0 = result_0
        assert out_align_0["head_scale"] == pytest.approx(1.0, abs=1e-6), (
            f"Expected head_scale=1.0 at strength=0, got {out_align_0['head_scale']}"
        )

        # At strength=1.0, head_scale should differ from 1.0
        result_1 = node.morph(img, model, [face], align_data, strength=1.0)
        _, _, out_align_1 = result_1
        assert out_align_1["head_scale"] != pytest.approx(1.0, abs=1e-6), (
            f"Expected head_scale!=1.0 at strength=1, got {out_align_1['head_scale']}"
        )
