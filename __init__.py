from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter

try:
    from .face_detection import FaceDetect
    from .face_crop import FaceCropAlign
    from .face_morph import FaceShapeMorph
    from .face_composite import FaceComposite
    from .face_model_builder import FaceModelBuilder
    from .face_model_morph import FaceModelMorph
    from .face_model_loader import LoadFaceModel
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
    NODE_CLASS_MAPPINGS["FaceCropAlign"] = FaceCropAlign
    NODE_DISPLAY_NAME_MAPPINGS["FaceCropAlign"] = "ImgTools Face Crop Align"
    NODE_CLASS_MAPPINGS["FaceShapeMorph"] = FaceShapeMorph
    NODE_DISPLAY_NAME_MAPPINGS["FaceShapeMorph"] = "ImgTools Face Shape Morph"
    NODE_CLASS_MAPPINGS["FaceComposite"] = FaceComposite
    NODE_DISPLAY_NAME_MAPPINGS["FaceComposite"] = "ImgTools Face Composite"
    NODE_CLASS_MAPPINGS["FaceModelBuilder"] = FaceModelBuilder
    NODE_DISPLAY_NAME_MAPPINGS["FaceModelBuilder"] = "ImgTools Face Model Builder"
    NODE_CLASS_MAPPINGS["FaceModelMorph"] = FaceModelMorph
    NODE_DISPLAY_NAME_MAPPINGS["FaceModelMorph"] = "ImgTools Face Model Morph"
    NODE_CLASS_MAPPINGS["LoadFaceModel"] = LoadFaceModel
    NODE_DISPLAY_NAME_MAPPINGS["LoadFaceModel"] = "ImgTools Load Face Model"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
