import os

import numpy as np
import pytest
import torch

from utils.mediapipe_helper import get_landmarker, comfyui_to_mediapipe, EXTENSION_ROOT


class TestGetLandmarker:
    def test_landmarker_creation(self):
        """get_landmarker() returns a FaceLandmarker instance (not None)."""
        from mediapipe.tasks.python import vision

        landmarker = get_landmarker()
        assert landmarker is not None
        assert isinstance(landmarker, vision.FaceLandmarker)

    def test_landmarker_caching(self):
        """Calling get_landmarker() twice returns the same instance."""
        l1 = get_landmarker()
        l2 = get_landmarker()
        assert l1 is l2

    def test_different_matrix_param_creates_new_instance(self):
        """Changing output_facial_transformation_matrixes creates a new landmarker."""
        l1 = get_landmarker(output_facial_transformation_matrixes=False)
        l2 = get_landmarker(output_facial_transformation_matrixes=True)
        assert l1 is not l2

    def test_same_matrix_param_returns_cached(self):
        """Same output_facial_transformation_matrixes value returns cached instance."""
        l1 = get_landmarker(output_facial_transformation_matrixes=True)
        l2 = get_landmarker(output_facial_transformation_matrixes=True)
        assert l1 is l2

    @pytest.mark.slow
    def test_model_auto_download(self):
        """If model file is missing, get_landmarker() downloads it."""
        model_path = os.path.join(EXTENSION_ROOT, "models", "face_landmarker.task")
        # After calling get_landmarker, the model file should exist
        get_landmarker()
        assert os.path.exists(model_path)
        assert os.path.getsize(model_path) > 0


class TestComfyuiToMediapipe:
    def test_shape(self, sample_face_image_tensor):
        """Converts a [1, 64, 64, 3] float32 tensor to mp.Image with correct dimensions."""
        tensor = torch.rand(1, 64, 64, 3, dtype=torch.float32)
        mp_image = comfyui_to_mediapipe(tensor)
        assert mp_image.width == 64
        assert mp_image.height == 64

    def test_dtype(self, sample_face_image_tensor):
        """Output image data is uint8, not float32."""
        mp_image = comfyui_to_mediapipe(sample_face_image_tensor)
        assert mp_image.numpy_view().dtype == np.uint8
