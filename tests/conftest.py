import numpy as np
import pytest
import torch


@pytest.fixture
def sample_face_image_tensor():
    """A ComfyUI-format IMAGE tensor [1, H, W, 3] float32 for shape/dtype tests."""
    return torch.rand(1, 256, 256, 3, dtype=torch.float32)


@pytest.fixture(scope="session")
def sample_mp_image():
    """A MediaPipe Image derived from a random tensor, for integration tests."""
    import mediapipe as mp

    img_np = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)


@pytest.fixture
def mock_landmark_data():
    """Fake landmark data for unit testing downstream consumers.

    Returns a list with one face dict containing (478, 2) and (478, 3) numpy arrays.
    """
    return [
        {
            "landmarks": np.random.rand(478, 2).astype(np.float64) * 256,
            "landmarks_3d": np.random.rand(478, 3).astype(np.float64),
        }
    ]
