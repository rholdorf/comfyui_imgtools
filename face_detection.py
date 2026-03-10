"""FaceDetect ComfyUI node - detects face landmarks using MediaPipe."""

import numpy as np
import torch

from .utils.mediapipe_helper import get_landmarker, comfyui_to_mediapipe
from .utils.landmarks import extract_landmarks, draw_landmarks_on_image


class FaceDetect:
    """Detect face landmarks in an image using MediaPipe Face Landmarker.

    Outputs structured landmark data, a preview image with landmarks drawn,
    and a count of detected faces.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "min_detection_confidence": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
            },
        }

    RETURN_TYPES = ("FACE_LANDMARKS", "IMAGE", "INT")
    RETURN_NAMES = ("landmarks", "preview", "face_count")
    FUNCTION = "detect_faces"
    CATEGORY = "imgtools/face"

    def detect_faces(self, image, min_detection_confidence=0.5):
        _, h, w, _ = image.shape

        # Convert to MediaPipe format and detect
        mp_image = comfyui_to_mediapipe(image)
        landmarker = get_landmarker(
            min_detection_confidence=min_detection_confidence
        )
        result = landmarker.detect(mp_image)

        # Extract structured landmark data
        faces = extract_landmarks(result, w, h)

        # Create preview image with landmarks drawn
        img_np = (image[0].cpu().numpy() * 255).astype(np.uint8)
        if faces:
            preview_np = draw_landmarks_on_image(
                img_np, result.face_landmarks, w, h
            )
        else:
            preview_np = img_np.copy()

        preview = torch.from_numpy(
            preview_np.astype(np.float32) / 255.0
        ).unsqueeze(0)

        return (faces, preview, len(faces))
