"""Tests for the FaceDetect ComfyUI node."""

import numpy as np
import pytest
import torch


class TestFaceDetectConventions:
    """Test that FaceDetect follows ComfyUI node conventions."""

    def test_node_conventions(self):
        from comfyui_imgtools.face_detection import FaceDetect

        # INPUT_TYPES is a classmethod returning dict with "required" containing "image"
        input_types = FaceDetect.INPUT_TYPES()
        assert isinstance(input_types, dict)
        assert "required" in input_types
        assert "image" in input_types["required"]
        assert input_types["required"]["image"] == ("IMAGE",)

        # RETURN_TYPES has 3 entries
        assert isinstance(FaceDetect.RETURN_TYPES, tuple)
        assert len(FaceDetect.RETURN_TYPES) == 3

        # RETURN_NAMES has 3 entries
        assert isinstance(FaceDetect.RETURN_NAMES, tuple)
        assert len(FaceDetect.RETURN_NAMES) == 3

        # FUNCTION is a string
        assert isinstance(FaceDetect.FUNCTION, str)

        # CATEGORY is a string
        assert isinstance(FaceDetect.CATEGORY, str)

        # The method named by FUNCTION exists
        assert hasattr(FaceDetect, FaceDetect.FUNCTION)


@pytest.mark.slow
class TestFaceDetectIntegration:
    """Integration tests requiring real MediaPipe face detection."""

    @pytest.fixture(scope="class")
    def real_face_tensor(self):
        """Create a tensor from a real face image for detection tests.

        Uses MediaPipe's built-in test image if available, otherwise
        creates a synthetic face-like pattern that may trigger detection.
        """
        # Try to use a real test image
        import os
        test_img_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "test_face.jpg"
        )
        if os.path.exists(test_img_path):
            from PIL import Image
            img = Image.open(test_img_path).convert("RGB")
            img_np = np.array(img).astype(np.float32) / 255.0
            return torch.from_numpy(img_np).unsqueeze(0)

        # Download a known face image for testing
        import urllib.request
        import tempfile
        url = "https://storage.googleapis.com/mediapipe-assets/portrait.jpg"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            urllib.request.urlretrieve(url, f.name)
            from PIL import Image
            img = Image.open(f.name).convert("RGB")
            img_np = np.array(img).astype(np.float32) / 255.0
            os.unlink(f.name)
            return torch.from_numpy(img_np).unsqueeze(0)

    def test_detect_landmarks_count(self, real_face_tensor):
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        assert isinstance(landmarks, list)
        assert len(landmarks) >= 1, "Should detect at least 1 face"
        assert landmarks[0]["landmarks"].shape == (478, 2)

    def test_landmarks_data_structure(self, real_face_tensor):
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        assert len(landmarks) >= 1
        face = landmarks[0]
        assert "landmarks" in face
        assert "landmarks_3d" in face
        assert isinstance(face["landmarks"], np.ndarray)
        assert isinstance(face["landmarks_3d"], np.ndarray)
        assert face["landmarks"].shape[1] == 2
        assert face["landmarks_3d"].shape[1] == 3

    def test_no_face_returns_empty(self):
        """Solid color image should return no faces and not crash."""
        from comfyui_imgtools.face_detection import FaceDetect

        # Solid blue image - no face
        no_face = torch.zeros(1, 256, 256, 3, dtype=torch.float32)
        no_face[:, :, :, 2] = 1.0  # solid blue

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(no_face)

        assert landmarks == []
        assert face_count == 0

    def test_preview_image_output(self, real_face_tensor):
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        # Preview should be a tensor with same spatial dims as input
        assert isinstance(preview, torch.Tensor)
        assert preview.dtype == torch.float32
        assert preview.shape[0] == 1  # batch
        assert preview.shape[1] == real_face_tensor.shape[1]  # H
        assert preview.shape[2] == real_face_tensor.shape[2]  # W
        assert preview.shape[3] == 3  # C
        assert preview.min() >= 0.0
        assert preview.max() <= 1.0

    def test_face_count_output(self, real_face_tensor):
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        assert face_count == len(landmarks)

    def test_face_detect_emits_pose_data(self, real_face_tensor):
        """Verify FaceDetect emits non-None pose dicts with expected keys."""
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        assert face_count >= 1, "Should detect at least 1 face"
        pose = landmarks[0]["pose"]
        assert pose is not None, "pose should not be None with transformation matrix enabled"
        assert "yaw" in pose
        assert "pitch" in pose
        assert "roll" in pose
        assert "matrix" in pose
        assert pose["matrix"].shape == (4, 4)

    def test_pose_values_are_reasonable(self, real_face_tensor):
        """Verify pose angle values are floats within expected range."""
        from comfyui_imgtools.face_detection import FaceDetect

        node = FaceDetect()
        landmarks, preview, face_count = node.detect_faces(real_face_tensor)

        assert face_count >= 1
        pose = landmarks[0]["pose"]
        assert pose is not None

        for key in ("yaw", "pitch", "roll"):
            val = pose[key]
            assert isinstance(val, float), f"{key} should be float, got {type(val)}"
            assert -180 < val < 180, f"{key}={val} out of expected range"

        matrix = pose["matrix"]
        assert matrix.dtype in (np.float64, np.float32), (
            f"matrix dtype should be float, got {matrix.dtype}"
        )
