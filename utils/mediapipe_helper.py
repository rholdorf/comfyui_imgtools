import os
import urllib.request

import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.dirname(MODULE_DIR)

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

_landmarker = None
_landmarker_params = None


def get_landmarker(min_detection_confidence=0.5, min_presence_confidence=0.5,
                   output_facial_transformation_matrixes=False):
    """Get or create a cached FaceLandmarker instance.

    If the model file is not present, it will be auto-downloaded from Google's CDN.
    If any parameter differs from the cached instance, a new one is created.

    Args:
        min_detection_confidence: Minimum confidence for face detection (0.0-1.0).
        min_presence_confidence: Minimum confidence for face presence (0.0-1.0).
        output_facial_transformation_matrixes: Whether to output the 4x4 facial
            transformation matrix for each detected face. Default False for
            backward compatibility.

    Returns:
        A mediapipe FaceLandmarker instance.
    """
    global _landmarker, _landmarker_params

    params = (min_detection_confidence, min_presence_confidence,
              output_facial_transformation_matrixes)

    if _landmarker is not None and _landmarker_params == params:
        return _landmarker

    model_dir = os.path.join(EXTENSION_ROOT, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "face_landmarker.task")

    if not os.path.exists(model_path):
        print("[ImgTools] Downloading MediaPipe Face Landmarker model...")
        urllib.request.urlretrieve(MODEL_URL, model_path)

    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=10,
        min_face_detection_confidence=min_detection_confidence,
        min_face_presence_confidence=min_presence_confidence,
        output_facial_transformation_matrixes=output_facial_transformation_matrixes,
    )
    _landmarker = vision.FaceLandmarker.create_from_options(options)
    _landmarker_params = params
    return _landmarker


def comfyui_to_mediapipe(image_tensor):
    """Convert a ComfyUI IMAGE tensor to a MediaPipe Image.

    Args:
        image_tensor: torch tensor of shape [batch, H, W, C], float32, range [0, 1].

    Returns:
        mp.Image (SRGB, uint8) for the first image in the batch.
    """
    img_np = (image_tensor[0].cpu().numpy() * 255).astype(np.uint8)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)
