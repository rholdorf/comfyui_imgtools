from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter

try:
    from .face_detection import FaceDetect
    _face_nodes_available = True
except ImportError as e:
    print(f"[ImgTools] Warning: Face detection nodes unavailable. {e}")
    print("[ImgTools] Install mediapipe: pip install mediapipe>=0.10.14")
    _face_nodes_available = False

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "PathSplitter": PathSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
    "ImagePaddingCalculator": "Image Padding Calculator",
    "PathSplitter": "Path Splitter",
}

if _face_nodes_available:
    NODE_CLASS_MAPPINGS["FaceDetect"] = FaceDetect
    NODE_DISPLAY_NAME_MAPPINGS["FaceDetect"] = "ImgTools Face Detect"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
