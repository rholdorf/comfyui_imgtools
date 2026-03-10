"""Face mask generation from MediaPipe face oval landmarks.

Uses scikit-image polygon2mask to create a binary mask from the face oval
contour defined by 36 MediaPipe landmark indices.
"""

import numpy as np
from skimage.draw import polygon2mask

# MediaPipe face oval landmark indices (36 points tracing the face contour).
# Verified from mediapipe/python/solutions/face_mesh_connections.py FACEMESH_FACE_OVAL.
FACE_OVAL_INDICES = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
    361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
    176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
    162, 21, 54, 103, 67, 109,
]


def generate_face_mask(landmarks_px, img_height, img_width):
    """Generate a binary face mask from face oval landmarks.

    Args:
        landmarks_px: numpy array of shape (478, 2) with (x, y) pixel coordinates.
        img_height: Height of the output mask.
        img_width: Width of the output mask.

    Returns:
        numpy array of shape (img_height, img_width), dtype float32,
        with 1.0 inside the face oval and 0.0 outside.
    """
    oval_points = landmarks_px[FACE_OVAL_INDICES]
    # polygon2mask expects (row, col) = (y, x), but landmarks are (x, y).
    polygon_rc = oval_points[:, ::-1]
    mask = polygon2mask((img_height, img_width), polygon_rc)
    return mask.astype(np.float32)
