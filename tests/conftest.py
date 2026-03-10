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


_FACE_OVAL_INDICES_FOR_FIXTURES = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
    361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
    176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
    162, 21, 54, 103, 67, 109,
]


def _make_deterministic_landmarks(center_x, center_y, spread=30.0):
    """Create a (478, 2) landmark array with known eye and oval positions.

    Places landmarks in a deterministic pattern around the given center.
    Eye indices and face oval indices get specific, predictable positions.
    """
    from utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES

    FACE_OVAL_INDICES = _FACE_OVAL_INDICES_FOR_FIXTURES

    landmarks = np.zeros((478, 2), dtype=np.float64)

    # Fill all landmarks with positions spread around center
    rng = np.random.RandomState(42)
    landmarks[:, 0] = center_x + rng.uniform(-spread, spread, 478)
    landmarks[:, 1] = center_y + rng.uniform(-spread, spread, 478)

    # Set left eye landmarks to a known cluster (subject's left = image right)
    for idx in LEFT_EYE_INDICES:
        landmarks[idx] = [center_x + 20.0, center_y - 15.0]

    # Set right eye landmarks to a known cluster (subject's right = image left)
    for idx in RIGHT_EYE_INDICES:
        landmarks[idx] = [center_x - 20.0, center_y - 15.0]

    # Set face oval landmarks to a known ellipse pattern
    n_oval = len(FACE_OVAL_INDICES)
    for i, idx in enumerate(FACE_OVAL_INDICES):
        angle = 2 * np.pi * i / n_oval
        landmarks[idx] = [
            center_x + spread * np.cos(angle),
            center_y + spread * 1.3 * np.sin(angle),
        ]

    return landmarks


@pytest.fixture
def mock_deterministic_landmarks():
    """Single face with deterministic landmarks centered at (128, 128).

    Eyes are perfectly horizontal (same y), so alignment angle should be ~0.
    """
    landmarks = _make_deterministic_landmarks(128.0, 128.0)
    return [
        {
            "landmarks": landmarks,
            "landmarks_3d": np.zeros((478, 3), dtype=np.float64),
        }
    ]


@pytest.fixture
def mock_landmarks_tilted():
    """Single face with tilted eyes (~15 degree tilt).

    Left eye (subject's left) is higher than right eye.
    """
    from utils.alignment import LEFT_EYE_INDICES, RIGHT_EYE_INDICES

    landmarks = _make_deterministic_landmarks(128.0, 128.0)

    # Tilt: left eye at y=100, right eye at y=128 -> ~15 deg
    # dx = 40, dy = right_y - left_y = 128 - 100 = 28
    # angle = arctan2(28, 40) ~ 0.611 rad ~ 35 deg (use smaller tilt)
    # For ~15 deg: dx=40, dy=40*tan(15deg)=40*0.268=10.72
    for idx in LEFT_EYE_INDICES:
        landmarks[idx] = [148.0, 118.0]  # right side of image, higher
    for idx in RIGHT_EYE_INDICES:
        landmarks[idx] = [108.0, 128.0]  # left side of image, lower

    # dy = 128 - 118 = 10, dx = 108 - 148 = -40
    # angle = arctan2(10, -40) -- but we want right-left:
    # Actually: right_eye=(108,128), left_eye=(148,118)
    # The angle formula: dy = right[1]-left[1] = 128-118=10, dx = right[0]-left[0] = 108-148=-40
    # arctan2(10, -40) ~ 2.897 rad -- that's wrong direction
    # Fix: make right eye to the right of left eye in image coords
    for idx in RIGHT_EYE_INDICES:
        landmarks[idx] = [148.0, 128.0]  # image right
    for idx in LEFT_EYE_INDICES:
        landmarks[idx] = [108.0, 118.0]  # image left, higher

    # Now: left_eye=(108,118), right_eye=(148,128)
    # dy = 128-118=10, dx = 148-108=40
    # angle = arctan2(10, 40) ~ 0.245 rad ~ 14 deg

    return [
        {
            "landmarks": landmarks,
            "landmarks_3d": np.zeros((478, 3), dtype=np.float64),
        }
    ]


@pytest.fixture
def mock_multi_face_landmarks():
    """Two faces with deterministic landmarks at different positions."""
    face1 = _make_deterministic_landmarks(80.0, 80.0, spread=20.0)
    face2 = _make_deterministic_landmarks(180.0, 180.0, spread=20.0)
    return [
        {
            "landmarks": face1,
            "landmarks_3d": np.zeros((478, 3), dtype=np.float64),
        },
        {
            "landmarks": face2,
            "landmarks_3d": np.zeros((478, 3), dtype=np.float64),
        },
    ]
