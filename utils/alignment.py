"""Alignment math utilities for face crop and alignment.

Provides functions to compute eye-based rotation angle, build affine transforms,
apply them to images, compute padded crop boxes, all using scikit-image (no OpenCV).
"""

import numpy as np
from skimage.transform import AffineTransform, warp

# MediaPipe face mesh landmark indices for eye contours.
# Using the mean of all contour landmarks gives a more robust eye center
# than any single landmark index.
# "Right" and "Left" are from the subject's perspective.
RIGHT_EYE_INDICES = [
    33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246
]
LEFT_EYE_INDICES = [
    362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398
]


def compute_eye_centers(landmarks_px):
    """Compute the center (x, y) of each eye from 478-point landmarks.

    Args:
        landmarks_px: numpy array of shape (478, 2) with (x, y) pixel coordinates.

    Returns:
        Tuple of (left_eye_center, right_eye_center), each a numpy array of shape (2,).
    """
    left_eye = landmarks_px[LEFT_EYE_INDICES].mean(axis=0)
    right_eye = landmarks_px[RIGHT_EYE_INDICES].mean(axis=0)
    return left_eye, right_eye


def compute_alignment_angle(left_eye, right_eye):
    """Compute the tilt angle (radians) of the eye line from horizontal.

    Returns the angle that the line between the eyes deviates from a
    perfectly horizontal orientation. A value of 0.0 means the eyes
    are at the same y-coordinate (face is upright).

    The sign convention ensures that negating this angle in a rotation
    transform will correct the tilt, regardless of which eye is to the
    left or right in image coordinates.

    Args:
        left_eye: (x, y) array for the subject's left eye center.
        right_eye: (x, y) array for the subject's right eye center.

    Returns:
        Angle in radians. The tilt deviation from horizontal.
    """
    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    # Use atan2 but normalize so that a horizontal line (dy=0) always gives 0,
    # regardless of whether dx is positive or negative.
    # For a normal upright face, dx < 0 (right eye is left of left eye in image).
    # arctan2(0, negative) = pi. We want 0.
    # The tilt is the angle relative to the horizontal axis direction.
    angle = float(np.arctan2(dy, abs(dx)))
    return angle


def build_alignment_transform(landmarks_px, img_width, img_height):
    """Build an AffineTransform that rotates the face to upright orientation.

    Rotates by the negative of the eye tilt angle around the midpoint between
    the two eye centers.

    Args:
        landmarks_px: numpy array of shape (478, 2) with (x, y) pixel coordinates.
        img_width: Width of the source image in pixels.
        img_height: Height of the source image in pixels.

    Returns:
        Tuple of (transform, angle) where transform is an AffineTransform instance
        and angle is the raw tilt angle in radians (before negation).
    """
    left_eye, right_eye = compute_eye_centers(landmarks_px)
    angle = compute_alignment_angle(left_eye, right_eye)

    # Rotation center is midpoint between eyes
    center_x, center_y = (left_eye + right_eye) / 2.0

    # Build composite transform: translate to origin, rotate, translate back.
    # skimage AffineTransform composes with + (right to left application).
    tform_to_origin = AffineTransform(translation=(-center_x, -center_y))
    tform_rotate = AffineTransform(rotation=-angle)
    tform_back = AffineTransform(translation=(center_x, center_y))

    full_transform = tform_back + tform_rotate + tform_to_origin

    return full_transform, angle


def apply_alignment(img_np, transform, output_shape=None):
    """Apply an alignment transform to an image.

    Args:
        img_np: numpy array of shape (H, W, 3), float64, values in [0, 1].
        transform: AffineTransform instance from build_alignment_transform.
        output_shape: optional (H, W) tuple for the output canvas size.
            Defaults to the input image shape.

    Returns:
        Aligned image as float64 array of the same shape.
    """
    aligned = warp(
        img_np,
        inverse_map=transform.inverse,
        output_shape=output_shape or img_np.shape[:2],
        order=1,
        mode="constant",
        cval=0.0,
        preserve_range=True,
    )
    return aligned


def compute_padded_crop_box(landmarks_px, transform, padding_factor, img_w, img_h):
    """Compute a padded crop box from transformed landmarks.

    Transforms the landmarks using the given affine transform, computes their
    bounding box, expands it by padding_factor on each side, and clamps to
    image bounds.

    Args:
        landmarks_px: numpy array of shape (478, 2) with (x, y) pixel coordinates.
        transform: AffineTransform used for alignment.
        padding_factor: float, e.g. 0.3 means 30% padding on each side.
        img_w: Image width for clamping.
        img_h: Image height for clamping.

    Returns:
        Tuple (x1, y1, x2, y2) as ints, clamped to image bounds.
    """
    # Transform landmarks to aligned space
    aligned_lms = transform(landmarks_px)

    # Bounding box of all transformed landmarks
    x_min, y_min = aligned_lms.min(axis=0)
    x_max, y_max = aligned_lms.max(axis=0)

    # Expand by padding factor
    w = x_max - x_min
    h = y_max - y_min
    pad_x = w * padding_factor
    pad_y = h * padding_factor

    x1 = max(0, int(x_min - pad_x))
    y1 = max(0, int(y_min - pad_y))
    x2 = min(img_w, int(x_max + pad_x))
    y2 = min(img_h, int(y_max + pad_y))

    return (x1, y1, x2, y2)
