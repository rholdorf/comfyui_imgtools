import numpy as np

from utils.pose_utils import extract_pose_angles


def extract_landmarks(result, img_width, img_height):
    """Extract landmark data from a FaceLandmarkerResult.

    Args:
        result: A mediapipe FaceLandmarkerResult.
        img_width: Width of the source image in pixels.
        img_height: Height of the source image in pixels.

    Returns:
        List of face dicts, each containing:
            - "landmarks": np.array of shape (478, 2) with pixel coordinates.
            - "landmarks_3d": np.array of shape (478, 3) with normalized coords.
            - "pose": dict with pitch/yaw/roll/matrix from the transformation
              matrix, or None if the matrix is unavailable.
        Returns an empty list if no faces were detected.
    """
    if not result.face_landmarks:
        return []

    faces = []
    for i, face_lms in enumerate(result.face_landmarks):
        landmarks_px = np.array(
            [[lm.x * img_width, lm.y * img_height] for lm in face_lms]
        )
        landmarks_3d = np.array(
            [[lm.x, lm.y, lm.z] for lm in face_lms]
        )

        pose = None
        if (hasattr(result, 'facial_transformation_matrixes') and
                result.facial_transformation_matrixes and
                i < len(result.facial_transformation_matrixes)):
            pose = extract_pose_angles(result.facial_transformation_matrixes[i])

        faces.append({
            "landmarks": landmarks_px,
            "landmarks_3d": landmarks_3d,
            "pose": pose,
        })
    return faces


def draw_landmarks_on_image(img_np, face_landmarks_list, img_width, img_height):
    """Draw green dots at each landmark position on an image copy.

    Args:
        img_np: numpy array of shape (H, W, 3), dtype uint8.
        face_landmarks_list: List of MediaPipe NormalizedLandmarkList (one per face).
        img_width: Width of the image in pixels.
        img_height: Height of the image in pixels.

    Returns:
        numpy array (H, W, 3) uint8 with green 2x2 dots drawn at landmark positions.
    """
    result = img_np.copy()
    for face_lms in face_landmarks_list:
        for lm in face_lms:
            x = int(lm.x * img_width)
            y = int(lm.y * img_height)
            y_start = max(0, y - 1)
            y_end = min(img_height, y + 1)
            x_start = max(0, x - 1)
            x_end = min(img_width, x + 1)
            result[y_start:y_end, x_start:x_end] = [0, 255, 0]
    return result
